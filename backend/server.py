"""Authenticated local REST/ogScript adapter. Python 3.11+, no external packages."""
import argparse
import hashlib
import hmac
import ipaddress
import json
import pathlib
import secrets
import sqlite3
import threading
import time
import getpass
import os
import sys
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from .core import Engine
from .panasonic_models import MODELS as PANASONIC_MODELS

ROOT=pathlib.Path(__file__).resolve().parent.parent

def default_storage():
    if not getattr(sys,'frozen',False):return ROOT/'runtime'
    if sys.platform=='win32':return pathlib.Path(os.environ.get('LOCALAPPDATA',pathlib.Path.home()/'AppData/Local'))/'CameraBridge'
    if sys.platform=='darwin':return pathlib.Path.home()/'Library/Application Support/CameraBridge'
    return pathlib.Path(os.environ.get('XDG_DATA_HOME',pathlib.Path.home()/'.local/share'))/'camerabridge'

class Auth:
    def __init__(self,path):
        self.path=path
        with closing(sqlite3.connect(path)) as db, db:db.execute('CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY,salt BLOB,hash BLOB,role TEXT)')
        with closing(sqlite3.connect(path)) as db, db:db.execute('CREATE TABLE IF NOT EXISTS device_sessions (token_hash TEXT PRIMARY KEY,name TEXT NOT NULL)')
        self.sessions={};self.failures={};self.lock=threading.Lock()
    def add(self,name,password,role):
        if not isinstance(password,str) or not password:raise ValueError('Password cannot be empty')
        if role not in ('operator','admin'):raise ValueError('Invalid role')
        salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,250000)
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('INSERT OR REPLACE INTO users VALUES(?,?,?,?)',(name,salt,digest,role))
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('DELETE FROM device_sessions WHERE name=?',(name,))
        with self.lock:
            for token,entry in list(self.sessions.items()):
                if entry[2]==name:self.sessions.pop(token,None)
    def login(self,name,password,client):
        now=time.monotonic()
        with self.lock:
            attempts=[x for x in self.failures.get(client,[]) if now-x<60]
            if len(attempts)>=8:raise PermissionError('Login temporarily rate limited')
            attempts.append(now);self.failures[client]=attempts
        with closing(sqlite3.connect(self.path)) as db:row=db.execute('SELECT salt,hash,role FROM users WHERE name=?',(name,)).fetchone()
        digest=hashlib.pbkdf2_hmac('sha256',password.encode(),row[0] if row else bytes(16),250000)
        if not row or not hmac.compare_digest(digest,row[1]):raise PermissionError('Invalid login')
        token=secrets.token_urlsafe(32)
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('INSERT INTO device_sessions VALUES(?,?)',(hashlib.sha256(token.encode()).hexdigest(),name))
        with self.lock:self.sessions[token]=(row[2],float('inf'),name)
        return token,row[2]
    def role(self,token):
        with self.lock:entry=self.sessions.get(token)
        if entry and entry[1]<=time.monotonic():return None
        if entry and entry[2]=='open-access':return entry[0]
        if not token:return None
        with closing(sqlite3.connect(self.path)) as db:
            row=db.execute('SELECT users.role,users.name FROM device_sessions JOIN users USING(name) WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if row:
            with self.lock:self.sessions[token]=(row[0],float('inf'),row[1])
            return row[0]
        with self.lock:self.sessions.pop(token,None)
        return None

    def logout(self,token):
        with self.lock:self.sessions.pop(token,None)
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('DELETE FROM device_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))

def provision_user(auth,name,role):
    """Interactive provisioning: show validation failures without exposing input."""
    print('Create CameraBridge account: '+name+' ('+role+')',flush=True)
    print('Choose a non-empty password. Repeat the same password.',flush=True)
    def read_password(prompt):
        if sys.stdin.isatty():return getpass.getpass(prompt)
        # getpass on Windows reads the console even with a redirected stdin.
        # Read a private pipe directly for scripted account provisioning.
        line=sys.stdin.readline()
        if not line:raise EOFError('Password input ended before account creation.')
        return line.rstrip('\r\n')
    while True:
        password=read_password('New password: ')
        if not password:
            print('Not saved: password cannot be empty. Try again.',flush=True)
            continue
        if password!=read_password('Repeat password: '):
            print('Not saved: passwords differ. Try again.',flush=True)
            continue
        auth.add(name,password,role)
        print('SUCCESS: account saved as a salted password hash.',flush=True)
        return

def validate_config(c):
    if not isinstance(c,dict) or not isinstance(c.get('cameras'),list):raise ValueError('Missing cameras')
    def reject_secrets(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if any(word in key.lower() for word in ('password','secret','token','credential')):raise ValueError('Credentials do not belong in configuration')
                reject_secrets(item)
        elif isinstance(value,list):
            for item in value:reject_secrets(item)
    reject_secrets(c)
    if type(c.get('authentication_enabled',True)) is not bool:raise ValueError('Invalid authentication option')
    ipaddress.ip_address(c.get('bind','127.0.0.1'))
    if not 1024<=c.get('port',8088)<=65535:raise ValueError('Invalid port')
    if not 1<=c.get('poll_seconds',4)<=60:raise ValueError('Poll interval must be 1..60 seconds')
    ids=set();numbers=set()
    for index,camera in enumerate(c['cameras'],1):
        cid=camera['id']
        if not isinstance(cid,str) or not cid.isascii() or not cid.replace('_','').isalnum() or cid in ids:raise ValueError('Invalid or duplicate camera ID')
        ids.add(cid)
        number=camera.setdefault('number',index)
        if type(number) is not int or not 1<=number<=255 or number in numbers:raise ValueError('Camera numbers must be unique integers from 1 through 255')
        numbers.add(number)
        if type(camera.get('enabled',True)) is not bool or type(camera.get('simulator',False)) is not bool:raise ValueError('Invalid camera enable or simulator option')
        camera.setdefault('tally_enabled',True)
        if type(camera['tally_enabled']) is not bool:raise ValueError('Invalid tally enable option')
        if 'tally_address' in camera and (type(camera['tally_address']) is not int or not 0<=camera['tally_address']<=126):raise ValueError('TSL address must be 0..126')
        if camera['driver'] not in ('panasonic','panasonic-serial','marshall-lab','sony-sdk','marshall-pending'):raise ValueError('Driver not implemented')
        if camera['driver'] in ('sony-sdk','marshall-pending'):
            if camera['driver']=='marshall-pending' and camera.get('enabled',True):raise ValueError('This camera profile requires its hardware integration; save it disabled')
            if camera.get('simulator'):raise ValueError('Pending hardware profiles are not simulators')
            expected='Sony' if camera['driver']=='sony-sdk' else 'Marshall'
            if camera.get('manufacturer')!=expected:raise ValueError('Driver/manufacturer mismatch')
            if camera['driver']=='sony-sdk' and camera.get('model')!='PXW-Z200':raise ValueError('Unknown Sony profile')
            if camera['driver']=='marshall-pending' and camera.get('model') not in ('CV226','CV228'):raise ValueError('Unknown Marshall profile')
        if camera['driver']=='marshall-lab' and not camera.get('simulator'):raise ValueError('Marshall lab must be labelled simulator')
        if camera['driver']=='panasonic' and camera['model'] not in PANASONIC_MODELS:raise ValueError('Unknown Panasonic model profile')
        if camera['driver']=='panasonic' and camera.get('simulator') and camera['model']!='AW-HE130':raise ValueError('The Panasonic simulator uses the HE130 profile')
        if camera['driver']=='panasonic-serial':
            from .panasonic_serial import MODEL
            if camera.get('model')!=MODEL:raise ValueError('Unknown Panasonic serial head profile')
            if camera.get('simulator'):raise ValueError('Serial gateways require a real TCP endpoint')
            if 'port' not in camera:raise ValueError('Set the serial gateway TCP port')
        if camera['driver'] in ('panasonic','panasonic-serial','sony-sdk'):
            if camera.get('manufacturer')!=('Sony' if camera['driver']=='sony-sdk' else 'Panasonic'):raise ValueError('Driver/manufacturer mismatch')
            host=camera.get('host','')
            if not isinstance(host,str) or not host or any(x in host for x in '/@?#:'):raise ValueError('Invalid camera host')
            if type(camera.get('port',80)) is not int or not 1<=camera.get('port',80)<=65535:raise ValueError('Invalid camera port')
            if camera['driver']=='sony-sdk':ipaddress.IPv4Address(host)
        if camera['driver']=='marshall-lab' and camera.get('manufacturer')!='Marshall':raise ValueError('Driver/manufacturer mismatch')
        if type(camera.get('pivotcam',False)) is not bool or type(camera.get('allow_store',False)) is not bool:raise ValueError('Invalid PIVOTCam option')
        if camera.get('pivotcam') and camera['driver'] not in ('panasonic','panasonic-serial','sony-sdk'):raise ValueError('PIVOTCam requires Panasonic or Sony')
        from .tracking import validate as validate_tracking
        validate_tracking(camera)
        if 'tracking_calibration' in camera:
            from .calibration import validate as validate_calibration
            validate_calibration(camera['tracking_calibration'])
    tracking_ids=set()
    from .tracking import settings as tracking_settings
    for camera in c['cameras']:
        t=tracking_settings(camera)
        if camera.get('enabled',True) and (t['enabled'] or t['xpression_enabled']):
            for switch,port in [('enabled','port'),('xpression_enabled','xpression_port')]:
                if t[switch]:
                    key=(t['host'],t[port],t['camera_id'])
                    if key in tracking_ids:raise ValueError('Tracking camera IDs must be unique at each destination')
                    tracking_ids.add(key)
    endpoints=[(camera['host'].lower(),camera['port']) for camera in c['cameras'] if camera['driver']=='panasonic-serial' and camera.get('enabled',True)]
    if len(endpoints)!=len(set(endpoints)):raise ValueError('Use one Panasonic head per serial gateway TCP endpoint')
    tally=c.get('tally',{})
    if not isinstance(tally,dict) or type(tally.get('enabled',False)) is not bool:raise ValueError('Invalid tally receiver configuration')
    if tally.get('enabled'):
        ipaddress.IPv4Address(tally.get('bind','127.0.0.1'));ipaddress.IPv4Address(tally.get('source',''))
        if type(tally.get('port',5727)) is not int or not 1024<=tally.get('port',5727)<=65535:raise ValueError('Invalid tally UDP port')
        if type(tally.get('address_offset',0)) is not int or not -1<=tally.get('address_offset',0)<=1:raise ValueError('Invalid tally address offset')
        if type(tally.get('program_tally',2)) is not int or tally.get('program_tally',2) not in (1,2):raise ValueError('Program tally must be 1 or 2')
    pivot=c.get('pivotcam',{})
    if not isinstance(pivot,dict) or type(pivot.get('enabled',False)) is not bool:raise ValueError('Invalid PIVOTCam settings')
    if pivot.get('enabled'):
        if ipaddress.ip_address(pivot.get('bind','127.0.0.1')).version!=4:raise ValueError('PIVOTCam requires an IPv4 listen address')
        if ipaddress.ip_address(pivot.get('controller','')).version!=4:raise ValueError('Set the Carbonite IPv4 address')
        base=pivot.get('base_port',19010)
        if type(base) is not int or not 1024<=base<=65280:raise ValueError('Invalid PIVOTCam base port')
        for camera in c['cameras']:
            if camera.get('enabled',True) and camera.get('pivotcam') and base+camera['number']==c.get('port',8088):raise ValueError('PIVOTCam port conflicts with HTTP port')
    for network in c.get('trusted_hosts',['127.0.0.1/32']):ipaddress.ip_network(network)
    return c

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,engine,auth,lab=False,desktop_control=False):
        self.engine,self.auth,self.lab=engine,auth,lab
        self.desktop_control=desktop_control
        self.setup_lock=threading.RLock()
        self.reconfiguring=False
        self.apply_configuration=None
        self.slots=threading.BoundedSemaphore(24)
        super().__init__(address,Handler)
    def process_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):request.close();return
        try:super().process_request(request,client_address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,*args):
        try:super().process_request_thread(*args)
        finally:self.slots.release()

class Handler(BaseHTTPRequestHandler):
    server_version='CameraBridge/0.2.0rc3'
    def setup(self):
        super().setup();self.connection.settimeout(5)
    def log_message(self,*args):pass
    def send(self,data,status=200,mime='application/json'):
        if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=True).encode()
        self.send_response(status)
        for k,v in [('Content-Type',mime),('Content-Length',str(len(data))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','no-referrer')]:self.send_header(k,v)
        self.end_headers();self.wfile.write(data)
    def trusted(self):
        address=ipaddress.ip_address(self.client_address[0])
        return any(address in ipaddress.ip_network(n) for n in self.server.engine.config.get('trusted_hosts',['127.0.0.1/32']))
    def access_role(self,token):
        return self.server.auth.role(token) if self.server.engine.config.get('authentication_enabled',True) else 'admin'
    def do_GET(self):
        if not self.trusted():self.send({'error':'Management host denied'},403);return
        path=urlsplit(self.path).path
        if path=='/':self.send((ROOT/'web/admin.html').read_bytes(),mime='text/html; charset=utf-8');return
        if path=='/sony':self.send((ROOT/'web/sony.html').read_bytes(),mime='text/html; charset=utf-8');return
        if path=='/help':self.send((ROOT/'web/help.html').read_bytes(),mime='text/html; charset=utf-8');return
        if path in ('/setup.js','/setup.css'):
            self.send((ROOT/'web'/path[1:]).read_bytes(),mime='application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8');return
        if path in ('/assets/camerabridge.svg','/assets/ross.png'):
            self.send((ROOT/'dashboard/assets'/path.rsplit('/',1)[-1]).read_bytes(),mime='image/svg+xml' if path.endswith('.svg') else 'image/png');return
        if path in ('/assets/sony.png','/assets/panasonic.png','/assets/marshall.png'):
            self.send((ROOT/'dashboard/assets'/path.rsplit('/',1)[-1]).read_bytes(),mime='image/png');return
        if path=='/health':self.send({'service':'CameraBridge','mode':'LAB' if self.server.lab else 'hardware','authentication_enabled':self.server.engine.config.get('authentication_enabled',True),'reconfiguring':self.server.reconfiguring});return
        token=self.headers.get('Authorization','').removeprefix('Bearer ')
        role=self.access_role(token)
        if not role and not (self.server.lab and ipaddress.ip_address(self.client_address[0]).is_loopback):self.send({'error':'Authentication required'},401);return
        if path=='/api/state':self.send(self.server.engine.snapshot())
        elif path=='/api/session':self.send({'role':role,'authentication_enabled':self.server.engine.config.get('authentication_enabled',True)})
        elif path=='/api/config' and role=='admin':self.send(self.server.engine.config)
        elif path=='/api/snapshots':
            p=self.server.engine.storage/'snapshots.json';self.send(json.loads(p.read_text()) if p.exists() else {})
        else:self.send({'error':'Not found'},404)
    def do_POST(self):
        if not self.trusted():self.send({'error':'Management host denied'},403);return
        # Never authenticate via cookies. Reject cross-origin browser requests as well.
        origin=self.headers.get('Origin')
        if origin and origin not in ('http://'+self.headers.get('Host',''),'https://'+self.headers.get('Host','')):
            self.send({'error':'Cross-origin request denied'},403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=65536:raise ValueError('Request body must be 1..65536 bytes')
            raw=self.rfile.read(length).decode('utf-8')
            if self.headers.get('Content-Type','').startswith('application/x-www-form-urlencoded') or raw.startswith('request='):
                data=json.loads(parse_qs(raw)['request'][0])
            else:data=json.loads(raw)
            path=urlsplit(self.path).path
            if path=='/api/state' and self.server.lab and ipaddress.ip_address(self.client_address[0]).is_loopback:
                self.send(self.server.engine.snapshot());return
            if path=='/api/login':
                if self.server.engine.config.get('authentication_enabled',True):
                    token,role=self.server.auth.login(data['username'],data['password'],self.client_address[0])
                else:
                    token=secrets.token_urlsafe(32);role='admin'
                    with self.server.auth.lock:self.server.auth.sessions[token]=(role,time.monotonic()+8*3600,'open-access')
                self.send({'token':token,'role':role});return
            token=self.headers.get('Authorization','').removeprefix('Bearer ') or data.pop('token','')
            role=self.access_role(token)
            if not role:raise PermissionError('Authentication required')
            if path=='/api/state':self.send(self.server.engine.snapshot());return
            if path=='/api/setup':
                if role!='admin':raise PermissionError('Administrator required for camera setup')
                from .setup import roster
                self.send(roster(self.server,data));return
            if path=='/api/calibration/capture':
                if role!='admin':raise PermissionError('Administrator required for calibration capture')
                if self.server.reconfiguring:raise ValueError('Camera setup is changing. Try again.')
                from .calibration import capture
                self.send(capture(self.server.engine,data['camera']));return
            if path=='/api/calibration/validate':
                if role!='admin':raise PermissionError('Administrator required for calibration import')
                from .calibration import validate as validate_calibration
                from .tracking import validate as validate_tracking
                profile=data['profile'];head=data['head']
                validate_calibration(profile)
                camera=self.server.engine.cameras[data['camera']]['config']
                if profile['model']!=camera['model']:raise ValueError('Calibration model does not match this camera')
                keys={'pan_zero','tilt_zero','degrees_per_count','pan_invert','tilt_invert','x_mm','y_mm','z_mm','roll'}
                if not isinstance(head,dict) or set(head)!=keys:raise ValueError('Invalid head calibration')
                validate_tracking(dict(camera,tracking_output={**camera.get('tracking_output',{}),**head}))
                self.send(dict(profile=profile,head=head));return
            if path in ('/api/sony/credentials','/api/sony/fingerprint'):
                if role!='admin':raise PermissionError('Administrator required for Sony access setup')
                from .sony import SonyCredentials,fingerprint
                if path.endswith('/fingerprint'):
                    self.send({'fingerprint':fingerprint(data['host'])});return
                cid=data['camera']
                if data.get('acknowledge_terms') is not True:raise ValueError('Acknowledge the Sony SDK terms before saving camera access')
                pending=self.server.engine.storage/'config.pending.json'
                with self.server.setup_lock:
                    configuration=json.loads(pending.read_text(encoding='utf-8')) if pending.exists() else self.server.engine.config
                    if not any(c['id']==cid and c['driver']=='sony-sdk' for c in configuration['cameras']):raise ValueError('Save the Sony camera setup first')
                SonyCredentials(self.server.engine.storage).save(cid,data['username'],data['password'],data['fingerprint'])
                if cid in self.server.engine.cameras:
                    c=self.server.engine.cameras[cid]
                    with c['io']:c['driver'].close()
                self.send({'status':'Sony camera access saved locally; password is not exported'});return
            if path=='/api/command':
                if self.server.reconfiguring:raise ValueError('Camera setup is updating. Try again shortly.')
                if data['action']=='lock' and role!='admin':raise PermissionError('Administrator required for lockout')
                # Ownership is bound to the authenticated session, never a client supplied owner.
                self.send(self.server.engine.command(data['camera'],data['action'],data.get('data',{}),token[:24] or 'open-'+self.client_address[0]));return
            if path=='/api/lab/ross/bus':
                if not self.server.lab or role!='admin' or not hasattr(self.server.engine,'ross_follower'):
                    raise PermissionError('Enabled VISCA lab and administrator required')
                self.send(self.server.engine.ross_follower.bus_event(data['bus'],data['camera']));return
            if path=='/api/service/stop':
                if not self.server.lab or role!='admin':raise PermissionError('Local laboratory administrator required')
                self.send({'status':'lab service stopping'})
                threading.Thread(target=self.server.shutdown,daemon=True).start();return
            if path=='/api/logout':
                self.server.auth.logout(token)
                self.send({'status':'logged out'});return
            if path=='/api/snapshot':self.send(self.server.engine.capture(data['camera'],data['name'],data.get('notes','')));return
            if path=='/api/config' and role=='admin':
                configuration=validate_config(data['configuration'])
                with self.server.setup_lock:
                    target=self.server.engine.storage/'config.pending.json'
                    tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(configuration,indent=2),encoding='utf-8');tmp.replace(target)
                    if data.get('apply') and self.server.desktop_control:
                        restart=self.server.engine.storage/'desktop-restart.json';temporary=restart.with_suffix('.tmp')
                        temporary.write_text(json.dumps({'apply':True}),encoding='utf-8');temporary.replace(restart)
                        self.send({'status':'Camera setup saved. Desktop service restart requested.'});return
                self.send({'status':'Camera setup saved. Select Apply saved camera setup in the desktop control panel, or restart the console with config.pending.json.'});return
            self.send({'error':'Unsupported endpoint or role'},403)
        except PermissionError as exc:self.send({'error':str(exc)},403)
        except (ValueError,KeyError,TypeError) as exc:self.send({'error':str(exc)[:200]},400)
        except Exception:self.send({'error':'Device request failed; see central state'},502)

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(ROOT/'config.example.json'));p.add_argument('--storage',default=str(default_storage()))
    p.add_argument('--lab',action='store_true');p.add_argument('--visca-lab',action='store_true');p.add_argument('--visca-allow-store',action='store_true')
    p.add_argument('--init-user');p.add_argument('--ensure-admin',action='store_true');p.add_argument('--role',choices=['admin','operator'],default='admin')
    p.add_argument('--desktop-control',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
    if a.visca_lab and not a.lab:p.error('--visca-lab requires --lab; physical gateway acceptance is pending')
    if a.visca_allow_store and not a.visca_lab:p.error('--visca-allow-store requires --visca-lab')
    storage=pathlib.Path(a.storage);storage.mkdir(parents=True,exist_ok=True)
    auth=Auth(storage/'credentials.sqlite')
    if a.ensure_admin:
        with closing(sqlite3.connect(auth.path)) as db:has_users=db.execute('SELECT COUNT(*) FROM users').fetchone()[0]>0
        if not has_users:
            provision_user(auth,'admin','admin')
    if a.init_user:
        provision_user(auth,a.init_user,a.role);return
    config=validate_config(json.loads(pathlib.Path(a.config).read_text(encoding='utf-8')))
    if a.lab and (not ipaddress.ip_address(config['bind']).is_loopback or any(not c.get('simulator') for c in config['cameras'] if c.get('enabled',True))):
        raise SystemExit('LAB requires loopback binding and simulator cameras only')
    from .runtime import Runtime
    runtime=Runtime(config,storage,a.visca_lab,a.visca_allow_store)
    service=None
    try:
        runtime.start()
        service=Server((config.get('bind','127.0.0.1'),config.get('port',8088)),runtime.engine,auth,a.lab,a.desktop_control)
        def apply_live(configuration):
            nonlocal runtime
            if any(configuration.get(k,default)!=runtime.config.get(k,default) for k,default in [('bind','127.0.0.1'),('port',8088)]):
                raise ValueError('Change the service address or port in the desktop control panel')
            if a.lab and any(not c.get('simulator') for c in configuration['cameras'] if c.get('enabled',True)):
                raise ValueError('Start the desktop service in hardware mode before adding a real camera')
            old=runtime.config
            service.reconfiguring=True
            candidate=None
            try:
                if runtime.transport_settings(configuration)==runtime.transport_settings(runtime.config):
                    candidate=runtime
                else:
                    runtime.close()
                    candidate=Runtime(configuration,storage,a.visca_lab,a.visca_allow_store)
                    candidate.start()
                paths={pathlib.Path(a.config),storage/'desktop-config.json',storage/'config.pending.json'}
                originals={path:path.read_bytes() if path.exists() else None for path in paths}
                try:
                    for path in paths:
                        temporary=path.with_suffix('.new')
                        temporary.write_text(json.dumps(configuration,indent=2),encoding='utf-8');temporary.replace(path)
                except Exception:
                    for path,content in originals.items():
                        if content is None:path.unlink(missing_ok=True)
                        else:path.write_bytes(content)
                    raise
                if candidate is runtime:runtime.update_metadata(configuration)
                runtime=candidate;service.engine=runtime.engine
                if not old.get('authentication_enabled',True) and configuration.get('authentication_enabled',True):
                    with auth.lock:
                        for token,entry in list(auth.sessions.items()):
                            if entry[2]=='open-access':auth.sessions.pop(token,None)
            except Exception as error:
                if candidate is not None:candidate.close()
                runtime=Runtime(old,storage,a.visca_lab,a.visca_allow_store);runtime.start();service.engine=runtime.engine
                raise ValueError('Setup could not apply. Previous setup restored: '+str(error)[:120]) from error
            finally:service.reconfiguring=False
        service.apply_configuration=apply_live
        if a.desktop_control:
            def parent_control():
                for line in sys.stdin:
                    if line.strip()=='quit':break
                service.shutdown()
            threading.Thread(target=parent_control,daemon=True).start()
        print(f'CameraBridge: http://{service.server_address[0]}:{service.server_address[1]} (LAB={a.lab})',flush=True)
        service.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        runtime.close()
        if service is not None:service.server_close()

if __name__=='__main__':main()
