"""AK-HC1800G on AW-PH360N through a transparent TCP/RS-422 gateway.

Panasonic Convertible Protocol v3.05, camera pages 2-6, head pages 29-32.
Camera frames use STX/ETX and ACK plus a result. Head frames end with CR.
A transmitted head command is not a camera acknowledgement.
"""
import re
import socket
import threading
import time
from dataclasses import replace
from .drivers import Panasonic,PanasonicRejected
from .protocol import PANASONIC,movement,preset
from .trace import record

MODEL='AK-HC1800G + AW-PH360N'

def parameters():
    result=dict(PANASONIC)
    for key in ('iris','focus'):
        result[key]=replace(result[key],dependency='')
    for key in ('red_gain','blue_gain'):
        result[key]=replace(result[key],dependency='',label=key.replace('_',' ').title()+' (150 = zero; 5 = one camera step)')
    return result

class PanasonicSerial(Panasonic):
    def __init__(self,host,port,timeout=.8):
        if not host or any(c in host for c in '/@?#:'):raise ValueError('Use a bare gateway address')
        self.host=host;self.port=int(port);self.timeout=timeout;self.model=MODEL
        self.parameters=parameters();self.lock=threading.RLock();self.last=0
        self.socket=None;self.buffer=bytearray();self.connected=False
        self.motion_state={}
        self.supported={'iris_auto','iris','red_gain','blue_gain','detail'}
        self.capabilities=dict(pan_tilt=True,pan_tilt_type='mechanical',zoom_jog=True,focus_jog=True,
            preset_max=50,preset_speed=False,gain_display_divisor=5,gain_display_multiplier=3,
            gain_constraint='gain_range_hc1800',hardware_tested=False,
            transport='tcp-serial',motion_feedback='sent, unverified',
            compatibility='AK-HC1800G on AW-PH360N; transparent TCP to RS-422, 9600 8N1')

    def metadata(self,name):
        return dict(supported=name in self.supported,writable=name in self.supported,
            readback=name in ('red_gain','blue_gain','detail'),
            display_divisor=5 if name in ('red_gain','blue_gain') else 1,
            display_multiplier=3 if name in ('red_gain','blue_gain') else 1)

    def close(self):
        if self.socket is not None:
            try:self.socket.close()
            except OSError:pass
        self.socket=None;self.buffer.clear();self.connected=False;self.motion_state.clear()

    def _frame(self,deadline):
        while True:
            while self.buffer and self.buffer[0]==6:del self.buffer[0]
            if self.buffer:
                if self.buffer[0]==2:
                    end=self.buffer.find(3,1)
                    if end>=0:
                        data=bytes(self.buffer[1:end]);del self.buffer[:end+1]
                        return data.decode('ascii')
                else:
                    end=self.buffer.find(13)
                    if end>=0:
                        data=bytes(self.buffer[:end]);del self.buffer[:end+1]
                        return data.decode('ascii')
                if len(self.buffer)>512:raise ValueError('Oversized serial reply')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('No complete camera reply; gateway write is not feedback')
            self.socket.settimeout(remaining)
            chunk=self.socket.recv(256)
            if not chunk:raise ConnectionError('Serial gateway closed')
            self.buffer.extend(chunk)

    def send(self,command,response=True):
        if not re.fullmatch(r'[#A-Z0-9:]+',command):raise ValueError('Invalid serial command')
        head=command.startswith('#')
        # Legacy head jog/store/tally commands have no required acknowledgement.
        if head and response:raise ValueError('Legacy head readback is unavailable')
        prefix=None if head else command.replace('Q','O',1).split(':')[0]
        started=time.monotonic()
        with self.lock:
            try:
                if self.socket is None:
                    self.socket=socket.create_connection((self.host,self.port),self.timeout)
                    self.connected=True;record('serial-connected',host=self.host,port=self.port)
                delay=.13-(time.monotonic()-self.last)
                if delay>0:time.sleep(delay)
                packet=command.encode('ascii')+b'\r' if head else b'\x02'+command.encode('ascii')+b'\x03'
                record('serial-send',host=self.host,port=self.port,command=command,hex=packet.hex(' '),wait_ms=round((time.monotonic()-started)*1000,3),feedback_expected=bool(response))
                self.socket.settimeout(self.timeout)
                self.socket.sendall(packet)
                if not response:return None
                deadline=time.monotonic()+self.timeout
                for _ in range(32):
                    reply=self._frame(deadline)
                    record('serial-reply',command=command,reply=reply)
                    if reply.startswith(('ER','eR')):raise PanasonicRejected(reply)
                    # Ignore unrelated notifications and delayed head echoes.
                    if reply.split(':')[0]==prefix:return reply
                raise ValueError('Too many unrelated serial replies')
            except Exception:
                self.close()
                raise
            finally:self.last=time.monotonic()

    def query(self,name):
        if name not in self.supported or name in ('iris','iris_auto'):
            # Keep health tied to an actual camera reply, not just a TCP socket.
            if name=='iris_auto' and not self.send('QID').startswith('OID:'):raise ValueError('Malformed camera identification')
            return None
        if name in ('red_gain','blue_gain'):
            reply=self.send('QGR' if name=='red_gain' else 'QGB')
            prefix='OGR:' if name=='red_gain' else 'OGB:'
            if not re.fullmatch(prefix+r'[0-9A-Fa-f]{2}',reply):raise ValueError('Malformed legacy gain feedback')
            return self.parameters[name].validate(int(reply[4:],16)*5)
        return self.parameters[name].decode(self.send(self.parameters[name].query))

    def write(self,name,value):
        if name not in self.supported:raise NotImplementedError('Control unavailable for AK-HC1800G / AW-PH360N')
        self.parameters[name].validate(value)
        if name in ('iris','iris_auto'):
            if name=='iris_auto':command='#D3'+str(value)
            else:command='#I'+f'{1+round((value-0x555)*98/(0xFFF-0x555)):02d}'
            self.send(command,response=False);return None
        if name in ('red_gain','blue_gain'):
            if value%5:raise ValueError('Legacy gain uses native steps of 5')
            self.send(('ORG:' if name=='red_gain' else 'OBG:')+f'{value//5:02X}')
        else:self.send(self.parameters[name].encode(value))
        return self.query(name)

    def send_motion(self,command):
        axis='#PTS' if command.startswith('#PTS') else command[:2]
        if not (re.fullmatch(r'#PTS[0-9]{4}',command) or re.fullmatch(r'#[ZF][0-9]{2}',command)):raise ValueError('Invalid head movement')
        self.motion_state.pop(axis,None)
        # PH360 uses separate pan and tilt speed commands, not integrated #PTS.
        commands=['#P'+command[4:6],'#T'+command[6:8]] if axis=='#PTS' else [command]
        for wire in commands:self.send(wire,response=False)
        self.motion_state[axis]=command

    def preset(self,number,store=False):
        preset(number,store)
        if number>50:raise ValueError('AW-PH360N supports shots 1..50')
        self.send(preset(number,store),response=False)

    def recall_speed(self,speed):raise NotImplementedError('AW-PH360N recall speed is not available in this profile')

    def white_balance_once(self):
        self.send('OWS',response=False)
        return dict(status='sent',completion='unavailable',time=time.time())

    def tally(self,program,preview=False):
        self.send('#DA'+str(int(program)),response=False)
        return dict(program=None,preview=None,delivery='sent')

    def tally_state(self):raise NotImplementedError('Legacy tally lamp readback is unavailable')
