"""Sony SDK process isolation, pinned SSH identity and capability based controls."""
import ctypes
import ipaddress
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading
import time
from .protocol import Parameter

SONY = {p.id:p for p in [
    Parameter('iris','Iris (f-number x 100)',0,65535,'','','',dependency='iris_auto=2'),
    Parameter('iris_auto','Iris: 1 auto / 2 manual',1,2,'','',''),
    Parameter('focus_auto','Focus: 1 auto / 2 manual',1,2,'','',''),
    Parameter('wb_mode','White balance: 1 auto / 2 manual',1,2,'','',''),
    Parameter('red_gain','Red gain (Sony native)',-32768,65535,'','','',dependency='wb_mode=2'),
    Parameter('blue_gain','Blue gain (Sony native)',-32768,65535,'','','',dependency='wb_mode=2'),
    Parameter('gain','Gain dB (Sony native)',-32768,65535,'','',''),
    Parameter('shutter','Shutter speed (Sony native)',0,4294967295,'','',''),
    Parameter('colour_temperature','White balance temperature',0,65535,'','',''),
    Parameter('zoom','Zoom scale (readback)',0,4294967295,'','',''),
]}

class Blob(ctypes.Structure):
    _fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]

def protect(data, decrypt=False):
    if sys.platform!='win32':return data
    buffer=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    fn=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):raise OSError('Windows credential protection failed')
    try:return ctypes.string_at(target.data,target.size)
    finally:ctypes.windll.kernel32.LocalFree(target.data)

class SonyCredentials:
    def __init__(self,storage):self.root=pathlib.Path(storage)/'sony-access';self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
    def path(self,cid):
        if not cid.isascii() or not cid.replace('_','').isalnum():raise ValueError('Invalid camera ID')
        return self.root/(cid+'.bin')
    def save(self,cid,username,password,fingerprint):
        if not all(isinstance(x,str) and x and len(x)<=1024 and '\x00' not in x for x in (username,password,fingerprint)):raise ValueError('Sony username, password and verified SSH fingerprint are required')
        data=protect(json.dumps(dict(username=username,password=password,fingerprint=fingerprint)).encode())
        target=self.path(cid);temp=target.with_suffix('.tmp')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data)
        temp.replace(target)
        if sys.platform!='win32':target.chmod(0o600)
    def load(self,cid):
        try:return json.loads(protect(self.path(cid).read_bytes(),True))
        except FileNotFoundError:raise PermissionError('Set Sony camera access in Camera setup') from None

def helper_path():
    root=pathlib.Path(getattr(sys,'_MEIPASS',pathlib.Path(__file__).resolve().parents[1]))
    return root/'sony'/('CameraBridge-Sony.exe' if sys.platform=='win32' else 'CameraBridge-Sony')

class SDKProcess:
    def __init__(self,path=None):self.path=pathlib.Path(path or helper_path());self.process=None;self.lock=threading.RLock()
    def request(self,line,timeout=3):
        with self.lock:
            if self.process is None:
                if not self.path.is_file():raise FileNotFoundError('Sony SDK adapter is absent; install the Windows or Linux Sony-enabled package')
                self.responses=queue.Queue(maxsize=16)
                options={'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}
                self.process=subprocess.Popen([str(self.path)],cwd=self.path.parent,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',**options)
                def reader(process,responses):
                    try:
                        for raw in iter(process.stdout.readline,''):
                            if len(raw)>131072:break
                            try:value=json.loads(raw)
                            except ValueError:continue
                            try:responses.put_nowait(value)
                            except queue.Full:break
                    finally:
                        try:responses.put_nowait({'error':'Sony adapter exited'})
                        except queue.Full:pass
                threading.Thread(target=reader,args=(self.process,self.responses),daemon=True).start()
            try:
                self.process.stdin.write(line+'\n');self.process.stdin.flush()
                result=self.responses.get(timeout=timeout)
                if result.get('error'):raise OSError(result['error'])
                return result
            except (queue.Empty,BrokenPipeError):
                self.close();raise TimeoutError('Sony SDK request timed out; connection closed') from None
    def close(self):
        with self.lock:
            process=self.process;self.process=None
            if process:
                try:process.stdin.write('quit\n');process.stdin.flush();process.wait(timeout=.5)
                except (OSError,subprocess.TimeoutExpired,ValueError):process.kill();process.wait(timeout=2)
                for stream in (process.stdin,process.stdout):stream.close()

class Sony:
    def __init__(self,config,storage,process=None):
        self.config=config;self.storage=storage;self.process=process or SDKProcess();self.connected=False;self.capabilities={};self.state_time=0;self.active_axes={'zoom_jog':False,'focus_jog':False}
    def connect(self):
        if self.connected:return
        access=SonyCredentials(self.storage).load(self.config['id'])
        fields=[access[k].encode().hex() for k in ('username','password','fingerprint')]
        self.process.request('connect '+self.config['host']+' '+' '.join(fields),timeout=12)
        self.connected=True
    def state(self,force=False):
        try:
            self.connect()
            if force or time.monotonic()-self.state_time>.3:
                self.capabilities=self.process.request('state')['properties'];self.state_time=time.monotonic()
            return self.capabilities
        except Exception:self.connected=False;self.process.close();raise
    def metadata(self,key):
        p=self.capabilities.get(key,{})
        values=p.get('values',[])
        result={'supported':bool(p),'writable':bool(p.get('writable') and values),'readback':bool(p.get('readable'))}
        if p.get('range') and len(values)==3:result.update(low=values[0],high=values[1],step=values[2],allowed=[])
        elif values:result.update(low=min(values),high=max(values),allowed=values)
        return result
    def query(self,key):
        p=self.state().get(key)
        return p['value'] if p and p.get('readable') else None
    def snap(self,key,value):
        p=self.capabilities.get(key,{})
        values=p.get('values',[])
        if not p.get('writable') or not values:raise ValueError('Sony control is not available')
        if p.get('range') and len(values)==3:
            low,high,step=values
            if step<=0:raise ValueError('Invalid Sony control step')
            return min(high,max(low,low+round((value-low)/step)*step))
        return min(values,key=lambda x:abs(x-value))
    def write(self,key,value):
        p=self.state(True).get(key)
        if not p or not p.get('writable'):raise ValueError('Sony control unavailable in this camera mode')
        self.process.request(f'set {key} {int(value)}')
        # The write response is not setting confirmation. Read independently.
        time.sleep(.15)
        return self.state(True).get(key,{}).get('value')
    def move(self,pan=0,tilt=0,zoom=0,focus=0):
        if pan or tilt:raise ValueError('PXW-Z200 has no pan/tilt motors')
        for key,value in [('zoom_jog',zoom),('focus_jog',focus)]:
            p=self.state().get(key)
            if p and p.get('writable'):
                self.write(key,(value>0)-(value<0));self.active_axes[key]=bool(value)
            elif value or self.active_axes[key]:raise ValueError('Sony lens jog or stop is unavailable in this camera mode')
    def stop(self):
        if self.connected:self.move()
    def tally(self,program,preview=False):
        props=self.state(True)
        if not props.get('tally_red',{}).get('writable'):raise NotImplementedError('External tally lamp control is not supported by the PXW-Z200 SDK profile')
        self.write('tally_red',2 if program else 1)
        if props.get('tally_green',{}).get('writable'):self.write('tally_green',2 if preview and not program else 1)
        return {'program':self.query('tally_red')==2,'preview':self.query('tally_green')==2 if 'tally_green' in props else False}
    def close(self):self.process.close();self.connected=False

def fingerprint(host):
    ipaddress.IPv4Address(host)
    process=SDKProcess()
    try:return bytes.fromhex(process.request('fingerprint '+host,timeout=10)['fingerprint_hex']).decode('utf-8')
    finally:process.close()
