"""Exercise the desktop's owned service, hidden window and port restart."""
import json
import os
import pathlib
import socket
import sys
import tempfile
import time
import urllib.request
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication,QSystemTrayIcon
from backend.desktop import DesktopSettings
from backend.server import Auth
from backend.tray import ControlPanel

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    def wait(predicate,seconds=60):
        deadline=time.monotonic()+seconds
        while not predicate():
            app.processEvents()
            if time.monotonic()>deadline:raise AssertionError('Desktop lifecycle timed out: '+panel.message.text()+'\n'+panel.log.toPlainText())
            time.sleep(.02)
        app.processEvents()
    def healthy(port):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=.2) as r:
                return json.load(r)['mode']=='LAB'
        except OSError:return False
    with tempfile.TemporaryDirectory() as directory:
        storage=pathlib.Path(directory);config=json.loads((ROOT/'tests/fixtures/cameras-lab.json').read_text(encoding='utf-8'))
        used=set()
        def port():
            value=free_port()
            while value in used:value=free_port()
            used.add(value);return value
        for camera in config['cameras']:
            if camera['driver']=='panasonic':camera['port']=port()
        source=storage/'camera.json';source.write_text(json.dumps(config),encoding='utf-8')
        first,second=port(),port()
        settings=DesktopSettings(port=first,config_path=str(source),auto_start=False,lab=True)
        settings.prepare(storage);Auth(storage/'credentials.sqlite').add('desktop-test','test','admin')
        panel=ControlPanel(storage,auto_start=False,create_tray=False);panel.show();app.processEvents()
        try:
            panel.start_service();wait(lambda:healthy(first))
            original_pid=panel.service.processId();assert original_pid
            def api(route,data):
                request=urllib.request.Request(f'http://127.0.0.1:{first}'+route,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=2) as response:return json.load(response)
            token=api('/api/login',{'username':'desktop-test','password':'test'})['token']
            config['cameras'][0]['name']='Saved through camera setup'
            result=api('/api/config',{'token':token,'configuration':config,'apply':True})
            assert 'restart requested' in result['status']
            wait(lambda:panel.service.processId()!=original_pid and panel.service.processId()!=0 and healthy(first))
            assert 'Saved through camera setup' in (storage/'desktop-config.json').read_text(encoding='utf-8')
            original_pid=panel.service.processId()
            panel.tray=QSystemTrayIcon(panel)
            with patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=True):panel.close()
            app.processEvents();assert not panel.isVisible()
            assert healthy(first) and panel.service.processId()==original_pid
            panel.show_panel();assert panel.isVisible()
            panel.port.setValue(second);panel.apply()
            wait(lambda:healthy(second))
            assert not healthy(first) and panel.service.processId()!=original_pid
            assert not panel.stop_timer.isActive()
            restored=DesktopSettings.load(storage);assert restored.port==second
            panel.quit_app();wait(lambda:panel.service.state()==QProcess.ProcessState.NotRunning)
            assert not healthy(second) and panel.quitting
            print('PASS: start, close to tray, reopen, saved port restart, old process exit and tray Quit')
        finally:
            if panel.service.state()!=QProcess.ProcessState.NotRunning:
                panel.stop_service();wait(lambda:panel.service.state()==QProcess.ProcessState.NotRunning)
            panel.tray=None;panel.quitting=True;panel.close();panel.deleteLater();app.processEvents()

if __name__=='__main__':main()
