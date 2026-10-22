"""Lab-only serial VISCA/TCP bridge plus a Preset-only selection state machine.

Wire syntax: Sony E0421001M / E-042-100-13; transport: Ross PTZ plugin manual9.15.
Physical Ross captures and preset completion semantics remain acceptance gates.
"""
import collections
import ipaddress
import socket
import socketserver
import threading
import time
import uuid
from .protocol import movement,preset

class ViscaError(ValueError):
    def __init__(self,message,code=0x02):super().__init__(message);self.code=code

def decode(frame):
    # Sony serial VISCA network administration, one virtual camera per endpoint.
    if frame==bytes.fromhex('88 30 01 FF'):return 'address_set',{}
    if frame in (bytes.fromhex('88 01 00 01 FF'),bytes.fromhex('81 01 00 01 FF')):
        return 'interface_clear',{'broadcast':frame[0]==0x88}
    if len(frame)<4 or len(frame)>16 or frame[0]!=0x81 or frame[-1]!=0xff:
        raise ViscaError('Only address1 serial VISCA frames are supported')
    body=frame[1:-1]
    if body[:3]==bytes.fromhex('01 06 01') and len(body)==7:
        pan_speed,tilt_speed,pan_direction,tilt_direction=body[3:]
        if not 1<=pan_speed<=24 or not 1<=tilt_speed<=20 or pan_direction not in (1,2,3) or tilt_direction not in (1,2,3):raise ViscaError('Invalid pan/tilt speed or direction')
        scale=lambda v,maximum:1+round((v-1)*48/(maximum-1))
        pan=0 if pan_direction==3 else scale(pan_speed,24)*(-1 if pan_direction==1 else 1)
        tilt=0 if tilt_direction==3 else scale(tilt_speed,20)*(1 if tilt_direction==1 else -1)
        return 'pan_tilt',{'pan':pan,'tilt':tilt}
    if body[:3] in (bytes.fromhex('01 04 07'),bytes.fromhex('01 04 08')) and len(body)==4:
        key='zoom' if body[2]==7 else 'focus';value=body[3]
        if value==0:speed=0
        elif value in (2,3):speed=24*(1 if value==2 else -1)
        elif value>>4 in (2,3) and value&15<=7:speed=(1+round((value&15)*48/7))*(1 if value>>4==2 else -1)
        else:raise ViscaError('Invalid lens speed')
        return key,{key:speed}
    if body[:3]==bytes.fromhex('01 04 38') and len(body)==4 and body[3] in (2,3):
        return 'focus_mode',{'value':1 if body[3]==2 else 0}
    if body==bytes.fromhex('09 04 38'):return 'focus_query',{}
    if body[:3]==bytes.fromhex('01 04 3F') and len(body)==5 and body[3] in (1,2):
        number=body[4]+1;preset(number)
        return 'preset',{'number':number,'store':body[3]==1}
    raise ViscaError('Unsupported VISCA command')

class PresetFollower:
    """Consumes explicit trusted bus events. No event is inferred from a packet.

    Until real Carbonite feedback is integrated, only simulator API inputs call
    this class. Non-neutral input after a handover is rejected until both PT and
    zoom neutral have been observed in the new epoch.
    """
    def __init__(self,engine):
        self.engine=engine;self.lock=threading.RLock();self.selected=None;self.epoch=0
        self.neutral=set();self.axes={'pan':0,'tilt':0,'zoom':0,'focus':0}
        self.owner='visca-lab-'+uuid.uuid4().hex[:12]
        self.recalled={}
        self.generation=None
        self.update_status()

    def update_status(self):
        with self.engine.lock:
            self.engine.ross_status.update(state='LAB VISCA/TCP — hardware unverified',preset_follow='simulator input only',
                selected=self.selected,selection_epoch=self.epoch,neutral_ready={'pan_tilt','zoom'}<=self.neutral)

    def bus_event(self,bus,camera):
        if bus not in ('preset','program'):raise ValueError('Bus must be preset or program')
        if bus=='program':return {'changed':False,'selected':self.selected,'epoch':self.epoch}
        if camera not in self.engine.cameras or self.engine.cameras[camera]['config']['manufacturer'] not in ('Panasonic','Sony'):raise ValueError('Select a configured Panasonic or Sony camera')
        with self.lock:
            if camera==self.selected:return {'changed':False,'selected':self.selected,'epoch':self.epoch}
            previous=self.selected
            if previous is not None:
                self.engine.stop(previous)
                with self.engine.lock:
                    old=self.engine.cameras[previous]
                    if old['owner']==self.owner:old['owner']=None;old['lease_until']=0
            self.epoch+=1;self.selected=camera;self.neutral=set();self.axes=dict.fromkeys(self.axes,0)
            self.generation=self.engine.cameras[camera]['generation']
            self.update_status();self.engine.event(camera,'lab-preset-selection',previous=previous,epoch=self.epoch)
            return {'changed':True,'selected':camera,'epoch':self.epoch}

    def apply_motion(self,camera,kind,axes,epoch,received):
        with self.lock:
            if camera!=self.selected or epoch!=self.epoch:raise ViscaError('Stale selection or wrong camera',0x41)
            if time.monotonic()-received>.3:raise ViscaError('Stale motion packet',0x41)
            c=self.engine.cameras[camera]
            with c['io']:
                if time.monotonic()-received>.3:raise ViscaError('Motion expired while waiting for camera',0x41)
                with self.engine.lock:
                    if self.generation!=c['generation']:
                        self.generation=c['generation'];self.neutral=set();self.axes=dict.fromkeys(self.axes,0)
                    neutral=not any(axes.values())
                    if neutral:self.neutral.add(kind)
                    if not neutral and not {'pan_tilt','zoom'}<=self.neutral:raise ViscaError('Return positioner to neutral after handover',0x41)
                    if neutral and c['owner']!=self.owner and c['lease_until']>time.monotonic():
                        self.axes.update(axes)
                        self.update_status();self.engine.event(camera,'visca-idle-kept-owner')
                        return
                    if not neutral or (c['owner']==self.owner and c['moving']):self.engine.claim(c,self.owner)
                    if axes.get('focus'):self.engine.check_mode(c,'focus')
                    if c['config']['driver']=='sony-sdk' and kind=='pan_tilt' and any(axes.values()):raise ViscaError('PXW-Z200 has no pan/tilt motors',0x41)
                    self.axes.update(axes)
                    c['moving']=any(self.axes.values());c['motion_deadline']=received+.9 if c['moving'] else 0
                    if not c['moving'] and c['owner']==self.owner:c['owner']=None;c['lease_until']=0
                if c['config']['driver']=='sony-sdk':
                    c['driver'].move(**self.axes)
                    self.update_status();self.engine.event(camera,'sony-visca-lens',axes=dict(self.axes));return
                if kind=='pan_tilt':
                    command=movement(self.axes['pan'],self.axes['tilt'])[0];expected='pTS'+command[4:]
                elif kind=='zoom':command=f'#Z{self.axes["zoom"]+50:02d}';expected='zS'+command[2:]
                else:command=f'#F{self.axes["focus"]+50:02d}';expected='fS'+command[2:]
                axis=command[:4] if command.startswith('#PTS') else command[:2]
                if neutral and c['driver'].motion_state.get(axis)==command:
                    self.update_status();return
                c['driver'].motion_state.pop(axis,None)
                response=c['driver'].send(command)
                if response!=expected:raise ViscaError('Downstream speed command not acknowledged',0x41)
                c['driver'].motion_state[command[:4] if command.startswith('#PTS') else command[:2]]=command
            self.update_status();self.engine.event(camera,'lab-visca-motion',axes=dict(self.axes))

    def halt(self,camera):
        with self.lock:
            self.engine.stop(camera)
            if camera==self.selected:
                self.axes=dict.fromkeys(self.axes,0);self.neutral=set();self.update_status()

class FixedCameraController(PresetFollower):
    """One numbered endpoint always controls one explicitly configured camera."""
    def __init__(self,engine,camera):
        super().__init__(engine);self.bus_event('preset',camera)

    def update_status(self):
        if self.selected is None:return
        with self.engine.lock:
            endpoints=self.engine.ross_status.setdefault('endpoints',{})
            endpoints[self.selected]={'number':self.engine.cameras[self.selected]['config'].get('number'),
                'neutral_ready':{'pan_tilt','zoom'}<=self.neutral,'selection':'fixed endpoint'}
            self.engine.ross_status.update(state='Configured PIVOTCam endpoints — equipment acceptance pending',preset_follow='fixed camera per TCP port')

class LabViscaServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True
    def __init__(self,address,engine,camera,follower,allow_store=False):
        if not ipaddress.ip_address(address[0]).is_loopback:raise ValueError('VISCA lab must bind to loopback')
        if camera not in engine.cameras or not engine.cameras[camera]['config'].get('simulator'):
            raise ValueError('VISCA bridge currently accepts simulated cameras only')
        if engine.cameras[camera]['config']['manufacturer']!='Panasonic':raise ValueError('VISCA target must be Panasonic')
        self.configure(address,engine,camera,follower,allow_store)

    def configure(self,address,engine,camera,follower,allow_store):
        self.engine,self.camera,self.follower,self.allow_store=engine,camera,follower,allow_store
        self.slots=threading.BoundedSemaphore(1)
        self.active=0
        self.stopping=threading.Event();self.clients=set();self.client_condition=threading.Condition()
        super().__init__(address,ViscaHandler)

    def server_close(self):
        self.stopping.set()
        with self.client_condition:
            for client in list(self.clients):
                try:client.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            self.client_condition.wait_for(lambda:self.active==0,timeout=6)
        super().server_close()

class PivotCamServer(LabViscaServer):
    """Explicit physical or simulated Panasonic endpoint, restricted to one frame."""
    def __init__(self,address,engine,camera,follower,controller,allow_store=False):
        self.controller=str(ipaddress.IPv4Address(controller))
        ipaddress.IPv4Address(address[0])
        if camera not in engine.cameras or engine.cameras[camera]['config']['driver'] not in ('panasonic','sony-sdk'):
            raise ValueError('PIVOTCam requires an enabled Panasonic or Sony camera')
        self.configure(address,engine,camera,follower,allow_store)

    def verify_request(self,request,client_address):
        return client_address[0]==self.controller and not self.stopping.is_set()

class ViscaHandler(socketserver.BaseRequestHandler):
    def handle(self):
        if not self.server.slots.acquire(False):return
        with self.server.client_condition:
            self.server.active+=1;self.server.clients.add(self.request)
        self.request.settimeout(.2)
        queue=collections.deque();condition=threading.Condition();alive=threading.Event();alive.set()
        def read():
            buffer=bytearray()
            try:
                while alive.is_set() and not self.server.stopping.is_set() and not self.server.engine.closed.is_set():
                    try:chunk=self.request.recv(1024)
                    except socket.timeout:continue
                    if not chunk:break
                    buffer.extend(chunk)
                    while 255 in buffer:
                        end=buffer.index(255)+1;frame=bytes(buffer[:end]);del buffer[:end]
                        try:kind,data=decode(frame)
                        except (ValueError,IndexError):kind,data='invalid',{}
                        stamp=time.monotonic()
                        with condition:
                            # Coalesce motion only after the last non-motion barrier.
                            if kind in ('pan_tilt','zoom','focus'):
                                for i in range(len(queue)-1,-1,-1):
                                    if queue[i][0] not in ('pan_tilt','zoom','focus'):break
                                    if queue[i][0]==kind:del queue[i];break
                            if len(queue)>=32:raise ValueError('VISCA queue overflow')
                            queue.append((kind,data,frame,stamp,self.server.follower.epoch));condition.notify()
                    if len(buffer)>16:raise ValueError('Oversized unterminated VISCA packet')
            except (OSError,ValueError):pass
            finally:
                alive.clear()
                with condition:condition.notify()
        reader=threading.Thread(target=read,daemon=True);reader.start()
        try:
            while alive.is_set() and not self.server.stopping.is_set() and not self.server.engine.closed.is_set():
                with condition:
                    if not queue:condition.wait(.1)
                    if not queue:continue
                    kind,data,frame,received,epoch=queue.popleft()
                self.server.engine.event(self.server.camera,'visca-rx',hex=frame.hex(' '))
                try:
                    if kind=='invalid':raise ViscaError('Invalid frame')
                    if kind=='address_set':
                        self.request.sendall(bytes.fromhex('88 30 02 FF'))
                        self.server.engine.event(self.server.camera,'visca-lab-initialized',command=kind);continue
                    if kind=='interface_clear':
                        self.server.follower.halt(self.server.camera)
                        self.request.sendall(bytes.fromhex('88 01 00 01 FF' if data['broadcast'] else '90 50 FF'))
                        self.server.engine.event(self.server.camera,'visca-lab-initialized',command=kind);continue
                    if kind=='focus_query':
                        c=self.server.engine.cameras[self.server.camera]
                        with c['io']:value=c['driver'].query('focus_auto')
                        with self.server.engine.lock:c['params']['focus_auto'].update(value=value,last_query=time.time(),confirmation='confirmed')
                        auto=value==1 if c['config']['driver']=='sony-sdk' else bool(value)
                        self.request.sendall(bytes([0x90,0x50,2 if auto else 3,0xff]));continue
                    # No ACK is sent until the request has passed policy checks.
                    if kind in ('pan_tilt','zoom','focus'):
                        self.server.follower.apply_motion(self.server.camera,kind,data,epoch,received)
                    elif kind=='focus_mode':
                        c=self.server.engine.cameras[self.server.camera]
                        with c['io']:
                            with self.server.engine.lock:self.server.engine.claim(c,self.server.follower.owner)
                            requested=(1 if data['value'] else 2) if c['config']['driver']=='sony-sdk' else data['value']
                            value=c['driver'].write('focus_auto',requested)
                            if value!=requested:raise ViscaError('Focus mode mismatch',0x41)
                            with self.server.engine.lock:c['params']['focus_auto'].update(value=value,last_query=time.time(),confirmation='confirmed')
                    elif kind=='preset':
                        if data['store'] and not self.server.allow_store:raise ViscaError('Preset store disabled',0x41)
                        result=self.server.engine.command(self.server.camera,'preset',dict(data,confirm='OVERWRITE' if data['store'] else ''),self.server.follower.owner)
                        self.server.follower.recalled[self.server.camera]=data['number']
                    self.request.sendall(bytes.fromhex('90 41 FF 90 51 FF'))
                    self.server.engine.event(self.server.camera,'visca-lab-accepted',command=kind)
                except ViscaError as exc:self.request.sendall(bytes([0x90,0x60,exc.code,0xff]))
                except (ValueError,PermissionError,KeyError):self.request.sendall(bytes.fromhex('90 60 41 FF'))
                except OSError:break
        finally:
            alive.clear()
            # A dropped controller connection cannot leave its selected target moving.
            if self.server.follower.selected==self.server.camera:
                try:self.server.follower.halt(self.server.camera)
                except Exception:pass
            with self.server.client_condition:
                self.server.active-=1;self.server.clients.discard(self.request);self.server.client_condition.notify_all()
            self.server.slots.release()
