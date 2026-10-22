"""Bounded HTTP transport and a serialized shared RS485 gateway transport."""
import socket
import threading
import time
import urllib.request
import urllib.parse
import re
from .panasonic_models import MODELS,capabilities
from .protocol import panasonic_parameters, movement, preset

class PanasonicRejected(ValueError):
    def __init__(self,reply):
        self.reply=reply
        super().__init__('Camera rejected command: '+reply[:32])

class Panasonic:
    def __init__(self, host, port=80, timeout=0.8, model='AW-HE130'):
        if not host or any(c in host for c in '/@?#:'):
            raise ValueError('Use a bare IPv4 address or hostname')
        self.url = f'http://{host}:{int(port)}/cgi-bin/'
        self.timeout = timeout
        self.model=model
        self.parameters=panasonic_parameters(model)
        self.capabilities=capabilities(model)
        family=MODELS[model]
        self.supported=set(self.parameters) if model in ('AW-HE130','AW-HE40') else {'iris_auto','iris','focus_auto','focus','zoom'}
        if family=='HE2':self.supported={'iris_auto','iris','wb_mode'}
        if family=='UE4':self.supported={'iris_auto'}
        if family in ('UB300','CX350'):self.supported=set()
        self.lock = threading.RLock()
        self.last = 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def metadata(self,name):
        return {'supported':name in self.supported,'writable':name in self.supported,
                'display_divisor':self.capabilities['gain_display_divisor'] if name in ('red_gain','blue_gain') else 1}

    def send(self, command):
        with self.lock:
            # Panasonic recommends a minimum 130ms between requests to one camera.
            delay = 0.13 - (time.monotonic() - self.last)
            if delay > 0:
                time.sleep(delay)
            endpoint = 'aw_ptz' if command.startswith('#') else 'aw_cam'
            url = self.url + endpoint + '?' + urllib.parse.urlencode({'cmd':command,'res':1})
            try:
                with self.opener.open(url, timeout=self.timeout) as response:
                    data = response.read(513)
                if len(data)>512:
                    raise ValueError('Oversized camera reply')
                answer = data.decode('ascii').strip()
                if answer.startswith(('ER','eR')):
                    raise PanasonicRejected(answer)
                return answer
            finally:
                self.last = time.monotonic()

    def query(self, name):
        if name not in self.supported:
            if not self.supported and name==next(iter(self.parameters)):
                if not self.send('QID').startswith('OID:'):raise ValueError('Malformed camera identification')
            return None
        p = self.parameters[name]
        try:
            if self.model=='AW-HE2' and name=='iris':
                answer=self.send('#GI')
                if not re.fullmatch(r'gi[0-9a-fA-F]{3}[01]',answer):raise ValueError('Malformed HE2 iris feedback')
                return p.validate(int(answer[2:5],16))
            answer=self.send(p.query)
            return p.decode(answer)
        except PanasonicRejected as exc:
            # ER3 means unavailable in the current camera mode, not offline.
            # Retest each poll so that manual mode restores feedback.
            if exc.reply.lower().startswith(('er1:','er3:')):return None
            raise

    def write(self, name, value):
        if name not in self.supported:raise NotImplementedError('Control is unavailable in this model profile')
        p = self.parameters[name]
        command = p.encode(value)
        # OAW control uses 1=A,2=B; HE130 query uses 2=A,3=B.
        if self.model!='AW-HE2' and name == 'wb_mode' and value in (2,3):
            command = 'OAW:' + str(value-1)
        self.send(command)
        return self.query(name)

    def move(self, **axes):
        commands=movement(**axes)
        for keys,cap in [(('pan','tilt'),'pan_tilt'),(('zoom',),'zoom_jog'),(('focus',),'focus_jog')]:
            if any(axes.get(k,0) for k in keys) and not self.capabilities[cap]:raise NotImplementedError('This model does not support '+cap)
        for command in self.motion_commands(commands):
            self.send_motion(command)

    def motion_commands(self,commands):
        return [cmd for cmd,cap in zip(commands,('pan_tilt','zoom_jog','focus_jog')) if self.capabilities[cap]]

    def send_motion(self,command):
        try:self.send(command)
        except PanasonicRejected as exc:
            # HE40 rejects even a neutral focus jog in autofocus. Confirm AF
            # before accepting that response; manual-focus stop must succeed.
            if command=='#F50' and exc.reply.lower().startswith('er3:') and self.query('focus_auto')==1:return
            raise

    def stop(self):
        errors=[]
        for command in self.motion_commands(movement()):
            try: self.send_motion(command)
            except Exception as exc: errors.append(exc)
        if errors: raise errors[0]

    def preset(self, number, store=False):
        preset(number,store)
        if number>self.capabilities['preset_max']:raise ValueError('Preset is outside this camera model range')
        self.send(preset(number,store))

    def tally(self,program,preview=False):
        # AW-HE130 CGI: enable network tally input, drive red lamp, read back.
        if self.send('#TAE1')!='tAE1':raise ValueError('Tally input enable was not acknowledged')
        self.send('#DA'+str(int(program)))
        answer=self.send('#DA')
        if answer not in ('dA0','dA1'):raise ValueError('Invalid tally readback')
        return {'program':answer=='dA1','preview':False}

class SerialBus:
    """One instance per TCP endpoint. No retry of ambiguous writes; no fake ACK."""
    def __init__(self, host, port, delay=0.1, timeout=0.5):
        self.host,self.port,self.delay,self.timeout=host,port,delay,timeout
        self.lock=threading.Lock()
        self.socket=None
        self.connected=False
        self.responsive=None

    def exchange(self, packet, expect_reply=False):
        if not packet or len(packet)>32 or packet[-1]!=255:
            raise ValueError('Invalid approved VISCA frame')
        with self.lock:
            try:
                if self.socket is None:
                    self.socket=socket.create_connection((self.host,self.port),self.timeout)
                    self.socket.settimeout(self.timeout)
                self.connected=True
                self.socket.sendall(packet)
                result=b''
                if expect_reply:
                    while not result.endswith(b'\xff'):
                        chunk=self.socket.recv(1)
                        if not chunk: raise ConnectionError('Gateway closed')
                        result+=chunk
                        if len(result)>32: raise ValueError('Oversized serial response')
                    self.responsive=True
                time.sleep(self.delay)
                return result or None
            except socket.timeout:
                # Connected transport is not evidence of an offline camera.
                self.responsive=None
                self.close()
                raise TimeoutError('Serial reply unknown; no automatic write retry')
            except OSError:
                self.close()
                raise

    def close(self):
        if self.socket:
            self.socket.close()
        self.socket=None
        self.connected=False

class Marshall:
    """Fail closed until exact-model commands are backed by approved fixtures."""
    def __init__(self,bus,model,address):
        if model not in ('CV226','CV228') or type(address) is not int or not 1<=address<=7:
            raise ValueError('Marshall model/address require verified profile')
        self.bus,self.model,self.address=bus,model,address

    def write(self,*args):
        raise NotImplementedError('CV226/CV228 exact-model serial command map not verified')
