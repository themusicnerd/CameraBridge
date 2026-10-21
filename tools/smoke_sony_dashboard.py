"""Browser contract/geometry checks using labelled Sony SDK software fixtures."""
import argparse
import json
import pathlib
import sys
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.sony import SONY
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=pathlib.Path);args=parser.parse_args()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=ROOT/'dashboard/assets/sony.png' if self.path=='/assets/sony.png' else ROOT/'web/sony.html'
            body=path.read_bytes();self.send_response(200);self.send_header('Content-Type','image/png' if path.suffix=='.png' else 'text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    values=dict(iris=280,iris_auto=2,focus_auto=2,wb_mode=2,red_gain=0,blue_gain=0,gain=0,shutter=50,colour_temperature=5600,zoom=100)
    params={key:dict(p.metadata(),value=values[key],confirmation='confirmed',age_seconds=0,low=0,high=100,step=1,allowed=[],writable=key!='zoom') for key,p in SONY.items()}
    params['iris'].update(allowed=[280,400,560],low=280,high=560)
    for key in ['iris_auto','focus_auto','wb_mode']:params[key].update(allowed=[1,2],low=1,high=2)
    params['colour_temperature'].update(low=2000,high=15000,step=100)
    camera=dict(id='sony1',number=3,name='Sony SDK software fixture',manufacturer='Sony',model='PXW-Z200',health='simulated',host='192.0.2.20',locked=False,parameters=params,tally=dict(enabled=True,status='unsupported',error='External tally lamps unavailable on PXW-Z200'))
    requests=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1366,'height':800})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            def route(r):
                data=r.request.post_data_json or {};endpoint=r.request.url.rsplit('/',1)[-1]
                if endpoint=='login':result={'token':'browser-fixture-session','role':'admin'}
                elif endpoint=='state':result={'cameras':[camera]}
                elif endpoint=='command':requests.append(data);result={'generation':1,'status':'queued'}
                else:result={'status':'ok'}
                r.fulfill(content_type='application/json',body=json.dumps(result))
            page.route('**/api/**',route);page.goto(f'http://127.0.0.1:{server.server_port}/sony')
            page.locator('#username').fill('test');page.locator('#password').fill('fixture');page.locator('#login').click()
            expect(page.locator('#status')).to_contain_text('simulated')
            expect(page.get_by_role('img',name='Sony')).to_be_visible()
            expect(page.locator('#controls .card')).to_have_count(6)
            zoom=page.get_by_role('button',name='WIDE',exact=True);zoom.hover();page.mouse.down();page.wait_for_timeout(250);page.mouse.up()
            page.wait_for_timeout(50)
            assert any(c['action']=='move' and c['data'].get('zoom',0)<0 for c in requests)
            assert any(c['action']=='stop' for c in requests)
            page.get_by_role('button',name='Tally: PROGRAM',exact=True).click()
            assert any(c['action']=='tally' and c['data']['program'] for c in requests)
            if args.screenshots:
                args.screenshots.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(args.screenshots/'Sony-dashboard-lens.png'))
            page.locator('#paintpage').click();expect(page.locator('#controls .card')).to_have_count(6)
            expect(page.get_by_role('heading',name='Red gain (Sony native)',exact=True)).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow'
            assert page.evaluate('document.documentElement.scrollHeight<=innerHeight'),'Vertical overflow at 1366x800'
            if args.screenshots:page.screenshot(path=str(args.screenshots/'Sony-dashboard-paint.png'))
            assert not errors,errors
            browser.close();print('PASS: Sony login, lens/paint pages, hold/release, tally request, manufacturer logo and 1366x800 geometry')
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
