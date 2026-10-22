"""Browser acceptance for inline setup, persistent sign-in, autosave and TSL."""
import argparse,json,pathlib,socket,subprocess,sys,tempfile,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Auth
from playwright.sync_api import sync_playwright,expect

def free_port(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET,kind) as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=pathlib.Path);parser.add_argument('--executable');args=parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        data=pathlib.Path(directory);port=free_port();camera_port=free_port();tsl_port=free_port(socket.SOCK_DGRAM)
        config={'bind':'127.0.0.1','port':port,'poll_seconds':1,'trusted_hosts':['127.0.0.1/32'],'cameras':[{'id':'p1','number':1,'name':'Camera 1','manufacturer':'Panasonic','model':'AW-HE130','driver':'panasonic','host':'127.0.0.1','port':camera_port,'simulator':True,'enabled':True,'carbonite_input':1,'tally_address':1,'tally_enabled':True,'pivotcam':False,'allow_store':False}], 'tally':{'enabled':True,'bind':'127.0.0.1','port':tsl_port,'source':'127.0.0.1','program_tally':2}}
        path=data/'cameras.json';path.write_text(json.dumps(config));Auth(data/'credentials.sqlite').add('test','test','admin')
        command=([args.executable] if args.executable else [sys.executable,str(ROOT/'camerabridge.py')])+['--serve','--config',str(path),'--storage',str(data),'--desktop-control']
        def start():return subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
        process=start();url=f'http://127.0.0.1:{port}'
        def api(route,payload=None,token=''):
            req=urllib.request.Request(url+'/'+route,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
            with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
        def ready():
            for _ in range(100):
                try:api('health');return
                except OSError:time.sleep(.1)
            raise AssertionError('Service did not start')
        def send_tsl(control):
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.sendto(bytes([0x81,control])+b'CAMERA 1        ',('127.0.0.1',tsl_port))
        try:
            ready()
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1366,'height':872});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(url);page.locator('#user').fill('test');page.locator('#password').fill('test');page.locator('#password').press('Enter');expect(page.locator('#savestatus')).to_have_text('All Changes Saved')
                assert page.get_by_text('Advanced JSON',exact=True).count()==0
                assert 'verify camera feedback before control' not in page.locator('body').inner_text().lower()
                assert page.locator('.app-logo').evaluate('(img)=>img.complete&&img.naturalWidth>0')
                row=page.locator('#camera-p1');row.locator('summary').click();expect(row.locator('[data-field=manufacturer]')).to_have_value('Panasonic');assert row.locator('[data-field=model] option').filter(has_text='AW-HE2').count()==1
                assert len(set(round(row.locator('[data-field="'+k+'"]').bounding_box()['y']) for k in ['number','name','manufacturer','model']))==1
                row.locator('[data-field=name]').fill('Studio Camera');row.locator('[data-field=name]').press('Tab');expect(page.locator('#savestatus')).to_have_text('All Changes Saved',timeout=20000)
                token=page.evaluate('localStorage.getItem("camerabridge-device-session")')
                assert api('api/config',token=token)['cameras'][0]['name']=='Studio Camera'
                expect(row.locator('[data-field=name]')).to_have_value('Studio Camera');assert row.get_attribute('open') is not None
                expect(row.locator('[data-field=host]').locator('..').locator('a')).to_have_attribute('href',f'http://127.0.0.1:{camera_port}/')
                send_tsl(2);expect(row).to_have_attribute('data-tally','program',timeout=10000);expect(row.locator('.tally-feedback')).to_contain_text('Camera Tally Lamp: On',timeout=10000);expect(page.locator('#tslbadge')).to_have_text('TSL Receiving')
                send_tsl(1);expect(row).to_have_attribute('data-tally','preview',timeout=10000);expect(row.locator('.tally-feedback')).to_contain_text('Camera Tally Lamp: Off',timeout=10000)
                # Disabling lamp control must not hide received Preview/Program feedback.
                row.locator('[data-field=tally_enabled]').uncheck();expect(page.locator('#savestatus')).to_have_text('All Changes Saved',timeout=20000);send_tsl(2);expect(row).to_have_attribute('data-tally','program',timeout=10000)
                if args.screenshots:
                    args.screenshots.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(args.screenshots/'CameraBridge-inline-setup.png'),full_page=True)
                page.reload();expect(page.locator('#login')).to_be_hidden();expect(page.locator('#savestatus')).to_have_text('All Changes Saved')
                # Restart the actual service while preserving browser storage and accounts.
                process.communicate('quit\n',timeout=20);assert process.returncode==0;process=start();ready();page.reload();expect(page.locator('#login')).to_be_hidden();expect(page.locator('#savestatus')).to_have_text('All Changes Saved')
                page.locator('#addcamera').click();new=page.locator('#roster details').last;new.locator('[data-field=enabled]').uncheck();new.locator('[data-field=manufacturer]').select_option('Sony');expect(new.locator('[data-field=model]')).to_have_value('PXW-Z200');new.locator('[data-field=manufacturer]').select_option('Panasonic');new.locator('[data-field=model]').select_option('AW-HE2');new.locator('[data-field=host]').fill('192.0.2.42');new.locator('[data-field=host]').press('Tab');expect(page.locator('#savestatus')).to_have_text('All Changes Saved',timeout=20000)
                assert api('api/config',token=token)['cameras'][1]['model']=='AW-HE2'
                page.locator('#accesssettings summary').click();page.locator('#authentication').uncheck();expect(page.locator('#sessionstatus')).to_have_text('Authentication Off',timeout=20000);assert api('api/config')['authentication_enabled'] is False
                # A new browser gets open access only while the setting is disabled.
                guest=browser.new_context().new_page();guest.goto(url);expect(guest.locator('#login')).to_be_hidden();expect(guest.locator('#savestatus')).to_have_text('All Changes Saved')
                page.locator('#authentication').check();expect(page.locator('#sessionstatus')).to_have_text('Signed In: Administrator',timeout=20000)
                guest.reload();expect(guest.locator('#login')).to_be_visible(timeout=10000);guest.close()
                # A busy receive port must roll back the live setup and retain sign-in.
                loaded=api('api/setup',{'operation':'load'},token)
                blocked=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);blocked.bind(('127.0.0.1',0))
                candidate=json.loads(json.dumps(loaded['configuration']));candidate['tally']['port']=blocked.getsockname()[1]
                try:
                    try:api('api/setup',{'operation':'autosave','revision':loaded['revision'],'configuration':candidate},token)
                    except urllib.error.HTTPError as error:
                        assert error.code==400
                        assert 'Previous setup restored' in json.load(error)['error']
                    else:raise AssertionError('A busy tally port must fail')
                finally:blocked.close()
                assert api('api/config',token=token)['tally']['port']==tsl_port
                assert api('api/session',token=token)['role']=='admin'
                page.locator('#signout').click();page.reload();expect(page.locator('#login')).to_be_visible()
                assert not errors,errors
                page.goto(url+'/help');expect(page.locator('h1')).to_have_text('CameraBridge Help');assert page.get_by_text('PIVOTCam_1.1',exact=True).count()>0
                browser.close()
            print('PASS: inline four-column setup, switches, manufacturer/model choices, autosave without session loss, persistent browser sign-in after restart, TSL Preview/Program and lamp readback, disabled-lamp feedback, auth toggle, sign-out revocation, IP links and Help')
        finally:
            if process.poll() is None:process.communicate('quit\n',timeout=20)

if __name__=='__main__':main()
