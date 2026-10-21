"""Development-only panel host for one explicitly selected TouchDrive.

Keeps CGI emulators and VISCA listeners on loopback. Only fixed panel/assets
and a small REST allowlist are reachable; existing backend authentication still
protects commands. Plain HTTP is intended for the isolated development LAN.
"""
import argparse
import http.client
import ipaddress
import pathlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
POST_PATHS = frozenset(('/api/login', '/api/logout', '/api/state', '/api/command', '/api/snapshot', '/api/lab/ross/bus'))

def panel_bytes(manufacturer, base):
    source = ROOT / 'dashboard' / ('SW-' + manufacturer + '-Camera-Control.grid')
    tree = ET.fromstring(source.read_bytes())
    for parameter in tree.iter('param'):
        if parameter.get('oid') == 'bridge' and 'value' in parameter.attrib:
            parameter.set('value',base)
            for value in parameter.iter('value'):
                value.text = base
    for image in tree.iter('image'):
        image.set('src', base + '/assets/' + manufacturer.lower() + '.png')
    return ET.tostring(tree, encoding='utf-8', xml_declaration=True)

class PanelHost(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, touchdrive):
        self.allowed = {str(ipaddress.ip_address(touchdrive)), address[0]}
        self.base = 'http://%s:%s' % address
        self.slots = threading.BoundedSemaphore(8)
        self.counts = {}; self.count_lock = threading.Lock()
        super().__init__(address, PanelHandler)
    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close(); return
        try: super().process_request(request, client_address)
        except Exception:
            self.slots.release(); raise
    def process_request_thread(self, *args):
        try: super().process_request_thread(*args)
        finally: self.slots.release()

class PanelHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup(); self.connection.settimeout(6)
    def log_message(self, *args): pass
    def reply(self, data, code=200, mime='application/json', attachment=None):
        self.send_response(code)
        self.send_header('Content-Type', mime)
        if attachment:self.send_header('Content-Disposition','attachment; filename="'+attachment+'"')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers(); self.wfile.write(data)
    def trusted(self):
        if self.client_address[0] not in self.server.allowed:
            self.reply(b'{"error":"Host denied"}',403); return False
        return True
    def count(self):
        with self.server.count_lock:
            key=(self.client_address[0],self.command,self.path)
            self.server.counts[key]=self.server.counts.get(key,0)+1
            n=self.server.counts[key]
        if n==1: print('%s %s %s (first request; no content logged)' % key,flush=True)
    def do_GET(self):
        if not self.trusted(): return
        self.count()
        if self.path in ('/Panasonic.grid','/Marshall.grid'):
            self.reply(panel_bytes(self.path[1:-5],self.server.base),mime='application/xml',attachment="CameraBridge-"+self.path[1:]); return
        assets={'/assets/panasonic.png':'panasonic.png','/assets/marshall.png':'marshall.png'}
        if self.path in assets:
            self.reply((ROOT/'dashboard/assets'/assets[self.path]).read_bytes(),mime='image/png'); return
        if self.path=='/health':
            self.reply(b'{"service":"CameraBridge TD panel host","mode":"development"}'); return
        self.reply(b'{"error":"Not found"}',404)
    def do_POST(self):
        if not self.trusted(): return
        if self.path not in POST_PATHS:
            self.reply(b'{"error":"Endpoint not exposed"}',403); return
        if self.headers.get('Origin') and self.headers['Origin']!=self.server.base:
            self.reply(b'{"error":"Origin denied"}',403); return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Transfer-Encoding') or not 0<size<=65536: raise ValueError()
        except ValueError:
            self.reply(b'{"error":"Invalid body size"}',400); return
        body=self.rfile.read(size)
        if len(body)!=size:
            self.reply(b'{"error":"Incomplete body"}',400); return
        self.count()
        upstream=http.client.HTTPConnection('127.0.0.1',8088,timeout=5)
        try:
            headers={'Content-Type':self.headers.get('Content-Type','application/json')}
            if self.headers.get('Authorization'):headers['Authorization']=self.headers['Authorization']
            upstream.request('POST',self.path,body,headers)
            response=upstream.getresponse();data=response.read(1048577)
            if len(data)>1048576:raise ValueError('Upstream response too large')
            self.reply(data,response.status)
        except (OSError,ValueError,http.client.HTTPException):self.reply(b'{"error":"Backend unavailable"}',502)
        finally:upstream.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--bind',required=True);p.add_argument('--touchdrive',required=True);p.add_argument('--port',type=int,default=8089);a=p.parse_args()
    bind=ipaddress.ip_address(a.bind);td=ipaddress.ip_address(a.touchdrive)
    if bind.version!=4 or not bind.is_private or bind.is_unspecified or td.version!=4 or not td.is_private:
        p.error('Explicit private IPv4 development addresses required')
    service=PanelHost((str(bind),a.port),str(td))
    print('Development panel host: %s; TouchDrive %s only' % (service.base,td),flush=True)
    try:service.serve_forever(.2)
    except KeyboardInterrupt:pass
    finally:service.server_close()
if __name__=='__main__': main()
