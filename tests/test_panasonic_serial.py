import copy
import socketserver
import tempfile
import threading
import time
import unittest
from backend.core import Engine
from backend.panasonic_serial import MODEL,PanasonicSerial
from backend.server import validate_config
from backend.ross import FixedCameraController
from tests.test_system import wait_for

class Gateway(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True
    def __init__(self):
        self.commands=[];self.frames=[];self.ack_only=False;self.delay_notification=False
        self.values={'ORG':'1E','OBG':'1E','ODT':'1'}
        super().__init__(('127.0.0.1',0),GatewayHandler)

class GatewayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        buffer=bytearray()
        while True:
            chunk=self.request.recv(256)
            if not chunk:return
            buffer.extend(chunk)
            while buffer:
                end=buffer.find(3 if buffer[0]==2 else 13)
                if end<0:break
                frame=bytes(buffer[:end+1]);del buffer[:end+1]
                command=frame[1:-1].decode() if frame[0]==2 else frame[:-1].decode()
                self.server.commands.append(command);self.server.frames.append(frame)
                if command.startswith('#'):continue
                if self.server.ack_only:self.request.sendall(b'\x06');continue
                if command=='QID':reply='OID:AK-HC1800G'
                elif command.startswith('Q'):
                    key={'QGR':'ORG','QGB':'OBG','QDT':'ODT'}[command]
                    reply=({'ORG':'OGR','OBG':'OGB'}.get(key,key))+':'+self.server.values[key]
                elif command=='OWS':self.server.delay_notification=True;continue
                else:
                    key,value=command.split(':');self.server.values[key]=value;reply=command
                extra=b'\x02OWS\x03' if self.server.delay_notification else b''
                self.server.delay_notification=False
                # ACK and camera result deliberately arrive in separate pieces.
                self.request.sendall(b'\x06'+extra+b'\x02'+reply[:2].encode())
                self.request.sendall(reply[2:].encode()+b'\x03')

class SerialPanasonicTests(unittest.TestCase):
    def setUp(self):
        self.gateway=Gateway();threading.Thread(target=self.gateway.serve_forever,daemon=True).start()
        self.camera=PanasonicSerial('127.0.0.1',self.gateway.server_address[1])
    def tearDown(self):self.camera.close();self.gateway.shutdown();self.gateway.server_close()
    def test_camera_ack_fragmented_results_and_gain_readback(self):
        self.assertIsNone(self.camera.query('iris_auto'))
        self.assertEqual(self.camera.query('red_gain'),150)
        self.assertEqual(self.camera.write('red_gain',155),155)
        self.assertEqual(self.camera.query('detail'),1)
        self.assertEqual(self.gateway.frames[0],b'\x02QID\x03')
        self.assertIn(b'\x02ORG:1F\x03',self.gateway.frames)
    def test_head_motion_is_cr_framed_with_no_invented_ack(self):
        self.camera.move(pan=-20,tilt=10,zoom=12,focus=-5)
        wait_for(lambda:len(self.gateway.commands)>=4)
        self.assertEqual(self.gateway.commands[:4],['#P30','#T60','#Z62','#F45'])
        self.assertTrue(all(frame.endswith(b'\r') for frame in self.gateway.frames))
        before=len(self.gateway.commands);self.camera.move(pan=-20,tilt=10,zoom=12,focus=-5)
        self.assertEqual(len(self.gateway.commands),before)
        self.assertIsNone(self.camera.send('#P50',response=False))
        with self.assertRaises(ValueError):self.camera.send('#P50')
        self.camera.stop(active_only=True)
        wait_for(lambda:'#F50' in self.gateway.commands)
        self.assertNotIn('#PTS5050',self.gateway.commands)
    def test_presets_iris_and_tally_have_sent_status(self):
        self.camera.preset(50);self.camera.preset(50,store=True)
        with self.assertRaises(ValueError):self.camera.preset(51)
        self.assertIsNone(self.camera.write('iris',0x555));self.assertIsNone(self.camera.write('iris',0xFFF))
        result=self.camera.tally(True);self.assertIsNone(result['program']);self.assertEqual(result['delivery'],'sent')
        wait_for(lambda:'#DA1' in self.gateway.commands)
        for command in ['#R49','#M49','#I01','#I99','#DA1']:self.assertIn(command,self.gateway.commands)
        self.assertIsNone(self.camera.query('focus_auto'));self.assertFalse(self.camera.metadata('focus_auto')['writable'])
        self.assertNotIn('#D1',self.gateway.commands)
        with self.assertRaises(NotImplementedError):self.camera.write('wb_mode',2)
    def test_ack_only_is_not_camera_feedback_and_no_command_retry(self):
        self.gateway.ack_only=True;self.camera.timeout=.08
        with self.assertRaises(TimeoutError):self.camera.query('red_gain')
        self.assertEqual(self.gateway.commands,['QGR']);self.assertFalse(self.camera.connected)
    def test_one_shot_delayed_result_does_not_corrupt_next_query(self):
        self.assertEqual(self.camera.white_balance_once()['status'],'sent')
        self.assertEqual(self.camera.query('blue_gain'),150)
    def test_configurable_endpoint_and_fixed_positioner_integration(self):
        cfg={'cameras':[dict(id='p1',manufacturer='Panasonic',model=MODEL,driver='panasonic-serial',host='127.0.0.1',port=self.gateway.server_address[1],pivotcam=True)]}
        config=validate_config(copy.deepcopy(cfg))
        with tempfile.TemporaryDirectory() as tmp:
            engine=Engine(config,tmp);follower=FixedCameraController(engine,'p1')
            try:
                follower.apply_motion('p1','pan_tilt',{'pan':10,'tilt':-5},follower.epoch,time.monotonic())
                follower.apply_motion('p1','pan_tilt',{'pan':0,'tilt':0},follower.epoch,time.monotonic()-2)
                wait_for(lambda:'#T50' in self.gateway.commands)
                self.assertIn('#P60',self.gateway.commands);self.assertIn('#T45',self.gateway.commands)
            finally:engine.close()
        bad=copy.deepcopy(cfg);bad['cameras'][0].pop('port')
        with self.assertRaises(ValueError):validate_config(bad)
        bad=copy.deepcopy(cfg);other=dict(bad['cameras'][0],id='p2',number=2);bad['cameras'].append(other)
        with self.assertRaises(ValueError):validate_config(bad)
    def test_engine_write_only_iris_and_unverified_lamp(self):
        cfg=validate_config({'poll_seconds':1,'cameras':[dict(id='p1',manufacturer='Panasonic',model=MODEL,driver='panasonic-serial',host='127.0.0.1',port=self.gateway.server_address[1])]})
        with tempfile.TemporaryDirectory() as tmp:
            engine=Engine(cfg,tmp);engine.start()
            try:
                wait_for(lambda:engine.cameras['p1']['health']=='online')
                engine.command('p1','write',dict(parameter='iris',value=0xFFF),'test')
                wait_for(lambda:engine.cameras['p1']['params']['iris']['confirmation']=='sent')
                self.assertIsNone(engine.cameras['p1']['params']['iris']['value'])
                engine.set_tally('p1',True)
                wait_for(lambda:engine.cameras['p1']['tally']['status']=='sent')
                self.assertIsNone(engine.cameras['p1']['tally']['actual']['program'])
            finally:engine.close()
