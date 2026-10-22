"""Start a packaged service with isolated ports and temporary user data."""
import argparse
import json
import pathlib
import socket
import subprocess
import tempfile
import time
import urllib.request

def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('executable');a=p.parse_args();exe=str(pathlib.Path(a.executable).resolve())
    subprocess.run([exe,'--version'],check=True)
    with tempfile.TemporaryDirectory() as tmp:
        root=pathlib.Path(tmp);config=json.loads((pathlib.Path(__file__).resolve().parents[1]/'config.example.json').read_text(encoding='utf-8'))
        ports=set()
        for c in config['cameras']:
            if c['driver']=='panasonic':
                port=free_port()
                while port in ports:port=free_port()
                ports.add(port);c['port']=port
        port=free_port()
        while port in ports:port=free_port()
        config['port']=port;path=root/'config.json';path.write_text(json.dumps(config),encoding='utf-8')
        common=[exe,'--config',str(path),'--storage',str(root/'data')]
        subprocess.run(common+['--init-user','smoke'],input='release-test-password\nrelease-test-password\n',text=True,check=True,timeout=20)
        subprocess.run([exe,'panels','--output',str(root/'panels')],check=True)
        assert (root/'panels/CameraBridge-Panasonic.grid').is_file()
        assert (root/'panels/CameraBridge-Sony.grid').is_file()
        assert (root/'panels/CameraBridge.grid').is_file()
        helper=pathlib.Path(exe).parent/'_internal/sony'/('CameraBridge-Sony.exe' if __import__('sys').platform=='win32' else 'CameraBridge-Sony')
        if __import__('sys').platform=='win32':
            assert {'msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'}<={p.name.lower() for p in helper.parent.glob('*.dll')}
        probe=subprocess.run([str(helper)],input='version\nquit\n',text=True,capture_output=True,timeout=15,check=True,cwd=helper.parent)
        assert '"adapter":1' in probe.stdout
        proc=subprocess.Popen(common+['--lab'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        def api(route,data=None):
            req=urllib.request.Request(f'http://127.0.0.1:{port}'+route,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=2) as r:return r.read()
        try:
            deadline=time.monotonic()+60
            while True:
                try:assert json.loads(api('/health'))['mode']=='LAB';break
                except (OSError,AssertionError):
                    if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Packaged service did not start')
                    time.sleep(.2)
            assert b'CameraBridge' in api('/')
            login=json.loads(api('/api/login',{'username':'smoke','password':'release-test-password'}))
            state=json.loads(api('/api/state',{'token':login['token']}));assert len(state['cameras'])==3
            roster=json.loads(api('/api/setup',{'token':login['token'],'operation':'load'}))
            camera=dict(roster['configuration']['cameras'][0],name='Packaged native setup check')
            saved=json.loads(api('/api/setup',{'token':login['token'],'operation':'save','revision':roster['revision'],'previous':camera['id'],'camera':camera}))
            assert saved['configuration']['cameras'][0]['name']==camera['name'] and saved['pending']
            api('/api/command',{'token':login['token'],'camera':'pana1','action':'write','data':{'parameter':'iris','value':1400}})
            deadline=time.monotonic()+15
            while True:
                state=json.loads(api('/api/state',{'token':login['token']}));iris=state['cameras'][0]['parameters']['iris']
                if iris['value']==1400 and iris['confirmation']=='confirmed':break
                if time.monotonic()>deadline:raise RuntimeError('Packaged driver readback did not confirm')
                time.sleep(.2)
            api('/api/service/stop',{'token':login['token']});assert proc.wait(timeout=15)==0
        finally:
            if proc.poll() is None:proc.terminate()
            output=proc.communicate(timeout=10)[0];print(output)
        # SQLite can be removed on Windows only when all connections are closed.
        print('PASS: version, panel export, account, assets, HTTP, login, CGI readback and clean shutdown')

if __name__=='__main__':main()
