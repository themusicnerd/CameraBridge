import copy
import json
import pathlib
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock,patch
from backend.sony import Sony,SonyCredentials,SONY
from backend.core import Engine
from backend.drivers import Panasonic
from backend.server import validate_config
from backend.tally import TallyServer,decode
from backend.simulator import server as simulator

def wait(predicate,timeout=4):
    limit=time.monotonic()+timeout
    while time.monotonic()<limit:
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Expected state was not observed')

class FakeSDK:
    """Process contract fixture, not a Sony protocol or physical camera emulator."""
    def __init__(self):
        self.requests=[];self.closed=False;self.apply=True
        self.properties={
            'iris':dict(value=280,readable=True,writable=True,range=False,values=[280,400,560]),
            'iris_auto':dict(value=2,readable=True,writable=True,range=False,values=[1,2]),
            'zoom':dict(value=100,readable=True,writable=False,range=False,values=[]),
            'zoom_jog':dict(value=0,readable=True,writable=True,range=False,values=[-1,0,1]),
            'focus_jog':dict(value=0,readable=True,writable=True,range=False,values=[-1,0,1]),
        }
    def request(self,line,timeout=3):
        self.requests.append(line)
        if line.startswith('connect '):return {'connected':True}
        if line=='state':return {'properties':copy.deepcopy(self.properties)}
        op,key,value=line.split()
        if self.apply:self.properties[key]['value']=int(value)
        return {'sent':True}
    def close(self):self.closed=True

class SonyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.config=dict(id='sony1',number=1,name='Sony fixture',driver='sony-sdk',manufacturer='Sony',model='PXW-Z200',host='192.0.2.20')
        SonyCredentials(self.tmp.name).save('sony1','operator','private-example','verified-example-identity')
        self.fake=FakeSDK();self.driver=Sony(self.config,self.tmp.name,self.fake)
    def test_credentials_roundtrip_and_config_exclusion(self):
        store=SonyCredentials(self.tmp.name);self.assertEqual(store.load('sony1')['password'],'private-example')
        if __import__('sys').platform=='win32':self.assertNotIn(b'private-example',store.path('sony1').read_bytes())
        else:self.assertEqual(store.path('sony1').stat().st_mode&0o777,0o600)
        with self.assertRaises(ValueError):store.path('../other')
        self.assertNotIn('password',json.dumps(self.config))
    def test_pinned_identity_capabilities_and_independent_readback(self):
        self.assertEqual(self.driver.query('iris'),280)
        request=self.fake.requests[0].split()
        self.assertEqual(bytes.fromhex(request[4]).decode(),'verified-example-identity')
        self.assertFalse(self.driver.metadata('zoom')['writable'])
        self.assertEqual(self.driver.metadata('iris')['allowed'],[280,400,560])
        self.assertEqual(self.driver.write('iris',400),400)
        self.fake.apply=False
        self.assertEqual(self.driver.write('iris',560),400)
    def test_unavailable_controls_and_no_pan_tilt(self):
        self.assertIsNone(self.driver.query('red_gain'))
        with self.assertRaises(ValueError):self.driver.write('zoom',200)
        with self.assertRaises(ValueError):self.driver.move(pan=1)
        self.driver.move(zoom=-24);self.assertEqual(self.fake.properties['zoom_jog']['value'],-1)
        self.driver.stop();self.assertEqual(self.fake.properties['zoom_jog']['value'],0)
    def test_z200_tally_is_unsupported_without_record_commands(self):
        with self.assertRaises(NotImplementedError):self.driver.tally(True)
        self.assertFalse(any(r.startswith('set ') for r in self.fake.requests))
    def test_supported_sony_lamps_use_explicit_sdk_enumeration(self):
        for key in ('tally_red','tally_green'):self.fake.properties[key]=dict(value=1,readable=True,writable=True,range=False,values=[1,2])
        self.assertEqual(self.driver.tally(False,True),{'program':False,'preview':True})
        self.assertEqual(self.driver.tally(True,True),{'program':True,'preview':False})
    def test_engine_accepts_sony_and_reports_missing_properties(self):
        with patch('backend.core.Sony',return_value=self.driver):
            # Patch only construction; preserve isinstance checks below.
            engine=Engine({'cameras':[self.config],'poll_seconds':1},self.tmp.name)
        engine.start();self.addCleanup(engine.close)
        wait(lambda:engine.cameras['sony1']['params']['iris']['confirmation']=='confirmed')
        with engine.lock:engine.cameras['sony1']['params']['iris_auto'].update(value=2,confirmation='confirmed',last_query=time.time())
        engine.command('sony1','write',{'parameter':'iris','value':400},'test')
        wait(lambda:engine.cameras['sony1']['params']['iris']['value']==400)
        state=engine.snapshot()['cameras'][0]
        self.assertTrue(state['tally']['enabled']);self.assertFalse(state['parameters']['zoom']['writable'])
        engine.set_tally('sony1',True)
        wait(lambda:engine.cameras['sony1']['tally']['status']=='unsupported')

class TallyTests(unittest.TestCase):
    def test_panasonic_wire_commands_and_readback(self):
        driver=Panasonic('127.0.0.1');driver.send=Mock(side_effect=['tAE1','dA1','dA1'])
        self.assertEqual(driver.tally(True),{'program':True,'preview':False})
        self.assertEqual([c.args[0] for c in driver.send.call_args_list],['#TAE1','#DA1','#DA'])
        driver.send=Mock(side_effect=['tAE1','dA1','dA0'])
        self.assertEqual(driver.tally(True)['program'],False)
    def test_default_enabled_optout_and_worker_feedback(self):
        sim=simulator(port=0);threading.Thread(target=sim.serve_forever,daemon=True).start()
        self.addCleanup(sim.server_close);self.addCleanup(sim.shutdown)
        with tempfile.TemporaryDirectory() as directory:
            c=dict(id='p1',name='P',model='AW-HE130',manufacturer='Panasonic',driver='panasonic',host='127.0.0.1',port=sim.server_port,simulator=True)
            cfg=validate_config({'cameras':[c]});self.assertTrue(c['tally_enabled'])
            engine=Engine(cfg,directory);engine.start()
            try:
                engine.set_tally('p1',True);wait(lambda:engine.cameras['p1']['tally']['status']=='confirmed')
                self.assertTrue(sim.model.tally_on)
                engine.set_tally('p1',False);wait(lambda:engine.cameras['p1']['tally']['actual']=={'program':False,'preview':False})
                c['tally_enabled']=False
                count=len(sim.model.history);self.assertEqual(engine.set_tally('p1',True)['status'],'disabled for this camera')
                time.sleep(.05);self.assertNotIn('#DA1',sim.model.history[count:])
                with self.assertRaises(ValueError):engine.set_tally('p1',1)
            finally:engine.close()
    def test_tsl_packets_are_validated_atomically(self):
        packet=bytes([0x80,0x31])+b'CAMERA 1        '
        self.assertEqual(decode(packet),[(0,True,False)])
        self.assertEqual(decode(bytes([0xfe,0x32])+b'CAMERA 127      '),[(126,False,True)])
        for data in (b'',packet[:-1],packet+bytes(18),bytes([0xff,0])+b' '*16):
            with self.assertRaises(ValueError):decode(data)
    def test_udp_mapping_and_source_restriction(self):
        engine=Mock();engine.cameras={'sony':{'config':{'carbonite_input':3}}}
        receiver=TallyServer(('127.0.0.1',0),engine,'127.0.0.1')
        thread=threading.Thread(target=receiver.serve_forever,daemon=True);thread.start()
        try:
            packet=bytes([0x82,0x33])+b'CAMERA 3        '
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.sendto(packet,receiver.server_address)
            wait(lambda:engine.set_tally.called);engine.set_tally.assert_called_once_with('sony',True,True,'TSL 3.1')
            self.assertFalse(receiver.verify_request(None,('192.0.2.5',12345)))
        finally:receiver.shutdown();receiver.server_close();thread.join()

if __name__=='__main__':unittest.main()
