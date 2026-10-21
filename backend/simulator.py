"""Independent HTTP CGI emulator. Marshall lab model is explicitly NOT a wire spec."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from .protocol import PANASONIC

class PanasonicModel:
    def __init__(self):
        self.values={key:p.low for key,p in PANASONIC.items()}
        self.values.update(red_gain=150,blue_gain=150,wb_mode=2,iris_auto=0,focus_auto=0)
        self.axes={'pan':0,'tilt':0,'zoom':0,'focus':0}
        self.presets={}
        self.history=[]
        self.lock=threading.RLock()
        self.tally_enabled=False;self.tally_on=False

    def command(self,command):
        with self.lock:
            self.history.append(command)
            self.history=self.history[-200:]
            if command in ('#TAE0','#TAE1'):
                self.tally_enabled=command[-1]=='1';return 'tAE'+command[-1]
            if command in ('#DA0','#DA1'):
                self.tally_on=self.tally_enabled and command[-1]=='1';return 'dA'+str(int(self.tally_on))
            if command=='#DA':return 'dA'+str(int(self.tally_on))
            for name,p in PANASONIC.items():
                if command==p.query:
                    v=self.values[name]
                    return p.reply+(f'{v:0{p.width}X}' if p.base==16 else f'{v:0{p.width}d}')
            for name,p in PANASONIC.items():
                if command.startswith(p.write) and len(command)==len(p.write)+p.width:
                    v=int(command[len(p.write):],p.base)
                    if name=='wb_mode' and v in (1,2):v+=1
                    self.values[name]=p.validate(v)
                    return command[1:].replace('AX','ax',1) if command.startswith('#') else command
            if command.startswith('#PTS') and len(command)==8:
                self.axes.update(pan=int(command[4:6])-50,tilt=int(command[6:8])-50)
                return 'pTS'+command[4:]
            if len(command)==4 and command[:2] in ('#Z','#F'):
                self.axes['zoom' if command[1]=='Z' else 'focus']=int(command[2:])-50
                return command[1].lower()+'S'+command[2:]
            if len(command)==4 and command[:2] in ('#M','#R'):
                n=int(command[2:])
                if command[1]=='M':self.presets[n]=dict(self.values)
                elif n in self.presets:self.values.update(self.presets[n])
                return ('s' if command[1]=='M' else 's')+command[2:]
            return 'ER2'

def server(host='127.0.0.1',port=18080,model=None):
    model=model or PanasonicModel()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            u=urlsplit(self.path)
            if u.path=='/lab/state':
                data=json.dumps({'values':model.values,'axes':model.axes,'history':model.history}).encode()
                mime='application/json'
            elif u.path in ('/cgi-bin/aw_ptz','/cgi-bin/aw_cam'):
                try:data=model.command(parse_qs(u.query)['cmd'][0]).encode()
                except (ValueError,KeyError):data=b'ER2'
                mime='text/plain'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def log_message(self,*args):pass
    result=ThreadingHTTPServer((host,port),Handler)
    result.model=model
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18080);a=p.parse_args()
    print(f'Panasonic CGI emulator: http://127.0.0.1:{a.port}',flush=True)
    server(port=a.port).serve_forever()
