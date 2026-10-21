"""Authenticated test selection plus raw TCP controller traffic to lab emulators.

Run the service with --lab --visca-lab. Add --visca-allow-store to the service and
--store here only when testing intentional simulator preset overwrites.
"""
import argparse
import getpass
import json
import socket
import urllib.request

def main():
    p=argparse.ArgumentParser();p.add_argument('--username',default='admin');p.add_argument('--store',action='store_true');a=p.parse_args()
    token=''
    def api(path,data):
        if token:data=dict(data,token=token)
        request=urllib.request.Request('http://127.0.0.1:8088/api/'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
    token=api('login',{'username':a.username,'password':getpass.getpass('CameraBridge password: ')})['token']
    def send(client,hexstr,expected=bytes.fromhex('90 41 FF 90 51 FF')):
        client.sendall(bytes.fromhex(hexstr));reply=b''
        while len(reply)<len(expected):
            chunk=client.recv(len(expected)-len(reply))
            if not chunk:raise RuntimeError('VISCA connection closed')
            reply+=chunk
        if reply!=expected:raise RuntimeError('Unexpected VISCA reply: '+reply.hex(' '))
    api('lab/ross/bus',{'bus':'preset','camera':'pana1'})
    with socket.create_connection(('127.0.0.1',19011),timeout=5) as first:
        send(first,'81 01 06 01 01 01 03 03 FF');send(first,'81 01 04 07 00 FF')
        send(first,'81 01 06 01 08 06 02 01 FF');send(first,'81 01 04 07 22 FF')
        state=api('lab/ross/bus',{'bus':'program','camera':'pana2'})
        assert state['selected']=='pana1','Program incorrectly retargeted positioner'
        api('lab/ross/bus',{'bus':'preset','camera':'pana2'})
        with urllib.request.urlopen('http://127.0.0.1:18080/lab/state') as response:
            assert not any(json.load(response)['axes'].values()),'Previous camera did not stop'
        send(first,'81 01 04 07 27 FF',bytes.fromhex('90 60 41 FF'))
        with socket.create_connection(('127.0.0.1',19012),timeout=5) as second:
            send(second,'81 01 06 01 01 01 03 03 FF');send(second,'81 01 04 07 00 FF')
            send(second,'81 01 06 01 08 06 01 02 FF');send(second,'81 01 04 07 32 FF')
            send(second,'81 01 06 01 01 01 03 03 FF');send(second,'81 01 04 07 00 FF')
            if a.store:send(second,'81 01 04 3F 01 13 FF')
            send(second,'81 01 04 3F 02 13 FF')
    print('PASS: authenticated lab selection; raw VISCA PT/zoom; Program ignored; handover stop; stale target rejected; preset20 '+('store/recall' if a.store else 'recall')+'.')
    print('This is simulator evidence. Carbonite/TouchDrive hardware has not been validated.')

if __name__=='__main__':main()
