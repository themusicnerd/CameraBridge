import copy
import pathlib
import socket
import tempfile
import threading
import time
import unittest
from backend.server import Auth,validate_config
from backend.core import Engine
from backend.runtime import Runtime
from backend.tally import TallyServer

class PersistentSessionTests(unittest.TestCase):
    def test_browser_session_survives_restart_and_signout_revokes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'auth.sqlite'
            first=Auth(path);first.add('admin','test','admin')
            token=first.login('admin','test','local')[0]
            restarted=Auth(path);self.assertEqual(restarted.role(token),'admin')
            restarted.logout(token)
            self.assertIsNone(restarted.role(token));self.assertIsNone(first.role(token))

    def test_password_change_from_another_process_revokes_cached_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'auth.sqlite';backend=Auth(path);backend.add('admin','test','admin')
            token=backend.login('admin','test','local')[0]
            self.assertEqual(backend.role(token),'admin')
            Auth(path).add('admin','new','admin')
            self.assertIsNone(backend.role(token))
            self.assertEqual(backend.role(backend.login('admin','new','local')[0]),'admin')

class RuntimeTests(unittest.TestCase):
    def test_name_and_tally_option_changes_keep_the_engine_and_receiver(self):
        with tempfile.TemporaryDirectory() as directory:
            config=validate_config({'cameras':[dict(id='camera',number=1,name='Camera',manufacturer='Panasonic',model='AW-HE40',driver='panasonic',host='192.0.2.1')]})
            runtime=Runtime(config,directory);engine=runtime.engine
            updated=copy.deepcopy(config);updated['cameras'][0].update(name='Studio',tally_enabled=False)
            self.assertTrue(runtime.update_metadata(updated));self.assertIs(runtime.engine,engine)
            self.assertEqual(engine.cameras['camera']['config']['name'],'Studio')
            self.assertFalse(engine.cameras['camera']['tally']['enabled'])
            updated=copy.deepcopy(updated);updated['cameras'][0]['host']='192.0.2.2'
            self.assertFalse(runtime.update_metadata(updated))

class TSLStatusTests(unittest.TestCase):
    def test_only_valid_packets_from_the_configured_source_establish_receiving(self):
        with tempfile.TemporaryDirectory() as directory:
            config=validate_config({'cameras':[]});engine=Engine(config,directory)
            receiver=TallyServer(('127.0.0.1',0),engine,'127.0.0.1')
            thread=threading.Thread(target=receiver.serve_forever,daemon=True);thread.start()
            try:
                self.assertEqual(engine.snapshot()['tsl']['state'],'waiting')
                self.assertFalse(receiver.verify_request(None,('192.0.2.1',999)))
                with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
                    sender.sendto(b'bad',receiver.server_address)
                    sender.sendto(bytes([0x81,2])+b'Camera 1        ',receiver.server_address)
                deadline=time.monotonic()+2
                while engine.snapshot()['tsl']['packets']!=1 and time.monotonic()<deadline:time.sleep(.01)
                status=engine.snapshot()['tsl'];self.assertEqual(status['state'],'receiving')
                self.assertEqual(status['invalid_packets'],1);self.assertEqual(status['rejected_sources'],1)
                self.assertEqual(status['messages'],1)
                engine.tsl['last_packet']=time.time()-11
                self.assertEqual(engine.snapshot()['tsl']['state'],'stale')
            finally:receiver.shutdown();receiver.server_close();thread.join()

    def test_disabled_lamp_still_receives_tsl_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config=validate_config({'cameras':[dict(id='camera',number=1,name='Camera',manufacturer='Panasonic',model='AW-HE40',driver='panasonic',host='192.0.2.1',tally_enabled=False)]})
            engine=Engine(config,directory)
            self.assertEqual(engine.set_tally('camera',True,False,'TSL 3.1')['status'],'disabled for this camera')
            self.assertEqual(engine.snapshot()['cameras'][0]['tally']['received'],{'program':True,'preview':False})
            self.assertIsNone(engine.cameras['camera']['tally_pending'])
