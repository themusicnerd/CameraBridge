import copy
import http.client
import json
import pathlib
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from backend.server import Auth, ROOT, Server, validate_config
from tools.td_panel_host import panel_bytes
from camerabridge import export_panels


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.storage = pathlib.Path(self.temp.name)
        self.config = validate_config(json.loads((ROOT/'config.example.json').read_text()))
        self.auth = Auth(self.storage/'auth.sqlite')
        self.auth.add('admin','test','admin'); self.auth.add('operator','test','operator')
        self.admin = self.auth.login('admin','test','127.0.0.1')[0]
        self.operator = self.auth.login('operator','test','127.0.0.1')[0]
        self.server = Server(('127.0.0.1',0),SimpleNamespace(config=self.config,storage=self.storage,cameras={}),self.auth,desktop_control=True)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()

    def api(self,data,token=None,path='/api/setup'):
        c=http.client.HTTPConnection(*self.server.server_address,timeout=3)
        c.request('POST',path,json.dumps(dict(data,token=self.admin if token is None else token)),{'Content-Type':'application/json'})
        r=c.getresponse();status=r.status;body=json.loads(r.read());c.close();return status,body

    def test_auth_and_roster_changes_are_saved_then_applied(self):
        self.assertEqual(self.api({},token='')[0],403)
        self.assertEqual(self.api({},token=self.operator)[0],403)
        status,loaded=self.api({});self.assertEqual(status,200);self.assertFalse(loaded['pending'])
        camera=copy.deepcopy(self.config['cameras'][0]);camera.update(id='camera_4',number=4,host='192.168.96.20',name='Studio',simulator=False)
        status,saved=self.api(dict(operation='save',revision=loaded['revision'],previous='',camera=camera))
        self.assertEqual(status,200);self.assertEqual(len(saved['configuration']['cameras']),4)
        self.assertEqual(saved['configuration']['pivotcam'],self.config['pivotcam'])
        self.assertEqual(len(self.config['cameras']),3,'Saving must not alter the active engine')
        self.assertFalse((self.storage/'desktop-restart.json').exists())
        self.assertEqual(self.api(dict(operation='remove',revision=loaded['revision'],camera='camera_4',confirmation='REMOVE'))[0],400)
        self.assertEqual(self.api(dict(operation='remove',revision=saved['revision'],camera='camera_4',confirmation=''))[0],400)
        status,removed=self.api(dict(operation='remove',revision=saved['revision'],camera='camera_4',confirmation='REMOVE'))
        self.assertEqual(status,200);self.assertEqual(len(removed['configuration']['cameras']),3)
        self.assertEqual(self.api(dict(operation='apply',revision=removed['revision']))[0],200)
        self.assertEqual(json.loads((self.storage/'desktop-restart.json').read_text()),{'apply':True})

    def test_validation_and_sony_access_for_pending_camera(self):
        _,loaded=self.api({})
        camera=dict(id='sony4',number=4,name='Sony',manufacturer='Sony',model='PXW-Z200',driver='sony-sdk',host='192.168.96.24',port=80,simulator=False,enabled=True,carbonite_input=4)
        status,saved=self.api(dict(operation='save',revision=loaded['revision'],camera=camera))
        self.assertEqual(status,200);self.assertTrue(saved['configuration']['cameras'][-1]['tally_enabled'])
        access=dict(camera='sony4',username='camera-user',password='test-camera-secret',fingerprint='SHA256:test',acknowledge_terms=True)
        self.assertEqual(self.api(access,path='/api/sony/credentials')[0],200)
        _,result=self.api({});self.assertNotIn('test-camera-secret',json.dumps(result))
        self.assertNotIn('test-camera-secret',(self.storage/'config.pending.json').read_text())
        camera['password']='must-not-be-config';camera['name']='Changed'
        self.assertEqual(self.api(dict(operation='save',revision=saved['revision'],previous='sony4',camera=camera))[0],400)
        self.assertNotIn('must-not-be-config',(self.storage/'config.pending.json').read_text())

    def test_bridge_settings_validate_before_save(self):
        _,loaded=self.api({})
        pivot=dict(enabled=True,bind='192.168.96.61',controller='192.168.96.123',base_port=19010)
        tally=dict(enabled=True,bind='192.168.96.61',source='192.168.96.123',port=5727,program_tally=2,address_offset=0)
        status,saved=self.api(dict(operation='bridge',revision=loaded['revision'],pivotcam=pivot,tally=tally))
        self.assertEqual(status,200);self.assertEqual(saved['configuration']['cameras'],loaded['configuration']['cameras'])
        self.assertEqual(saved['configuration']['pivotcam']['base_port']+1,19011)
        tally['source']='bad address'
        self.assertEqual(self.api(dict(operation='bridge',revision=saved['revision'],pivotcam=pivot,tally=tally))[0],400)
        self.assertEqual(json.loads((self.storage/'config.pending.json').read_text())['tally']['source'],'192.168.96.123')

    def test_unified_panel_export_and_remote_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_panels(tmp);root=ET.parse(pathlib.Path(tmp)/'CameraBridge.grid').getroot()
            ids=[e.get('id') for e in root.iter() if e.get('id')]
            self.assertEqual(len(ids),len(set(ids)))
            definitions=root.findall('./meta/params/param');oids=[e.get('oid') for e in definitions]
            self.assertEqual(len(oids),len(set(oids)))
            for oid in ('password','setup_access_password','sony_password','panasonic_password','marshall_password'):
                self.assertEqual(next(p for p in definitions if p.get('oid')==oid).get('value'),'')
            remote=panel_bytes('CameraBridge','http://192.168.96.61:8089')
            self.assertNotIn(b'file://',remote)
            remote=ET.fromstring(remote)
            self.assertEqual({p.get('src') for p in remote.iter('image')},{'http://192.168.96.61:8089/assets/'+n+'.png' for n in ('sony','panasonic','marshall')})
