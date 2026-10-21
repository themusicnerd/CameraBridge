"""One-frame, simulator-only LAN test relay; capture real Carbonite VISCA traffic.

The backend and its CGI/VISCA simulators stay bound to loopback. This separate
listener permits exactly one configured frame IP and one active TCP connection.
No real Preset-bus following or physical camera compatibility is claimed.
"""
import argparse
import ipaddress
import json
import pathlib
import select
import socket
import socketserver
import threading
import time
import urllib.request


def verify_lab(port):
    def get(path):
        with urllib.request.urlopen('http://127.0.0.1:8088'+path,timeout=2) as r:return json.load(r)
    if get('/health').get('mode')!='LAB':raise ValueError('Development relay requires LAB backend')
    cid={19011:'pana1',19012:'pana2'}[port]
    camera=next(c for c in get('/api/state')['cameras'] if c['id']==cid)
    if not camera.get('simulator') or camera['manufacturer']!='Panasonic' or not ipaddress.ip_address(camera['host']).is_loopback:
        raise ValueError('Only loopback Panasonic emulators are permitted')

class Capture:
    def __init__(self,path,limit=2_000_000):
        self.file=open(path,'a',encoding='utf-8');self.lock=threading.Lock();self.size=self.file.tell();self.limit=limit
    def record(self,peer,direction,data=b''):
        line=json.dumps(dict(time=time.time(),peer=peer,direction=direction,hex=data.hex(' ')))+'\n'
        with self.lock:
            if self.size+len(line)>self.limit:raise OSError('Capture limit reached; end this test and archive capture')
            self.file.write(line);self.file.flush();self.size+=len(line)
    def close(self):self.file.close()

class Relay(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True
    def __init__(self,address,frame,upstream_port,capture,validator=verify_lab):
        self.frame,self.upstream_port,self.capture,self.validator=frame,upstream_port,capture,validator
        self.slot=threading.BoundedSemaphore(1);self.closing=threading.Event();self.clients=set();self.lock=threading.Lock();self.condition=threading.Condition(self.lock)
        super().__init__(address,Handler)
    def verify_request(self,request,client_address):return client_address[0]==self.frame and not self.closing.is_set()
    def server_close(self):
        self.closing.set()
        with self.lock:
            for s in self.clients:
                try:s.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            self.condition.wait_for(lambda:not self.clients,timeout=3)
        super().server_close()

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        if not self.server.slot.acquire(False):return
        peer=self.client_address[0]
        try:
            self.server.validator(self.server.upstream_port)
            with socket.create_connection(('127.0.0.1',self.server.upstream_port),timeout=2) as upstream:
                self.request.settimeout(1);upstream.settimeout(1)
                with self.server.lock:self.server.clients.update((self.request,upstream))
                try:
                    self.server.capture.record(peer,'connect')
                    print('Carbonite connected: '+peer,flush=True)
                    sockets=(self.request,upstream);seen_first=False;forward=True
                    while not self.server.closing.is_set():
                        ready,_,_=select.select(sockets,[],[],.2)
                        for source in ready:
                            data=source.recv(4096)
                            if not data:return
                            incoming=source is self.request
                            self.server.capture.record(peer,'frame-to-lab' if incoming else 'lab-to-frame',data)
                            if incoming and not seen_first:
                                seen_first=True;forward=data[0] in (0x81,0x88)
                                if not forward:
                                    self.server.capture.record(peer,'unsupported-framing-disconnect',data[:16])
                                    print('Non-VISCA prefix from frame; captured and disconnected without forwarding or invented replies.',flush=True)
                                    return
                            if incoming and not forward:continue
                            target=upstream if incoming else self.request
                            target.sendall(data)
                finally:
                    with self.server.condition:
                        self.server.clients.difference_update((self.request,upstream));self.server.condition.notify_all()
                    self.server.capture.record(peer,'disconnect')
                    print('Carbonite disconnected; loopback gateway will stop its selected emulator.',flush=True)
        except (OSError,ValueError,KeyError,StopIteration) as e:
            print('Development relay ended connection: '+str(e),flush=True)
        finally:self.server.slot.release()

def main():
    p=argparse.ArgumentParser();p.add_argument('--bind',required=True);p.add_argument('--frame',required=True);p.add_argument('--port',type=int,choices=(19011,19012),default=19011);p.add_argument('--output',required=True);a=p.parse_args()
    for value in (a.bind,a.frame):
        ip=ipaddress.ip_address(value)
        if ip.version!=4 or not ip.is_private or ip.is_unspecified or ip.is_loopback:p.error('Use explicit private LAN IPv4 addresses')
    verify_lab(a.port)
    path=pathlib.Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    capture=Capture(path);service=Relay((a.bind,a.port),a.frame,a.port,capture)
    print('SIMULATOR TEST relay: %s:%s; frame %s only; capture %s' % (a.bind,a.port,a.frame,path),flush=True)
    try:service.serve_forever(.2)
    except KeyboardInterrupt:pass
    finally:service.shutdown();service.server_close();capture.close()
if __name__=='__main__':main()
