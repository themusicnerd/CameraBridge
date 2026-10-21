"""Bounded HTTP transport and a serialized shared RS485 gateway transport."""
import socket
import threading
import time
import urllib.request
import urllib.parse
from .protocol import PANASONIC, movement, preset

class Panasonic:
    def __init__(self, host, port=80, timeout=0.8):
        if not host or any(c in host for c in '/@?#:'):
            raise ValueError('Use a bare IPv4 address or hostname')
        self.url = f'http://{host}:{int(port)}/cgi-bin/'
        self.timeout = timeout
        self.lock = threading.RLock()
        self.last = 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

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
                    raise ValueError('Camera rejected command: ' + answer[:32])
                return answer
            finally:
                self.last = time.monotonic()

    def query(self, name):
        p = PANASONIC[name]
        return p.decode(self.send(p.query))

    def write(self, name, value):
        p = PANASONIC[name]
        command = p.encode(value)
        # OAW control uses 1=A,2=B; HE130 query uses 2=A,3=B.
        if name == 'wb_mode' and value in (2,3):
            command = 'OAW:' + str(value-1)
        self.send(command)
        return self.query(name)

    def move(self, **axes):
        for command in movement(**axes):
            self.send(command)

    def stop(self):
        errors=[]
        for command in movement():
            try: self.send(command)
            except Exception as exc: errors.append(exc)
        if errors: raise errors[0]

    def preset(self, number, store=False):
        self.send(preset(number,store))

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
