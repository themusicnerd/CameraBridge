import json
import pathlib
import socket
import tempfile
import threading
import time
import unittest
from backend.core import Engine
from backend.simulator import server as simulator
from backend.ross import decode,ViscaError,PresetFollower,LabViscaServer
from tests.test_system import wait_for

class ViscaCodecTests(unittest.TestCase):
    def test_direction_speed_and_preset_index(self):
        kind,axes=decode(bytes.fromhex('81 01 06 01 18 14 01 01 FF'))
        self.assertEqual((kind,axes),('pan_tilt',{'pan':-49,'tilt':49}))
        self.assertEqual(decode(bytes.fromhex('81 01 04 07 27 FF')),('zoom',{'zoom':49}))
        self.assertEqual(decode(bytes.fromhex('81 01 04 07 37 FF')),('zoom',{'zoom':-49}))
        self.assertEqual(decode(bytes.fromhex('81 01 04 07 20 FF')),('zoom',{'zoom':1}))
        self.assertEqual(decode(bytes.fromhex('81 01 06 01 01 01 02 02 FF')),('pan_tilt',{'pan':1,'tilt':-1}))
        self.assertEqual(decode(bytes.fromhex('81 01 04 3F 02 13 FF')),('preset',{'number':20,'store':False}))
    def test_reject_unsupported_or_malformed(self):
        for frame in ['81 01 06 01 19 14 01 01 FF','82 01 04 07 00 FF','81 01 04 07 28 FF','81 01 06 04 FF','81 01 04 3F 00 01 FF']:
            with self.assertRaises(ValueError):decode(bytes.fromhex(frame))

class RossLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.sims=[];cameras=[]
        for i in range(2):
            sim=simulator(port=0);self.sims.append(sim);threading.Thread(target=sim.serve_forever,daemon=True).start()
            cameras.append(dict(id='p'+str(i+1),name='Camera '+str(i+1),manufacturer='Panasonic',model='AW-HE130',driver='panasonic',host='127.0.0.1',port=sim.server_port,simulator=True))
        self.engine=Engine({'cameras':cameras,'poll_seconds':1},self.tmp.name);self.engine.start()
        wait_for(lambda:all(c['params']['focus_auto']['confirmation']=='confirmed' for c in self.engine.cameras.values()))
        self.follower=PresetFollower(self.engine)
    def tearDown(self):
        self.engine.close()
        for sim in self.sims:sim.shutdown();sim.server_close()
        self.tmp.cleanup()
    def neutral(self):
        epoch=self.follower.epoch;camera=self.follower.selected
        self.follower.apply_motion(camera,'pan_tilt',{'pan':0,'tilt':0},epoch,time.monotonic())
        self.follower.apply_motion(camera,'zoom',{'zoom':0},epoch,time.monotonic())
    def test_preset_only_handover_and_stale_motion(self):
        result=self.follower.bus_event('preset','p1');epoch=result['epoch'];self.neutral()
        self.follower.apply_motion('p1','pan_tilt',{'pan':20,'tilt':10},epoch,time.monotonic())
        self.follower.apply_motion('p1','zoom',{'zoom':12},epoch,time.monotonic())
        self.assertEqual(self.sims[0].model.axes,{'pan':20,'tilt':10,'zoom':12,'focus':0})
        self.follower.bus_event('program','p2');self.assertEqual(self.follower.selected,'p1')
        self.follower.bus_event('preset','p2');self.assertTrue(all(v==0 for v in self.sims[0].model.axes.values()))
        with self.assertRaises(ViscaError):self.follower.apply_motion('p1','zoom',{'zoom':20},epoch,time.monotonic())
        with self.assertRaises(ViscaError):self.follower.apply_motion('p2','zoom',{'zoom':20},self.follower.epoch,time.monotonic())
        with self.assertRaises(ViscaError):self.follower.apply_motion('p2','zoom',{'zoom':20},epoch,time.monotonic())
        self.neutral();self.follower.apply_motion('p2','zoom',{'zoom':20},self.follower.epoch,time.monotonic())
        self.assertEqual(self.sims[1].model.axes['zoom'],20)
        self.engine.stop('p2')
        with self.assertRaises(ViscaError):self.follower.apply_motion('p2','zoom',{'zoom':20},self.follower.epoch,time.monotonic())
    def test_preset_name_persists(self):
        self.engine.command('p1','label_preset',{'number':20,'name':'Weather map'},'test')
        self.assertEqual(self.engine.snapshot()['cameras'][0]['preset_names']['20'],'Weather map')
        self.assertEqual(json.loads((pathlib.Path(self.tmp.name)/'preset-names.json').read_text())['p1']['20'],'Weather map')
    def test_fragmented_tcp_preset_focus_and_disconnect_stop(self):
        self.follower.bus_event('preset','p1')
        service=LabViscaServer(('127.0.0.1',0),self.engine,'p1',self.follower,allow_store=True)
        threading.Thread(target=service.serve_forever,daemon=True).start()
        def packet(sock,hexstr,size=6):
            data=bytes.fromhex(hexstr);sock.sendall(data[:2]);sock.sendall(data[2:]);reply=b''
            while len(reply)<size:
                part=sock.recv(size-len(reply))
                if not part:raise AssertionError('Gateway disconnected')
                reply+=part
            return reply
        try:
            with socket.create_connection(service.server_address,timeout=3) as client:
                self.assertEqual(packet(client,'81 01 06 01 01 01 03 03 FF'),bytes.fromhex('90 41 FF 90 51 FF'))
                self.assertEqual(packet(client,'81 01 04 07 00 FF'),bytes.fromhex('90 41 FF 90 51 FF'))
                self.assertEqual(packet(client,'81 01 04 07 27 FF'),bytes.fromhex('90 41 FF 90 51 FF'))
                self.assertEqual(self.sims[0].model.axes['zoom'],49)
            wait_for(lambda:self.sims[0].model.axes['zoom']==0)
            wait_for(lambda:service.active==0)
            # The synthetic preset has an immediate, verifiable position restore.
            with socket.create_connection(service.server_address,timeout=3) as client:
                self.engine.cameras['p1']['driver'].write('zoom',2000)
                self.assertEqual(packet(client,'81 01 04 3F 01 13 FF'),bytes.fromhex('90 41 FF 90 51 FF'))
                self.engine.cameras['p1']['driver'].write('zoom',3000)
                self.assertEqual(packet(client,'81 01 04 3F 02 13 FF'),bytes.fromhex('90 41 FF 90 51 FF'))
                self.assertEqual(self.engine.cameras['p1']['driver'].query('zoom'),2000)
                self.assertEqual(packet(client,'81 09 04 38 FF',4),bytes.fromhex('90 50 03 FF'))
                service.allow_store=False
                self.assertEqual(packet(client,'81 01 04 3F 01 12 FF',4),bytes.fromhex('90 60 41 FF'))
                self.assertNotIn(18,self.sims[0].model.presets)
        finally:service.shutdown();service.server_close()
    def test_hardware_and_nonloopback_are_rejected(self):
        with self.assertRaises(ValueError):LabViscaServer(('0.0.0.0',0),self.engine,'p1',self.follower)
        self.engine.cameras['p1']['config']['simulator']=False
        with self.assertRaises(ValueError):LabViscaServer(('127.0.0.1',0),self.engine,'p1',self.follower)
    def test_gateway_close_drains_and_stops_active_controller(self):
        self.follower.bus_event('preset','p1');self.neutral()
        service=LabViscaServer(('127.0.0.1',0),self.engine,'p1',self.follower)
        threading.Thread(target=service.serve_forever,daemon=True).start()
        with socket.create_connection(service.server_address,timeout=3) as client:
            client.sendall(bytes.fromhex('81 01 04 07 27 FF'))
            reply=b''
            while len(reply)<6:reply+=client.recv(6-len(reply))
            self.assertEqual(reply,bytes.fromhex('90 41 FF 90 51 FF'))
            with self.engine.lock:self.engine.cameras['p1']['motion_deadline']=time.monotonic()+20
            self.assertEqual(self.sims[0].model.axes['zoom'],49)
            service.shutdown();service.server_close()
            self.assertEqual(service.active,0)
            self.assertTrue(all(v==0 for v in self.sims[0].model.axes.values()))
