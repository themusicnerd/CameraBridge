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
    def __init__(self,address,engine,source,address_offset=0,program_tally=2):
        if program_tally not in (1,2):raise ValueError('Program tally must be 1 or 2')
        self.engine=engine;self.source=source;self.address_offset=address_offset;self.program_tally=program_tally
        super().__init__(address,TallyHandler)
        if isinstance(getattr(engine,'tsl',None),dict):
            with engine.lock:engine.tsl.update(enabled=True,listening=True,bind=self.server_address[0],port=self.server_address[1],source=source)
    def verify_request(self,request,address):
        accepted=address[0]==self.source
        if not accepted and isinstance(getattr(self.engine,'tsl',None),dict):
            with self.engine.lock:self.engine.tsl['rejected_sources']+=1
        return accepted
    def server_close(self):
        if isinstance(getattr(self.engine,'tsl',None),dict):
            with self.engine.lock:self.engine.tsl['listening']=False
        super().server_close()

class TallyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:messages=decode(self.request[0])
        except ValueError:
            if isinstance(getattr(self.server.engine,'tsl',None),dict):
                with self.server.engine.lock:self.server.engine.tsl['invalid_packets']+=1
            return
        if isinstance(getattr(self.server.engine,'tsl',None),dict):
            with self.server.engine.lock:
                status=self.server.engine.tsl
                status.update(last_packet=time.time(),packets=status['packets']+1,messages=status['messages']+len(messages))
        for address,tally1,tally2 in messages:
            program,preview=(tally2,tally1) if self.server.program_tally==2 else (tally1,tally2)
            for cid,c in self.server.engine.cameras.items():
                target=c['config'].get('tally_address',c['config'].get('carbonite_input',c['config'].get('number',1))+self.server.address_offset)
                if address==target:self.server.engine.set_tally(cid,program,preview,'TSL 3.1')
