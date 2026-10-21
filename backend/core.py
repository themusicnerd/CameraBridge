"""Central state, exclusive camera ownership, write coalescing and motion watchdog."""
import collections
import json
import pathlib
import threading
import time
from .protocol import PANASONIC,Parameter
from .drivers import Panasonic

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
        for c in configuration['cameras']:
            if not c.get('enabled',True):continue
            lab=c['driver']=='marshall-lab'
            if not lab and c['driver']!='panasonic':
                raise ValueError('Unsupported production driver; no guessed Marshall serial commands')
            definitions=MARSHALL_LAB if lab else PANASONIC
            driver=LabMarshall() if lab else Panasonic(c['host'],c.get('port',80))
            self.cameras[c['id']]={'config':c,'driver':driver,'defs':definitions,'io':threading.RLock(),
                'params':{k:{'value':None,'requested':None,'confirmation':'unknown','last_query':None,'last_command':None,'error':None} for k in definitions},
                'pending':{},'owner':None,'lease_until':0,'generation':0,'motion_deadline':0,'moving':False,'locked':False,'error':None,
                'health':'unknown','last_poll':0,'active_preset':None}

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
                result.append(dict(c['config'],parameters=parameters,health=c['health'],error=c['error'],locked=c['locked'],
                    owner=c['owner'] if c['lease_until']>time.monotonic() else None,generation=c['generation'],moving=c['moving'],active_preset=c['active_preset']))
            return {'revision':self.revision,'time':now,'cameras':result,'ross':{'state':'unverified','preset_follow':'not connected'},'events':list(self.events)}

    def claim(self,c,owner):
        if not isinstance(owner,str) or not 1<=len(owner)<=100:raise ValueError('Invalid owner')
        if c['locked']:raise PermissionError('Camera locked')
        now=time.monotonic()
        if c['owner']!=owner and c['lease_until']>now:raise PermissionError('Camera owned by another controller')
        c['owner']=owner;c['lease_until']=now+3

    def command(self,cid,action,data,owner):
        c=self.cameras[cid]
        if action=='stop':
            self.stop(cid);return {'status':'stop sent'}
        if action=='claim':
            with self.lock:self.claim(c,owner)
            return {'generation':c['generation']}
        if action=='lock':
            self.stop(cid)
            with self.lock:c['locked']=bool(data['value'])
            return {'locked':c['locked']}
        with self.lock:
            self.claim(c,owner)
            if action=='write':
                key=data['parameter'];value=c['defs'][key].validate(data['value'])
                self.check_mode(c,key)
                c['pending'][key]=(value,c['generation'],owner)
                c['params'][key].update(requested=value,confirmation='pending',last_command=time.time(),error=None)
                self.event(cid,'queued',parameter=key,value=value)
                return {'status':'queued'}
            if action=='move':
                if c['config']['manufacturer']!='Panasonic':raise ValueError('Fixed camera has no mechanical PTZ')
                if data.get('generation')!=c['generation']:raise ValueError('Stale motion generation; claim again')
                axes={k:data.get(k,0) for k in ('pan','tilt','zoom','focus')}
                from .protocol import movement
                movement(**axes)
                if axes['focus']:self.check_mode(c,'focus')
                c['motion_deadline']=time.monotonic()+0.9
                c['moving']=any(axes.values())
                c['pending']['@motion']=(axes,c['generation'],owner)
                return {'status':'queued','watchdog_ms':900}
        if action=='preset':
            if c['config']['manufacturer']!='Panasonic':raise ValueError('PTZ presets unavailable')
            store=data.get('store',False)
            if store and data.get('confirm')!='OVERWRITE':raise ValueError('Preset storage requires OVERWRITE confirmation')
            self.stop(cid)
            with c['io']:c['driver'].preset(data['number'],store)
            with self.lock:c['active_preset']={'number':data['number'],'state':'last command sent, unverified'}
            self.event(cid,'preset',number=data['number'],store=store)
            return {'status':'last command sent, unverified'}
        if action=='osd':
            if not isinstance(c['driver'],LabMarshall):raise ValueError('OSD protocol not verified for hardware')
            if data['key'] not in ('menu','up','down','left','right','enter','back'):raise ValueError('Unknown OSD key')
            c['driver'].osd.append(data['key']);self.event(cid,'lab-osd',key=data['key'])
            return {'status':'simulator only'}
        raise ValueError('Unknown action')

    def check_mode(self,c,key):
        requirement=c['defs'][key].dependency
        if c['config']['manufacturer']=='Marshall':
            if key in ('red_gain','blue_gain'):requirement='wb_mode=1'
            if key in ('gain','shutter'):requirement='exposure_auto=0'
        if not requirement:return
        mode,raw=requirement.split('=');state=c['params'][mode]
        if state['confirmation']!='confirmed' or state['last_query'] is None or time.time()-state['last_query']>10 or state['value'] not in [int(x) for x in raw.split(',')]:
            raise ValueError('Manual adjustment requires fresh confirmed '+requirement)

    def stop(self,cid):
        c=self.cameras[cid]
        with self.lock:
            c['generation']+=1;c['pending'].pop('@motion',None);c['moving']=False;c['motion_deadline']=0
        try:
            with c['io']:c['driver'].stop()
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
                        if key=='@motion':driver.move(**value)
                        else:
                            with self.lock:self.check_mode(c,key)
                            actual=driver.write(key,value)
                            with self.lock:c['params'][key].update(value=actual,confirmation='confirmed' if actual==value else 'mismatch',last_query=time.time(),error=None)
                            self.event(cid,'readback',parameter=key,value=actual)
                elif time.monotonic()>=next_poll:
                    with c['io']:
                        with self.lock:moving=c['moving']
                        if moving:
                            self.closed.wait(.03);continue
                        try:key=next(poll_keys)
                        except StopIteration:
                            poll_keys=iter(c['defs']);key=next(poll_keys)
                            next_poll=time.monotonic()+self.config.get('poll_seconds',4)
                        actual=driver.query(key)
                        with self.lock:
                            v=c['params'][key]
                            v.update(value=actual,last_query=time.time(),error=None)
                            if v['confirmation']!='pending':v['confirmation']='confirmed'
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
