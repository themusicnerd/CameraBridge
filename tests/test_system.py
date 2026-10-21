import json
import pathlib
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from backend.protocol import PANASONIC,movement,preset
from backend.drivers import Panasonic,Marshall,SerialBus
from backend.simulator import server as simulator
from backend.core import Engine
from backend.server import Auth,Server,validate_config,ROOT,provision_user

def wait_for(predicate,timeout=5):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.03)
    raise AssertionError('Timed out waiting for expected state')

class ProtocolTests(unittest.TestCase):
    def test_interactive_provisioning_retries_without_exposing_password(self):
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        with tempfile.TemporaryDirectory() as directory:
            auth=Auth(pathlib.Path(directory)/'auth.sqlite')
            output=StringIO()
            with patch('backend.server.sys.stdin.isatty',return_value=True),patch('backend.server.getpass.getpass',side_effect=['','a','b','password','password']),redirect_stdout(output):
                provision_user(auth,'test','admin')
            self.assertIn('cannot be empty',output.getvalue())
            self.assertIn('passwords differ',output.getvalue())
            self.assertIn('SUCCESS',output.getvalue())
            self.assertNotIn('New password: password',output.getvalue())
            self.assertEqual(auth.login('test','password','test-client')[1],'admin')
    def test_pipe_provisioning_and_eof(self):
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        with tempfile.TemporaryDirectory() as directory:
            auth=Auth(pathlib.Path(directory)/'auth.sqlite');output=StringIO()
            with patch('backend.server.sys.stdin',StringIO('pipe-test\npipe-test\n')),redirect_stdout(output):
                provision_user(auth,'pipe','admin')
            self.assertEqual(auth.login('pipe','pipe-test','test-client')[1],'admin')
            self.assertNotIn('pipe-test',output.getvalue())
            with patch('backend.server.sys.stdin',StringIO('')),redirect_stdout(output),self.assertRaises(EOFError):
                provision_user(auth,'missing','admin')
    def test_directions_and_neutral(self):
        self.assertEqual(movement(-49,49,1,-1),['#PTS0199','#Z51','#F49'])
        self.assertEqual(movement(),['#PTS5050','#Z50','#F50'])
    def test_preset_and_ranges(self):
        self.assertEqual(preset(20),'#R19');self.assertEqual(preset(100,True),'#M99')
        for v in (0,101,True):
            with self.assertRaises(ValueError):preset(v)
        for v in (-1,301,True,1.5):
            with self.assertRaises(ValueError):PANASONIC['red_gain'].encode(v)
    def test_malformed_readback(self):
        for text in ('ORI:','ORI:XYZ','ORI:12Cjunk','OBI:096','ORI:FFF'):
            with self.assertRaises(ValueError):PANASONIC['red_gain'].decode(text)
    def test_marshall_fail_closed(self):
        m=Marshall(SerialBus('127.0.0.1',1),'CV228',1)
        with self.assertRaises(NotImplementedError):m.write('red_gain',1)
        with self.assertRaises(ValueError):Marshall(m.bus,'unknown',255)
    def test_config_validation(self):
        c=json.loads((ROOT/'config.example.json').read_text());c['cameras'].append(c['cameras'][0])
        with self.assertRaises(ValueError):validate_config(c)
    def test_secret_config_rejected(self):
        c=json.loads((ROOT/'config.example.json').read_text());c['cameras'][0]['password']='do-not-store'
        with self.assertRaises(ValueError):validate_config(c)
    def test_camera_numbers_and_pending_profiles(self):
        config=json.loads((ROOT/'config.example.json').read_text(encoding='utf-8'))
        validate_config(config);self.assertEqual([c['number'] for c in config['cameras']],[1,2,3])
        config['cameras'][1]['number']=1
        with self.assertRaises(ValueError):validate_config(config)
        config['cameras'][1]['number']=2
        sony=dict(id='sony1',number=4,name='Sony',manufacturer='Sony',model='PXW-Z200',driver='sony-sdk',enabled=False,simulator=False,host='192.0.2.20')
        config['cameras'].append(sony);validate_config(config)
        sony['enabled']=True
        validate_config(config)
        sony['enabled']=False;sony['pivotcam']=True
        validate_config(config)
        sony['simulator']=True
        with self.assertRaises(ValueError):validate_config(config)
    def test_documented_fixtures(self):
        fixture=json.loads((ROOT/'tests/fixtures/panasonic-documented.json').read_text())
        for case in fixture['cases']:
            if 'pan' in case:self.assertEqual(movement(case['pan'],case['tilt'])[0],case['command'])
            if 'iris' in case:self.assertEqual(PANASONIC['iris'].decode(case['response']),case['iris'])
            if 'red_gain' in case:self.assertEqual(PANASONIC['red_gain'].decode(case['response']),case['red_gain'])

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.sim=simulator(port=0);threading.Thread(target=self.sim.serve_forever,daemon=True).start()
        self.driver=Panasonic('127.0.0.1',self.sim.server_port)
        self.config={'poll_seconds':1,'trusted_hosts':['127.0.0.1/32'],'cameras':[{'id':'p1','name':'P1','model':'AW-HE130','manufacturer':'Panasonic','driver':'panasonic','host':'127.0.0.1','port':self.sim.server_port,'simulator':True,'carbonite_input':1}]}
        self.engine=Engine(self.config,self.tmp.name);self.engine.start()
        wait_for(lambda:self.engine.cameras['p1']['params']['wb_mode']['confirmation']=='confirmed')
    def tearDown(self):
        self.engine.close();self.sim.shutdown();self.sim.server_close();self.tmp.cleanup()
    def test_http_readback_and_external_change(self):
        self.assertEqual(self.driver.write('red_gain',200),200)
        wait_for(lambda:self.engine.cameras['p1']['params']['red_gain']['value']==200)
    def test_wb_query_mapping(self):
        self.assertEqual(self.driver.write('wb_mode',2),2)
        self.assertIn('OAW:1',self.sim.model.history)
        self.assertEqual(self.driver.write('wb_mode',3),3)
    def test_ownership_and_stale_generation(self):
        gen=self.engine.command('p1','claim',{},'a')['generation']
        with self.assertRaises(PermissionError):self.engine.command('p1','claim',{},'b')
        self.engine.stop('p1')
        with self.assertRaises(ValueError):self.engine.command('p1','move',{'pan':10,'generation':gen},'a')
    def test_watchdog_stops_without_ui(self):
        gen=self.engine.command('p1','claim',{},'a')['generation']
        self.engine.command('p1','move',{'pan':20,'tilt':-5,'zoom':10,'generation':gen},'a')
        wait_for(lambda:self.sim.model.axes['pan']==20)
        wait_for(lambda:all(v==0 for v in self.sim.model.axes.values()),timeout=4)
    def test_preset_overwrite_guard(self):
        with self.assertRaises(ValueError):self.engine.command('p1','preset',{'number':1,'store':True},'a')
        self.engine.command('p1','preset',{'number':20,'store':True,'confirm':'OVERWRITE'},'a')
        self.assertIn(19,self.sim.model.presets)
    def test_manual_mode_guard_and_coalescing(self):
        c=self.engine.cameras['p1']
        with self.engine.lock:c['params']['iris_auto'].update(value=1,confirmation='confirmed',last_query=time.time())
        with self.assertRaises(ValueError):self.engine.command('p1','write',{'parameter':'iris','value':2000},'a')
        with self.engine.lock:
            for v in range(160,201):self.engine.command('p1','write',{'parameter':'red_gain','value':v},'a')
            self.assertEqual(len(c['pending']),1)
        wait_for(lambda:c['params']['red_gain']['value']==200)
    def test_snapshot_excludes_unknown(self):
        with self.engine.lock:self.engine.cameras['p1']['params']['blue_gain']['confirmation']='unknown'
        snap=self.engine.capture('p1','Reference')
        self.assertNotIn('blue_gain',snap['values']);self.assertNotIn('zoom',snap['values'])
    def test_feedback_age_is_not_live(self):
        with self.engine.lock:
            self.engine.cameras['p1']['params']['red_gain'].update(value=150,confirmation='confirmed',last_query=time.time()-40)
            p=self.engine.snapshot()['cameras'][0]['parameters']['red_gain']
            self.assertEqual(p['confirmation'],'stale');self.assertGreater(p['age_seconds'],39)
    def test_stop_discards_queued_motion(self):
        c=self.engine.cameras['p1']
        with c['io']:
            generation=self.engine.command('p1','claim',{},'a')['generation']
            self.engine.command('p1','move',{'pan':30,'generation':generation},'a')
            self.engine.stop('p1')
        time.sleep(.5)
        self.assertEqual(self.sim.model.axes['pan'],0)
    def test_auth_api_and_csrf(self):
        auth=Auth(pathlib.Path(self.tmp.name)/'users.sqlite');auth.add('test','temporary-test-password','operator')
        api=Server(('127.0.0.1',0),self.engine,auth,True);threading.Thread(target=api.serve_forever,daemon=True).start()
        def request(path,body,**headers):
            req=urllib.request.Request(f'http://127.0.0.1:{api.server_port}/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**headers})
            return json.loads(urllib.request.urlopen(req).read())
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:request('command',{'camera':'p1','action':'stop'})
            self.assertEqual(e.exception.code,403)
            login=request('login',{'username':'test','password':'temporary-test-password'})
            token=login['token']
            state=request('state',{'token':token});self.assertEqual(len(state['cameras']),1)
            from urllib.parse import urlencode
            native=urllib.request.Request(f'http://127.0.0.1:{api.server_port}/api/state',data=urlencode({'request':json.dumps({'token':token})}).encode(),headers={'Content-Type':'text/plain'})
            with urllib.request.urlopen(native) as response:self.assertEqual(len(json.load(response)['cameras']),1)
            with self.assertRaises(urllib.error.HTTPError) as e:request('command',{'camera':'p1','action':'lock','data':{'value':True},'token':token})
            self.assertEqual(e.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError):request('command',{'camera':'p1','action':'stop','token':token},Origin='http://attacker.invalid')
            self.assertNotIn('password',json.dumps(state))
        finally:api.shutdown();api.server_close()

class PanelTests(unittest.TestCase):
    def test_touch_targets_and_faders(self):
        for manufacturer in ('Panasonic','Marshall'):
            root=ET.parse(ROOT/'dashboard'/f'SW-{manufacturer}-Camera-Control.grid').getroot()
            self.assertEqual((root.get('width'),root.get('height')),('1366','800'))
            for control in root.findall('.//button')+root.findall('.//reveal'):
                self.assertGreaterEqual(int(control.get('width')),48,control.get('name'))
                self.assertGreaterEqual(int(control.get('height')),48,control.get('name'))
            for control in root.findall('.//param[@left]'):
                self.assertGreaterEqual(int(control.get('height')),48,control.get('oid'))
            faders=root.findall('.//param[@widget="26"]')
            self.assertGreaterEqual(len(faders),6 if manufacturer=='Panasonic' else 8)
            self.assertFalse(root.findall('.//param[@left][@widget="4"]'))
            if manufacturer=='Marshall':self.assertIsNotNone(root.find(".//abs[@id='page_image']"))
    def test_aura_pages_logos_and_no_overflow(self):
        from urllib.parse import urlparse
        from urllib.request import url2pathname
        for manufacturer in ('Panasonic','Marshall','Sony'):
            root=ET.parse(ROOT/'dashboard'/f'SW-{manufacturer}-Camera-Control.grid').getroot()
            logo=root.find('.//image');self.assertIsNotNone(logo)
            self.assertEqual(pathlib.Path(url2pathname(urlparse(logo.get('src')).path)).name,manufacturer.lower()+'.png')
            self.assertTrue(pathlib.Path(url2pathname(urlparse(logo.get('src')).path)).is_file())
            for parent in root.iter('abs'):
                width=int(parent.get('width','1366'));height=int(parent.get('height','800'))
                for child in parent:
                    if child.get('left') is not None and child.get('width') is not None:
                        self.assertLessEqual(int(child.get('left'))+int(child.get('width')),width)
                    if child.get('top') is not None and child.get('height') is not None:
                        self.assertLessEqual(int(child.get('top'))+int(child.get('height')),height)
            self.assertIsNotNone(root.find(".//abs[@id='page_config']"))
            if manufacturer=='Panasonic':self.assertIsNotNone(root.find(".//abs[@id='page_td1c']"))
    def test_two_native_panels_contract(self):
        for manufacturer in ('Panasonic','Marshall'):
            tree=ET.parse(ROOT/'dashboard'/f'SW-{manufacturer}-Camera-Control.grid');root=tree.getroot()
            self.assertEqual(root.tag,'abs');self.assertEqual(root.get('contexttype'),'opengear')
            self.assertFalse(root.findall('.//browser'))
            ids=[x.get('oid') for x in root.findall('./meta/params/param')]
            self.assertEqual(len(ids),len(set(ids)))
            self.assertIn('ogscript.asyncPost',root.find('api').text)
            from backend.protocol import PANASONIC
            from backend.core import MARSHALL_LAB
            definitions=PANASONIC if manufacturer=='Panasonic' else MARSHALL_LAB
            listeners=root.findall("./ogscript[@handles='onchange']")
            self.assertEqual({x.get('oid') for x in listeners},set(definitions))
            self.assertEqual(len(listeners),len(definitions))
            self.assertFalse(root.findall(".//param/ogscript[@handles='onchange']"))
            if manufacturer=='Panasonic':
                presets=[b for b in root.findall('.//button') if (b.findtext('task') or '').startswith('preset(')]
                self.assertEqual(len(presets),20)
            else:self.assertNotIn('PTZ ·',ET.tostring(root,encoding='unicode'))

if __name__=='__main__':unittest.main()
