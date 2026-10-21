"""Passive application-level receive capture; no camera commands or proxy forwarding.

Point an authorized development controller at this listener. This does NOT capture
physical RS485 or silently intercept a running production connection.
"""
import argparse
import json
import socket
import time

def main():
    p=argparse.ArgumentParser();p.add_argument('--bind',default='127.0.0.1');p.add_argument('--port',type=int,default=19000);p.add_argument('--output',required=True);a=p.parse_args()
    with socket.socket() as listener,open(a.output,'a',encoding='utf-8') as log:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind((a.bind,a.port));listener.listen(1)
        print('Receive-only capture listening; no VISCA responses are fabricated.',flush=True)
        while True:
            client,peer=listener.accept()
            with client:
                client.settimeout(5)
                while True:
                    try:data=client.recv(4096)
                    except socket.timeout:break
                    if not data:break
                    log.write(json.dumps({'time':time.time(),'peer':peer[0],'hex':data.hex(' ')})+'\n');log.flush()

if __name__=='__main__':main()
