"""Loopback-only video calibration workstation, independent of camera control."""
import argparse
import copy
import ipaddress
import json
import pathlib
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from .calibration_video import VideoSession,capture_devices,ffmpeg_path
from .calibration import validate,validate_optical

ROOT=pathlib.Path(__file__).resolve().parents[1]


class Bridge:
    def __init__(self):self.url=None;self.token=None;self.cameras=[]

    def api(self,path,data=None):
        request=urllib.request.Request(self.url+'/api/'+path,data=None if data is None else json.dumps(data).encode(),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+(self.token or '')})
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=12) as response:
                body=response.read(2*1024*1024+1)
                if len(body)>2*1024*1024:raise ValueError('Bridge response is too large')
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            try:message=json.loads(exc.read(2048)).get('error','Bridge request failed')
            except Exception:message='Bridge request failed'
            raise ValueError(message) from None
        except (OSError,ValueError) as exc:
            if isinstance(exc,ValueError) and str(exc)=='Bridge response is too large':raise
            raise ValueError('Cannot communicate with CameraBridge. Check its address and network access.') from None

    def connect(self,data):
        url=urllib.parse.urlsplit(str(data.get('url','')).strip())
        if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
            raise ValueError('Enter the CameraBridge base HTTP address without credentials or a path')
        self.url=urllib.parse.urlunsplit((url.scheme,url.netloc,'','',''));self.token=None
        login=self.api('login',dict(username=data.get('username',''),password=data.get('password','')))
        if login['role']!='admin':raise ValueError('Use a CameraBridge administrator account for calibration')
        self.token=login['token']
        state=self.api('state')
        self.cameras=[{k:c.get(k) for k in ('id','number','name','model','host')} for c in state['cameras']]
        return self.cameras

    def encoders(self,camera):
        if not self.token:raise ValueError('Connect to CameraBridge first')
        return self.api('calibration/capture',dict(camera=camera))

    def save(self,camera,solution,tag):
        if not self.token:raise ValueError('Connect to CameraBridge first')
        validate_optical(solution)
        loaded=self.api('setup',dict(operation='load'));active=self.api('config')
        if loaded['configuration']!=active:raise ValueError('CameraBridge has a pending setup. Resolve that setup before saving calibration.')
        configuration=copy.deepcopy(active)
        selected=next((c for c in configuration['cameras'] if c['id']==camera),None)
        if selected is None:raise ValueError('Camera no longer exists')
        if (selected['model'],selected['host'],selected.get('port',80))!=(tag['camera_model'],tag['camera_host'],tag['camera_port']):raise ValueError('Camera connection changed after capture. Start a new calibration batch.')
        p=selected.get('tracking_calibration') or dict(version=1,name=(selected['name']+' Lens')[:80],model=selected['model'],
            video_width=solution['width'],video_height=solution['height'],lens_points=[])
        if p['model']!=selected['model'] or ((p.get('lens_points') or p.get('optical_solutions')) and (p['video_width'],p['video_height'])!=(solution['width'],solution['height'])):
            raise ValueError('Profile model or video dimensions differ. Export the old profile and start an empty matching profile first.')
        p['video_width']=solution['width'];p['video_height']=solution['height']
        p['optical_solutions']=[s for s in p.get('optical_solutions',[]) if s['zoom']!=solution['zoom']]+[solution]
        validate(p);selected['tracking_calibration']=p
        return self.api('setup',dict(operation='autosave',revision=loaded['revision'],configuration=configuration))


class Workstation(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,port=0):
        self.video=VideoSession();self.bridge=Bridge();self.token=secrets.token_urlsafe(32);self.operations=threading.Lock();self.tag=None
        super().__init__(('127.0.0.1',port),Handler)
    def close(self):
        self.video.stop();self.shutdown();self.server_close();self.bridge.token=None


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,value,status=200,mime='application/json'):
        data=value if isinstance(value,bytes) else json.dumps(value,allow_nan=False).encode()
        self.send_response(status)
        for key,val in [('Content-Type',mime),('Content-Length',str(len(data))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY')]:self.send_header(key,val)
        self.end_headers();self.wfile.write(data)
    def host_ok(self):
        port=self.server.server_address[1]
        return ipaddress.ip_address(self.client_address[0]).is_loopback and self.headers.get('Host') in ('127.0.0.1:'+str(port),'localhost:'+str(port))
    def authorized(self):return self.host_ok() and secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+self.server.token)
    def do_GET(self):
        if not self.host_ok():self.send({'error':'Local workstation access only'},403);return
        if self.path=='/':
            html=(ROOT/'web/calibration-workstation.html').read_text(encoding='utf-8').replace('__LOCAL_TOKEN__',self.server.token)
            self.send(html.encode(),mime='text/html; charset=utf-8');return
        if self.path=='/workstation.js':self.send((ROOT/'web/workstation.js').read_bytes(),mime='application/javascript');return
        if self.path=='/setup.css':self.send((ROOT/'web/setup.css').read_bytes(),mime='text/css');return
        if self.path=='/assets/camerabridge.svg':self.send((ROOT/'web/assets/camerabridge.svg').read_bytes(),mime='image/svg+xml');return
        if not self.authorized():self.send({'error':'Workstation access required'},403);return
        try:
            if self.path=='/api/state':self.send(dict(self.server.video.snapshot(),bridge_connected=bool(self.server.bridge.token),cameras=self.server.bridge.cameras,tag=self.server.tag))
            elif self.path=='/api/preview':self.send(self.server.video.preview(),mime='image/jpeg')
            else:self.send({'error':'Not found'},404)
        except ValueError as exc:self.send({'error':str(exc)},400)
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.authorized() or (origin and origin!='http://'+self.headers.get('Host','')):
            self.send({'error':'Workstation access required'},403);return
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=65536:raise ValueError('Invalid workstation request size')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Workstation request must be a JSON object')
            with self.server.operations:result=self.operation(data)
            self.send(result)
        except (ValueError,KeyError,TypeError,RuntimeError,OSError) as exc:
            message=str(exc) if isinstance(exc,(ValueError,RuntimeError)) else 'Workstation operation failed'
            self.send({'error':message},400)
    def operation(self,data):
        s=self.server;v=s.video
        if self.path=='/api/discover':
            if data.get('type')=='ndi':
                from .ndi_video import runtime
                return dict(sources=runtime().sources())
            if data.get('type')=='usb':return dict(sources=capture_devices())
            return dict(sources=[])
        if self.path=='/api/start':v.start(data);s.tag=None;return dict(status='Connecting')
        if self.path=='/api/stop':v.stop();return dict(status='Stopped')
        if self.path=='/api/reset':v.reset();s.tag=None;return dict(status='New lens-setting batch')
        if self.path=='/api/bridge/connect':
            if v.samples and str(data.get('url','')).rstrip('/')!=s.bridge.url:raise ValueError('Start a new batch before connecting to another bridge')
            return dict(cameras=s.bridge.connect(data))
        if self.path=='/api/bridge/encoders':return s.bridge.encoders(data['camera'])
        if self.path=='/api/capture':
            tag=data.get('tag')
            if data.get('camera'):
                raw=s.bridge.encoders(data['camera']);tag=dict(zoom=raw['zoom'],focus=raw['focus'],camera_model=raw['model'],camera=data['camera'],camera_host=raw['host'],camera_port=raw['port'])
            if tag is not None:
                for key in ('zoom','focus'):
                    if type(tag.get(key)) is not int or not 0<=tag[key]<=0xffffff:raise ValueError('Set the lens encoder tags, or leave both blank for an untagged solve')
                if not isinstance(tag.get('camera_model'),str) or not 1<=len(tag['camera_model'])<=80:raise ValueError('Set the camera model for the lens tags')
            if v.samples and tag!=s.tag:raise ValueError('Camera or lens setting changed. Start a new batch before capture.')
            result=v.capture(data)
            s.tag=tag;return result
        if self.path=='/api/solve':return v.solve()
        if self.path=='/api/save':
            if not v.result or not s.tag or not s.tag.get('camera'):raise ValueError('Solve a batch linked to a CameraBridge camera before saving')
            solution=dict(v.result,zoom=s.tag['zoom'],focus=s.tag['focus'])
            s.bridge.save(s.tag['camera'],solution,s.tag);return dict(status='Optical calibration saved to CameraBridge')
        raise ValueError('Unknown workstation operation')


def start(port=0):
    server=Workstation(port);threading.Thread(target=server.serve_forever,daemon=True,name='calibration-workstation').start()
    return server


def main():
    parser=argparse.ArgumentParser(description='Local NDI, RTSP, and USB capture calibration workstation')
    parser.add_argument('--port',type=int,default=8090);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--check-dependencies',action='store_true');args=parser.parse_args()
    if args.check_dependencies:
        from .calibration_video import cv_modules
        from .ndi_video import runtime_path
        cv,np=cv_modules()
        try:ndi=runtime_path()
        except RuntimeError:ndi=None
        try:ffmpeg=ffmpeg_path()
        except RuntimeError:ffmpeg=None
        print(json.dumps(dict(opencv=cv.__version__,numpy=np.__version__,ndi_runtime=ndi,ffmpeg=ffmpeg)));return
    server=Workstation(args.port);url='http://127.0.0.1:'+str(server.server_address[1])+'/'
    print('CameraBridge Calibration: '+url,flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.video.stop();server.server_close()
