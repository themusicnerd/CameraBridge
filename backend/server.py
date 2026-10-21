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
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from .core import Engine

ROOT=pathlib.Path(__file__).resolve().parent.parent

class Auth:
    def __init__(self,path):
        self.path=path
        with closing(sqlite3.connect(path)) as db, db:db.execute('CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY,salt BLOB,hash BLOB,role TEXT)')
        self.sessions={};self.failures={};self.lock=threading.Lock()
    def add(self,name,password,role):
        if not isinstance(password,str) or not password:raise ValueError('Password cannot be empty')
        if role not in ('operator','admin'):raise ValueError('Invalid role')
        salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,250000)
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('INSERT OR REPLACE INTO users VALUES(?,?,?,?)',(name,salt,digest,role))
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
        with self.lock:self.sessions[token]=(row[2],now+8*3600,name)
        return token,row[2]
    def role(self,token):
        with self.lock:entry=self.sessions.get(token)
        return entry[0] if entry and entry[1]>time.monotonic() else None

def provision_user(auth,name,role):
    """Interactive provisioning: show validation failures without exposing input."""
    print('Create CameraBridge account: '+name+' ('+role+')',flush=True)
    print('Choose a non-empty password. Input is hidden. Repeat the same password.',flush=True)
    while True:
        password=getpass.getpass('New password: ')
        if not password:
            print('Not saved: password cannot be empty. Try again.',flush=True)
            continue
        if password!=getpass.getpass('Repeat password: '):
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
    ipaddress.ip_address(c.get('bind','127.0.0.1'))
    if not 1024<=c.get('port',8088)<=65535:raise ValueError('Invalid port')
    if not 1<=c.get('poll_seconds',4)<=60:raise ValueError('Poll interval must be 1..60 seconds')
    ids=set()
    for camera in c['cameras']:
        cid=camera['id']
        if not isinstance(cid,str) or not cid.isascii() or not cid.replace('_','').isalnum() or cid in ids:raise ValueError('Invalid or duplicate camera ID')
        ids.add(cid)
        if camera['driver'] not in ('panasonic','marshall-lab'):raise ValueError('Driver not implemented')
        if camera['driver']=='marshall-lab' and not camera.get('simulator'):raise ValueError('Marshall lab must be labelled simulator')
        if camera['driver']=='panasonic' and camera['model']!='AW-HE130':raise ValueError('This release validates HE130 only; other model profiles pending')
        if camera['driver']=='panasonic':
            if camera.get('manufacturer')!='Panasonic':raise ValueError('Driver/manufacturer mismatch')
            host=camera.get('host','')
            if not isinstance(host,str) or not host or any(x in host for x in '/@?#:'):raise ValueError('Invalid camera host')
            if type(camera.get('port',80)) is not int or not 1<=camera.get('port',80)<=65535:raise ValueError('Invalid camera port')
        if camera['driver']=='marshall-lab' and camera.get('manufacturer')!='Marshall':raise ValueError('Driver/manufacturer mismatch')
    for network in c.get('trusted_hosts',['127.0.0.1/32']):ipaddress.ip_network(network)
    return c

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,engine,auth,lab=False):
        self.engine,self.auth,self.lab=engine,auth,lab
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
    server_version='CameraBridge/0.1'
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
    def do_GET(self):
        if not self.trusted():self.send({'error':'Management host denied'},403);return
        path=urlsplit(self.path).path
        if path=='/':self.send((ROOT/'web/admin.html').read_bytes(),mime='text/html; charset=utf-8');return
        if path=='/health':self.send({'service':'CameraBridge','mode':'LAB' if self.server.lab else 'hardware'});return
        token=self.headers.get('Authorization','').removeprefix('Bearer ')
        role=self.server.auth.role(token)
        if not role and not (self.server.lab and ipaddress.ip_address(self.client_address[0]).is_loopback):self.send({'error':'Authentication required'},401);return
        if path=='/api/state':self.send(self.server.engine.snapshot())
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
                token,role=self.server.auth.login(data['username'],data['password'],self.client_address[0])
                self.send({'token':token,'role':role});return
            token=self.headers.get('Authorization','').removeprefix('Bearer ') or data.pop('token','')
            role=self.server.auth.role(token)
            if not role:raise PermissionError('Authentication required')
            if path=='/api/state':self.send(self.server.engine.snapshot());return
            if path=='/api/command':
                if data['action']=='lock' and role!='admin':raise PermissionError('Administrator required for lockout')
                # Ownership is bound to the authenticated session, never a client supplied owner.
                self.send(self.server.engine.command(data['camera'],data['action'],data.get('data',{}),token[:24]));return
            if path=='/api/logout':
                with self.server.auth.lock:self.server.auth.sessions.pop(token,None)
                self.send({'status':'logged out'});return
            if path=='/api/snapshot':self.send(self.server.engine.capture(data['camera'],data['name'],data.get('notes','')));return
            if path=='/api/config' and role=='admin':
                configuration=validate_config(data['configuration'])
                target=self.server.engine.storage/'config.pending.json'
                tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(configuration,indent=2));tmp.replace(target)
                self.send({'status':'validated and saved; restart explicitly with this configuration to apply'});return
            self.send({'error':'Unsupported endpoint or role'},403)
        except PermissionError as exc:self.send({'error':str(exc)},403)
        except (ValueError,KeyError,TypeError) as exc:self.send({'error':str(exc)[:200]},400)
        except Exception:self.send({'error':'Device request failed; see central state'},502)

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(ROOT/'config.example.json'));p.add_argument('--storage',default=str(ROOT/'runtime'))
    p.add_argument('--lab',action='store_true');p.add_argument('--init-user');p.add_argument('--ensure-admin',action='store_true');p.add_argument('--role',choices=['admin','operator'],default='admin');a=p.parse_args()
    storage=pathlib.Path(a.storage);storage.mkdir(parents=True,exist_ok=True)
    auth=Auth(storage/'credentials.sqlite')
    if a.ensure_admin:
        with closing(sqlite3.connect(auth.path)) as db:has_users=db.execute('SELECT COUNT(*) FROM users').fetchone()[0]>0
        if not has_users:
            provision_user(auth,'admin','admin')
    if a.init_user:
        provision_user(auth,a.init_user,a.role);return
    config=validate_config(json.loads(pathlib.Path(a.config).read_text(encoding='utf-8')))
    if a.lab and (not ipaddress.ip_address(config['bind']).is_loopback or any(not c.get('simulator') for c in config['cameras'])):
        raise SystemExit('LAB requires loopback binding and simulator cameras only')
    simulators=[]
    if a.lab:
        from .simulator import server
        for c in config['cameras']:
            if c['driver']=='panasonic':
                sim=server(port=c['port']);threading.Thread(target=sim.serve_forever,daemon=True).start();simulators.append(sim)
    engine=Engine(config,storage);service=Server((config.get('bind','127.0.0.1'),config.get('port',8088)),engine,auth,a.lab)
    engine.start();print(f'CameraBridge: http://{service.server_address[0]}:{service.server_address[1]} (LAB={a.lab})',flush=True)
    try:service.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        engine.close();service.server_close()
        for sim in simulators:sim.shutdown();sim.server_close()

if __name__=='__main__':main()
