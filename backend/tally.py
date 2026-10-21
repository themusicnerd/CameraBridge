"""Source restricted TSL UMD 3.1 UDP tally input. Labels never execute commands."""
import socketserver
import time

def decode(data):
    if not data or len(data)%18 or len(data)>2304:raise ValueError('Expected complete 18-byte TSL 3.1 messages')
    result=[]
    for n in range(0,len(data),18):
        frame=data[n:n+18]
        if not 0x80<=frame[0]<=0xfe or frame[1]&0xc0 or any(not 0x20<=v<=0x7e for v in frame[2:]):raise ValueError('Invalid TSL 3.1 message')
        result.append((frame[0]-0x80,bool(frame[1]&1),bool(frame[1]&2)))
    return result

class TallyServer(socketserver.UDPServer):
    def __init__(self,address,engine,source,address_offset=0):
        self.engine=engine;self.source=source;self.address_offset=address_offset
        super().__init__(address,TallyHandler)
    def verify_request(self,request,address):return address[0]==self.source

class TallyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:messages=decode(self.request[0])
        except ValueError:return
        for address,program,preview in messages:
            for cid,c in self.server.engine.cameras.items():
                target=c['config'].get('tally_address',c['config'].get('carbonite_input',c['config'].get('number',1))-1+self.server.address_offset)
                if address==target:self.server.engine.set_tally(cid,program,preview,'TSL 3.1')
