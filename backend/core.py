"""Central state, exclusive camera ownership, write coalescing and motion watchdog."""
import collections
import json
import pathlib
import threading
import time
from .scheduling import CameraAccess
from .protocol import PANASONIC,Parameter,panasonic_parameters
from .drivers import Panasonic
from .panasonic_serial import PanasonicSerial,parameters as serial_parameters
from .sony import Sony,SONY

MARSHALL_LAB={p.id:p for p in [
    Parameter('wb_mode','White balance: 0 auto / 1 manual / 2 ATW / 3 push',0,3,'','','',1,10),
    Parameter('red_gain','Red gain (LAB range)',0,255,'','','',dependency='wb_mode=1'),
    Parameter('blue_gain','Blue gain (LAB range)',0,255,'','','',dependency='wb_mode=1'),
    Parameter('exposure_auto','Exposure: 0 manual / 1 auto',0,1,'','',''),
    Parameter('brightness','Brightness',0,20,'','',''),
    Parameter('gain','Gain (LAB range)',0,20,'','','',dependency='exposure_auto=0'),
    Parameter('agc_limit','AGC limit',0,20,'','',''),
    Parameter('shutter','Shutter (LAB enumeration)',0,15,'','','',dependency='exposure_auto=0'),
    Parameter('black_level','Black level',0,32,'','',''),
    Parameter('gamma','Gamma x 10',3,8,'','',''),
    Parameter('colour','Colour level',0,20,'','',''),
    Parameter('sharpness','Sharpness',0,20,'','',''),
    Parameter('dnr','Noise reduction: 0 off / 1 low / 2 mid / 3 high',0,3,'','',''),
    Parameter('mirror','Mirror',0,1,'','',''),
    Parameter('flip','Flip',0,1,'','',''),
    Parameter('digital_zoom','Digital zoom x 10 (LAB)',10,160,'','',''),
]}

class LabMarshall:
    """UI/state testing model only. It never transmits guessed VISCA commands."""
    def __init__(self):
        self.values={k:p.low for k,p in MARSHALL_LAB.items()}
        self.values.update(red_gain=128,blue_gain=128,wb_mode=1)
        self.osd=[]
    def query(self,k):return self.values[k]
    def write(self,k,v):self.values[k]=v;return v
    def stop(self):pass

class Engine:
    def __init__(self,configuration,storage):
        self.config=configuration
        self.storage=pathlib.Path(storage);self.storage.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.closed=threading.Event()
        self.cameras={}
        self.events=collections.deque(maxlen=500)
        self.revision=0
        self.threads=[]
        self.ross_status={'state':'Not Connected','preset_follow':'not connected'}
        self.tsl={'enabled':False,'listening':False,'last_packet':None,'packets':0,'messages':0,'invalid_packets':0,'rejected_sources':0,'source':None}
        names_path=self.storage/'preset-names.json'
        self.preset_names=json.loads(names_path.read_text()) if names_path.exists() else {}
        speeds_path=self.storage/'preset-speeds.json'
        self.preset_speeds=json.loads(speeds_path.read_text()) if speeds_path.exists() else {}
        for c in configuration['cameras']:
            if not c.get('enabled',True):continue
            lab=c['driver']=='marshall-lab'
            sony=c['driver']=='sony-sdk'
            serial=c['driver']=='panasonic-serial'
            if not lab and not sony and not serial and c['driver']!='panasonic':
                raise ValueError('Unsupported production driver; no guessed Marshall serial commands')
            definitions=serial_parameters() if serial else SONY if sony else MARSHALL_LAB if lab else panasonic_parameters(c.get('model','AW-HE130'))
            driver=PanasonicSerial(c['host'],c['port']) if serial else Sony(c,storage) if sony else LabMarshall() if lab else Panasonic(c['host'],c.get('port',80),model=c.get('model','AW-HE130'))
            self.cameras[c['id']]={'config':c,'driver':driver,'defs':definitions,'io':CameraAccess(),
                'params':{k:{'value':None,'requested':None,'confirmation':'unknown','last_query':None,'last_command':None,'error':None} for k in definitions},
                'pending':{},'owner':None,'lease_until':0,'generation':0,'motion_deadline':0,'moving':False,'locked':False,'error':None,
                'health':'unknown','last_poll':0,'active_preset':None,'white_balance_once':None,
                'tally':{'enabled':c.get('tally_enabled',True),'requested':None,'actual':None,'status':'unknown' if c.get('tally_enabled',True) else 'disabled','source':None,'updated':None},'tally_pending':None}

    def event(self,camera,kind,**data):
        with self.lock:
            self.revision+=1
            self.events.append(dict(time=time.time(),camera=camera,kind=kind,**data))

    def start(self):
        for cid in self.cameras:
            thread=threading.Thread(target=self.worker,args=(cid,),daemon=True,name='camera-'+cid)
            thread.start();self.threads.append(thread)
        t=threading.Thread(target=self.watchdog,daemon=True,name='movement-watchdog');t.start();self.threads.append(t)

    def snapshot(self):
        now=time.time()
        with self.lock:
            result=[]
            for cid,c in self.cameras.items():
                parameters={}
                for key,v in c['params'].items():
                    age=None if v['last_query'] is None else now-v['last_query']
                    status='stale' if age is not None and age>max(10,self.config.get('poll_seconds',4)*3) and v['confirmation']=='confirmed' else v['confirmation']
                    parameters[key]=dict(c['defs'][key].metadata(),**v)
                    parameters[key].update(confirmation=status,age_seconds=age)
                    if isinstance(c['driver'],(Sony,Panasonic)):parameters[key].update(c['driver'].metadata(key))
                result.append(dict(c['config'],parameters=parameters,preset_names=dict(self.preset_names.get(cid,{})),preset_speeds=dict(self.preset_speeds.get(cid,{})),white_balance_once=c['white_balance_once'],health=c['health'],error=c['error'],locked=c['locked'],
                    owner=c['owner'] if c['lease_until']>time.monotonic() else None,generation=c['generation'],moving=c['moving'],active_preset=c['active_preset'],tally=dict(c['tally'])))
                if isinstance(c['driver'],Panasonic):result[-1]['capabilities']=dict(c['driver'].capabilities)
            tsl=dict(self.tsl)
            tsl['age_seconds']=None if tsl['last_packet'] is None else max(0,now-tsl['last_packet'])
            tsl['state']='disabled' if not tsl['enabled'] else 'not listening' if not tsl['listening'] else 'waiting' if tsl['last_packet'] is None else 'receiving' if tsl['age_seconds']<=10 else 'stale'
            return {'revision':self.revision,'time':now,'cameras':result,'ross':dict(self.ross_status),'tsl':tsl,'events':list(self.events)}

    def claim(self,c,owner):
        if not isinstance(owner,str) or not 1<=len(owner)<=100:raise ValueError('Invalid owner')
        if c['locked']:raise PermissionError('Camera locked')
        now=time.monotonic()
        if c['owner']!=owner and c['lease_until']>now:raise PermissionError('Camera owned by another controller')
        c['owner']=owner;c['lease_until']=now+3

    def command(self,cid,action,data,owner):
        c=self.cameras[cid]
        if action=='tally':return self.set_tally(cid,data.get('program',False),data.get('preview',False),'manual')
        if action=='stop':
            self.stop(cid,active_only=data.get('active_only') is True);return {'status':'stop sent'}
        if action=='claim':
            with self.lock:self.claim(c,owner)
            return {'generation':c['generation']}
        if action=='lock':
            self.stop(cid)
            with self.lock:c['locked']=bool(data['value'])
            return {'locked':c['locked']}
        with self.lock:
            self.claim(c,owner)
            if action=='label_preset':
                from .protocol import preset
                preset(data['number'])
                name=data['name']
                if not isinstance(name,str) or not 1<=len(name)<=80:raise ValueError('Shot name must contain 1..80 characters')
                if 'speed' in data:self.validate_preset_speed(c,data['speed'])
                self.preset_names.setdefault(cid,{})[str(data['number'])]=name
                target=self.storage/'preset-names.json';temporary=target.with_suffix('.tmp')
                temporary.write_text(json.dumps(self.preset_names,indent=2));temporary.replace(target)
                if 'speed' in data:self.save_preset_speed(cid,data['number'],data['speed'])
                self.event(cid,'shot-name',number=data['number'])
                return {'status':'name saved'}
            if action=='write':
                key=data['parameter'];value=c['defs'][key].validate(data['value'])
                if isinstance(c['driver'],Panasonic) and not c['driver'].metadata(key)['writable']:raise ValueError('Control unavailable in this camera profile')
                if isinstance(c['driver'],Sony) and data.get('snap') is True:value=c['defs'][key].validate(c['driver'].snap(key,value))
                self.check_mode(c,key)
                c['pending'][key]=(value,c['generation'],owner)
                c['params'][key].update(requested=value,confirmation='pending',last_command=time.time(),error=None)
                self.event(cid,'queued',parameter=key,value=value)
                return {'status':'queued'}
            if action=='move':
                if c['config']['manufacturer'] not in ('Panasonic','Sony'):raise ValueError('Fixed camera has no mechanical PTZ')
                if isinstance(c['driver'],Sony) and (data.get('pan',0) or data.get('tilt',0)):raise ValueError('PXW-Z200 has no pan/tilt motors')
                if data.get('generation')!=c['generation']:raise ValueError('Stale motion generation; claim again')
                axes={k:data.get(k,0) for k in ('pan','tilt','zoom','focus')}
                if isinstance(c['driver'],Panasonic):
                    for keys,cap in [(('pan','tilt'),'pan_tilt'),(('zoom',),'zoom_jog'),(('focus',),'focus_jog')]:
                        if any(axes[k] for k in keys) and not c['driver'].capabilities[cap]:raise ValueError('Camera does not support '+cap)
                from .protocol import movement
                movement(**axes)
                if axes['focus']:self.check_mode(c,'focus')
                c['motion_deadline']=time.monotonic()+0.9
                c['moving']=any(axes.values())
                c['pending']['@motion']=(axes,c['generation'],owner)
                return {'status':'queued','watchdog_ms':900}
        if action=='white_balance_once':
            if not isinstance(c['driver'],Panasonic):raise ValueError('One Shot is unavailable for this profile')
            try:
                with c['io']:result=c['driver'].white_balance_once()
            except Exception as error:
                with self.lock:c['white_balance_once']={'status':'failed','error':str(error)[:180],'time':time.time(),'completion':'unavailable'}
                raise
            with self.lock:c['white_balance_once']=result
            self.event(cid,'white-balance-once',status=result['status'])
            return result
        if action=='preset':
            if c['config']['manufacturer']!='Panasonic':raise ValueError('PTZ presets unavailable')
            store=data.get('store',False)
            if store and data.get('confirm')!='OVERWRITE':raise ValueError('Preset storage requires OVERWRITE confirmation')
            from .protocol import preset
            preset(data['number'],store)
            speed=data.get('speed',self.preset_speeds.get(cid,{}).get(str(data['number'])))
            if speed is not None:self.validate_preset_speed(c,speed)
            self.stop(cid)
            with c['io']:
                if speed is not None and not store:c['driver'].recall_speed(speed)
                c['driver'].preset(data['number'],store)
            if store and speed is not None:self.save_preset_speed(cid,data['number'],speed)
            with self.lock:c['active_preset']={'number':data['number'],'speed':speed,'speed_confirmation':'saved' if store else 'confirmed' if speed is not None else 'camera default','state':'last command sent, unverified'}
            self.event(cid,'preset',number=data['number'],store=store)
            return {'status':'last command sent, unverified'}
        if action=='osd':
            if not isinstance(c['driver'],LabMarshall):raise ValueError('OSD protocol not verified for hardware')
            if data['key'] not in ('menu','up','down','left','right','enter','back'):raise ValueError('Unknown OSD key')
            c['driver'].osd.append(data['key']);self.event(cid,'lab-osd',key=data['key'])
            return {'status':'simulator only'}
        raise ValueError('Unknown action')

    def validate_preset_speed(self,c,speed):
        if type(speed) is not int or not 1<=speed<=30:raise ValueError('Recall speed must be 1..30')
        if not isinstance(c['driver'],Panasonic) or not c['driver'].capabilities['preset_speed']:raise ValueError('Preset speed is unavailable for this profile')

    def save_preset_speed(self,cid,number,speed):
        with self.lock:
            self.preset_speeds.setdefault(cid,{})[str(number)]=speed
            target=self.storage/'preset-speeds.json';temporary=target.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.preset_speeds,indent=2));temporary.replace(target)

    def check_mode(self,c,key):
        requirement='focus_auto=2' if isinstance(c['driver'],Sony) and key=='focus' else c['defs'][key].dependency
        if c['config']['manufacturer']=='Marshall':
            if key in ('red_gain','blue_gain'):requirement='wb_mode=1'
            if key in ('gain','shutter'):requirement='exposure_auto=0'
        if not requirement:return
        mode,raw=requirement.split('=');state=c['params'][mode]
        if state['confirmation']!='confirmed' or state['last_query'] is None or time.time()-state['last_query']>10 or state['value'] not in [int(x) for x in raw.split(',')]:
            raise ValueError('Manual adjustment requires fresh confirmed '+requirement)

    def set_tally(self,cid,program,preview=False,source='manual'):
        if type(program) is not bool or type(preview) is not bool:raise ValueError('Tally values must be true or false')
        c=self.cameras[cid]
        with self.lock:
            if source=='TSL 3.1':c['tally'].update(received={'program':program,'preview':preview},received_time=time.time())
            if not c['config'].get('tally_enabled',True):return {'status':'disabled for this camera'}
            desired={'program':program,'preview':preview}
            t=c['tally']
            if t['requested']==desired and t['status'] in ('pending','confirmed','unsupported'):return {'status':t['status']}
            t.update(requested=desired,status='pending',source=source,updated=time.time())
            c['tally_pending']=dict(desired)
            self.revision+=1
        return {'status':'queued'}

    def stop(self,cid,active_only=False):
        c=self.cameras[cid]
        with self.lock:
            c['generation']+=1;c['pending'].pop('@motion',None);c['moving']=False;c['motion_deadline']=0
        try:
            with c['io'].priority(-20):
                if isinstance(c['driver'],Panasonic):c['driver'].stop(active_only=active_only)
                else:c['driver'].stop()
            self.event(cid,'stop')
        except Exception:
            with self.lock:c['error']='Stop delivery failed; physical status unknown';c['health']='error'
            self.event(cid,'stop-failed')
            raise

    def watchdog(self):
        while not self.closed.wait(0.05):
            with self.lock:due=[cid for cid,c in self.cameras.items() if c['moving'] and time.monotonic()>c['motion_deadline']]
            for cid in due:
                try:self.stop(cid)
                except Exception:pass

    def worker(self,cid):
        c=self.cameras[cid];driver=c['driver']
        next_poll=0;poll_keys=iter(())
        while not self.closed.is_set():
            with self.lock:
                tally=c['tally_pending'];c['tally_pending']=None
            if tally is not None:
                try:
                    if not hasattr(driver,'tally'):raise NotImplementedError('No tally driver for this camera')
                    with c['io'].priority(5):actual=driver.tally(**tally)
                    expected={'program':tally['program'],'preview':tally['preview'] if isinstance(driver,Sony) else False}
                    with self.lock:c['tally'].update(actual=actual,status='sent' if actual.get('delivery')=='sent' else 'confirmed' if actual==expected else 'mismatch',error=None,updated=time.time());self.revision+=1
                    self.event(cid,'tally-readback',actual=actual)
                except Exception as exc:
                    with self.lock:c['tally'].update(status='unsupported' if isinstance(exc,NotImplementedError) else 'error',error=str(exc)[:180],updated=time.time());self.revision+=1
                continue
            try:
                with self.lock:
                    item=next(iter(c['pending'].items()),None)
                    if item:c['pending'].pop(item[0])
                if item:
                    key,(value,generation,owner)=item
                    with c['io']:
                        with self.lock:
                            valid=generation==c['generation'] and owner==c['owner'] and c['lease_until']>time.monotonic() and not c['locked']
                        if not valid:
                            if key!='@motion':
                                with self.lock:c['params'][key].update(confirmation='unknown',error='Ownership expired or command superseded')
                            continue
                        if key=='@motion':
                            driver.move(**value)
                            self.event(cid,'motion-sent',axes=dict(value))
                        else:
                            with self.lock:self.check_mode(c,key)
                            actual=driver.write(key,value)
                            with self.lock:
                                c['params'][key].update(value=actual,confirmation='sent' if isinstance(driver,PanasonicSerial) and not driver.metadata(key)['readback'] else 'confirmed' if actual==value else 'mismatch',last_query=time.time(),error=None)
                                if not c['moving'] and not c['pending'] and c['owner']==owner:c['owner']=None;c['lease_until']=0
                            self.event(cid,'readback',parameter=key,value=actual)
                elif time.monotonic()>=next_poll:
                    with self.lock:moving=c['moving']
                    if moving:
                        self.closed.wait(.03);continue
                    with c['io'].priority(10):
                        # Motion may have started while this poll waited. Never
                        # sleep with camera access held, or poll ahead of a jog.
                        with self.lock:moving=c['moving']
                        if moving:continue
                        try:key=next(poll_keys)
                        except StopIteration:
                            if hasattr(driver,'tally_state'):
                                try:
                                    actual_tally=driver.tally_state()
                                    with self.lock:c['tally'].update(actual=actual_tally,readback_status='confirmed',readback_time=time.time())
                                except Exception as exc:
                                    with self.lock:c['tally'].update(readback_status='unavailable',readback_error=str(exc)[:100])
                            poll_keys=iter(c['defs'])
                            # Release access after tally readback so that a waiting
                            # stop or jog can run before the next parameter query.
                            continue
                        actual=driver.query(key)
                        with self.lock:
                            v=c['params'][key]
                            v.update(value=actual,last_query=time.time(),error=None)
                            if v['confirmation']!='pending':v['confirmation']='confirmed' if actual is not None else 'sent' if isinstance(driver,PanasonicSerial) and v['last_command'] and driver.metadata(key)['writable'] else 'unavailable' if isinstance(driver,PanasonicSerial) and driver.metadata(key)['writable'] else 'unsupported'
                            c['health']='simulated' if c['config'].get('simulator') else 'online';c['error']=None
                            self.revision+=1
                        # Spread queries; finish a round without a burst.
                        if key!=list(c['defs'])[-1]:next_poll=time.monotonic()+0.15
                        else:next_poll=time.monotonic()+self.config.get('poll_seconds',4)
                else:self.closed.wait(0.03)
            except Exception as exc:
                with self.lock:
                    c['health']='error';c['error']=type(exc).__name__
                    if item and item[0]!='@motion':c['params'][item[0]].update(confirmation='error',error=type(exc).__name__)
                    for pending_key in c['pending']:
                        if pending_key!='@motion':c['params'][pending_key].update(confirmation='error',error='Cancelled after communication failure')
                    c['pending'].clear()
                self.event(cid,'communication-error',error=type(exc).__name__)
                if c['moving']:
                    try:self.stop(cid)
                    except Exception:pass
                self.closed.wait(0.5);next_poll=time.monotonic()+1

    def capture(self,cid,name,notes=''):
        c=self.cameras[cid]
        if not isinstance(name,str) or not 1<=len(name)<=80:raise ValueError('Snapshot name required')
        with self.lock:
            values={k:v['value'] for k,v in c['params'].items() if k not in ('zoom','focus') and v['confirmation']=='confirmed' and v['last_query'] and time.time()-v['last_query']<10}
            snap={'name':name,'notes':str(notes)[:1000],'camera':cid,'model':c['config']['model'],'capture_time':time.time(),'values':values,'simulator':c['config'].get('simulator',False)}
        path=self.storage/'snapshots.json'
        with self.lock:
            existing=json.loads(path.read_text()) if path.exists() else {}
            existing[name]=snap
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(existing,indent=2));tmp.replace(path)
        return snap

    def close(self):
        self.closed.set()
        for cid in self.cameras:
            try:self.stop(cid)
            except Exception:pass
        for t in self.threads:t.join(3)
        for c in self.cameras.values():
            try:
                if c['config'].get('tally_enabled',True) and ((c['tally']['actual'] and any(c['tally']['actual'].values())) or (isinstance(c['driver'],PanasonicSerial) and (c['tally']['requested'] or {}).get('program'))):
                    with c['io']:c['driver'].tally(False,False)
            except Exception:pass
            if hasattr(c['driver'],'close'):c['driver'].close()
