"""Browser acceptance test for camera setup. Requires the optional Playwright package."""
import argparse
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.server import Auth
from playwright.sync_api import sync_playwright,expect

def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=pathlib.Path);args=parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        storage=pathlib.Path(directory);config=json.loads((ROOT/'config.example.json').read_text(encoding='utf-8'))
        ports=set()
        def port():
            p=free_port()
            while p in ports:p=free_port()
            ports.add(p);return p
        config['port']=port()
        for c in config['cameras']:
            if c['driver']=='panasonic':c['port']=port()
        path=storage/'config.json';path.write_text(json.dumps(config),encoding='utf-8')
        Auth(storage/'credentials.sqlite').add('test','browser-test','admin')
        Auth(storage/'credentials.sqlite').add('operator','browser-test','operator')
        process=subprocess.Popen([sys.executable,str(ROOT/'camerabridge.py'),'--serve','--config',str(path),'--storage',str(storage),'--lab','--desktop-control'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            url=f'http://127.0.0.1:{config["port"]}'
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url+'/health',timeout=.2):break
                except OSError:time.sleep(.1)
            else:raise AssertionError('Test service did not start')
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1366,'height':800})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(url)
                # Regression: the user opened setup before signing in. Login must
                # load it automatically, without another navigation/reload click.
                page.get_by_role('button',name='Camera setup',exact=True).click()
                expect(page.locator('#addcamera')).to_be_disabled()
                expect(page.locator('#draftstatus')).to_contain_text('Sign in as an administrator')
                page.locator('#user').fill('test');page.locator('#password').fill('browser-test');page.locator('#password').press('Enter')
                expect(page.locator('#status')).to_contain_text('Authenticated')
                expect(page.locator('#draftstatus')).to_contain_text('Setup ready')
                expect(page.locator('#addcamera')).to_be_enabled()
                expect(page.locator('#roster details[open]')).to_have_count(0)
                for logo in page.locator('#roster summary img').all():
                    expect(logo).to_be_visible()
                    assert logo.evaluate('(img)=>img.complete && img.naturalWidth>0')
                expect(page.locator('#applycameras')).to_be_disabled()
                expect(page.locator('#sessionstatus')).to_have_text('Signed in · admin')
                if args.screenshots:
                    args.screenshots.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(args.screenshots/'CameraBridge-setup-ready.png'))
                page.locator('#addcamera').click();expect(page.locator('#cameraform')).to_be_visible()
                expect(page.locator('#camhost')).to_have_value('')
                assert page.locator('#camname').bounding_box()['y']>=0
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                if args.screenshots:page.screenshot(path=str(args.screenshots/'CameraBridge-add-camera.png'))
                # Sign-out must clear the previous administrator's draft/form.
                page.locator('#signout').click();expect(page.locator('#cameraform')).to_be_hidden()
                expect(page.locator('#addcamera')).to_be_disabled()
                page.locator('#user').fill('operator');page.locator('#password').fill('browser-test');page.locator('#signin').click()
                expect(page.locator('#sessionstatus')).to_have_text('Signed in · operator')
                expect(page.locator('#addcamera')).to_be_disabled()
                expect(page.locator('#draftstatus')).to_contain_text('administrator account')
                page.locator('#signout').click()
                # A load error must offer a usable retry, not claim setup is ready.
                page.route('**/api/setup',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Setup test failure"}'))
                page.locator('#user').fill('test');page.locator('#password').fill('browser-test');page.locator('#signin').click()
                expect(page.locator('#draftstatus')).to_contain_text('could not load')
                expect(page.locator('#addcamera')).to_be_disabled()
                expect(page.locator('#loadcameras')).to_be_enabled()
                page.unroute('**/api/setup');page.locator('#loadcameras').click()
                expect(page.locator('#draftstatus')).to_contain_text('Setup ready')
                page.route('**/api/setup',lambda r:r.fulfill(status=403,content_type='application/json',body='{"error":"Authentication required"}'))
                page.locator('#loadcameras').click()
                expect(page.locator('#sessionstatus')).to_have_text('Signed out')
                expect(page.locator('#draftstatus')).to_contain_text('Sign in again')
                expect(page.locator('#addcamera')).to_be_disabled()
                page.unroute('**/api/setup')
                page.locator('#password').fill('browser-test');page.locator('#signin').click()
                expect(page.locator('#draftstatus')).to_contain_text('Setup ready')
                page.locator('#addcamera').click();page.locator('#camnumber').fill('7');page.locator('#camname').fill('Sony Z200');page.locator('#camprofile').select_option('sony-sdk');page.locator('#camhost').fill('192.0.2.20')
                expect(page.locator('#camenabled')).to_be_enabled();expect(page.locator('#camenabled')).to_be_checked()
                expect(page.locator('#camtally')).to_be_checked()
                page.locator('#camtally').uncheck()
                page.get_by_role('button',name='Save camera to setup',exact=True).click();expect(page.locator('#roster')).to_contain_text('Camera 7')
                page.locator('#addcamera').click();page.locator('#camnumber').fill('7');page.locator('#camname').fill('Real Panasonic');page.locator('#camhost').fill('192.0.2.30');page.get_by_role('button',name='Save camera to setup',exact=True).click()
                expect(page.locator('#status')).to_contain_text('already assigned')
                page.locator('#camnumber').fill('8');page.locator('#camprofile').select_option('panasonic:AW-HE40');page.locator('#campivot').check();page.get_by_role('button',name='Save camera to setup',exact=True).click()
                page.locator('#roster article').filter(has_text='Camera 1 ·').locator('summary').click()
                page.locator('#roster article').filter(has_text='Camera 1 ·').get_by_role('button',name='Edit',exact=True).click();page.locator('#camnumber').fill('4');page.get_by_role('button',name='Save camera to setup',exact=True).click()
                page.on('dialog',lambda dialog:dialog.accept())
                page.locator('#roster article').filter(has_text='Camera 2 ·').locator('summary').click()
                page.locator('#roster article').filter(has_text='Camera 2 ·').get_by_role('button',name='Remove',exact=True).click()
                page.locator('#networksetup summary').click()
                page.locator('#pivotenabled').check();page.locator('#pivotbind').fill('127.0.0.1');page.locator('#pivotcontroller').fill('127.0.0.1')
                with page.expect_download() as result:page.locator('#mappingexport').click()
                download=result.value;mapping=json.loads(pathlib.Path(download.path()).read_text(encoding='utf-8'))
                assert next(c for c in mapping if c['number']==8)['tcp_port']==19018
                page.locator('#applycameras').click();expect(page.locator('#draftstatus')).to_contain_text('restart requested')
                saved=json.loads((storage/'config.pending.json').read_text(encoding='utf-8'))
                assert {c['number'] for c in saved['cameras']}=={3,4,7,8}
                assert next(c for c in saved['cameras'] if c['number']==4)['id']=='pana1'
                assert saved['pivotcam']['base_port']==19010
                assert next(c for c in saved['cameras'] if c['number']==8)['model']=='AW-HE40'
                assert next(c for c in saved['cameras'] if c['number']==8)['driver']=='panasonic'
                assert next(c for c in saved['cameras'] if c['number']==7)['enabled']
                assert not next(c for c in saved['cameras'] if c['number']==7)['tally_enabled']
                assert next(c for c in saved['cameras'] if c['number']==4)['tally_enabled']
                assert not errors,errors
                browser.close();print('PASS: setup-before-login, Enter sign-in, automatic roster load, form access, sign-out isolation, operator restrictions, load retry, add/edit/remove cameras, duplicate number rejection, Sony profile, default tally, map export and save/restart request')
        finally:
            if process.poll() is None:process.communicate('quit\n',timeout=20)
            assert process.returncode==0

if __name__=='__main__':main()
