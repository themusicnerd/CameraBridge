import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock
from backend.core import Engine
from backend.ross import FixedCameraController,PivotCamServer
from backend.scheduling import CameraAccess
from backend.simulator import server as simulator
from tests.test_system import wait_for

class CameraAccessTests(unittest.TestCase):
    def test_stop_precedes_motion_and_poll_and_access_is_reentrant(self):
        access=CameraAccess();order=[];threads=[]
        def take(priority,label):
            with access.priority(priority):
                with access:order.append(label)
        with access:
            for priority,label in [(10,'poll'),(-10,'motion'),(-20,'stop')]:
                thread=threading.Thread(target=take,args=(priority,label));thread.start();threads.append(thread)
            wait_for(lambda:len(access.waiters)==3)
        for thread in threads:thread.join(2);self.assertFalse(thread.is_alive())
        self.assertEqual(order,['stop','motion','poll'])

class FixedMotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.engine=Engine({'cameras':[dict(id='p1',manufacturer='Panasonic',model='AW-HE40',driver='panasonic',host='127.0.0.1')]},self.tmp.name)
        self.camera=self.engine.cameras['p1'];self.driver=self.camera['driver']
        self.driver.send=Mock(side_effect=lambda command:'pTS'+command[4:] if command.startswith('#PTS') else command[1].lower()+'S'+command[2:])
        self.follower=FixedCameraController(self.engine,'p1')
    def tearDown(self):self.tmp.cleanup()
    def move(self,kind,axes,age=0):self.follower.apply_motion('p1',kind,axes,self.follower.epoch,time.monotonic()-age)
    def test_first_pan_and_zoom_work_without_unrelated_neutral_and_after_stop(self):
        self.move('pan_tilt',{'pan':12,'tilt':0});self.move('zoom',{'zoom':10})
        self.assertTrue(self.camera['moving'])
        self.engine.stop('p1')
        self.move('pan_tilt',{'pan':-12,'tilt':5})
        self.assertEqual(self.driver.motion_state['#PTS'],'#PTS3855')
    def test_delayed_stop_is_delivered_but_delayed_motion_is_rejected(self):
        self.move('pan_tilt',{'pan':12,'tilt':0})
        self.move('pan_tilt',{'pan':0,'tilt':0},age=2)
        self.assertEqual(self.driver.motion_state['#PTS'],'#PTS5050');self.assertFalse(self.camera['moving'])
        with self.assertRaises(ValueError):self.move('pan_tilt',{'pan':12,'tilt':0},age=2)
    def test_queued_motion_before_stop_cannot_restart_fixed_endpoint(self):
        generation=self.camera['generation']
        self.engine.stop('p1');self.driver.send.reset_mock()
        with self.assertRaisesRegex(ValueError,'superseded by stop'):
            self.follower.apply_motion('p1','pan_tilt',{'pan':12,'tilt':0},self.follower.epoch,time.monotonic(),generation)
        self.driver.send.assert_not_called()
        self.move('pan_tilt',{'pan':12,'tilt':0})
        self.assertTrue(self.camera['moving'])
    def test_repeated_speed_renews_watchdog_without_duplicate_http(self):
        self.move('pan_tilt',{'pan':12,'tilt':0});deadline=self.camera['motion_deadline']
        self.driver.send.reset_mock();time.sleep(.02)
        self.move('pan_tilt',{'pan':12,'tilt':0})
        self.driver.send.assert_not_called();self.assertGreater(self.camera['motion_deadline'],deadline)
        self.move('pan_tilt',{'pan':-12,'tilt':0});self.driver.send.assert_called_once_with('#PTS3850')
    def test_stop_waiting_for_busy_camera_does_not_expire(self):
        self.move('pan_tilt',{'pan':12,'tilt':0})
        errors=[]
        def stop():
            try:self.move('pan_tilt',{'pan':0,'tilt':0})
            except Exception as exc:errors.append(exc)
        with self.camera['io']:
            thread=threading.Thread(target=stop);thread.start();wait_for(lambda:bool(self.camera['io'].waiters));time.sleep(.35)
        thread.join(2);self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
        self.assertEqual(self.driver.motion_state['#PTS'],'#PTS5050')

class MotionStreamTests(unittest.TestCase):
    def test_sixty_hz_reversals_and_release_with_polling(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim=simulator(port=0);threading.Thread(target=sim.serve_forever,daemon=True).start()
            engine=Engine({'poll_seconds':.1,'cameras':[dict(id='p1',manufacturer='Panasonic',model='AW-HE130',driver='panasonic',host='127.0.0.1',port=sim.server_port,simulator=True)]},tmp)
            engine.start();wait_for(lambda:engine.cameras['p1']['params']['focus_auto']['confirmation']=='confirmed')
            follower=FixedCameraController(engine,'p1')
            service=PivotCamServer(('127.0.0.1',0),engine,'p1',follower,'127.0.0.1')
            threading.Thread(target=service.serve_forever,daemon=True).start()
            replies=bytearray();observed=[]
            try:
                with socket.create_connection(service.server_address,timeout=2) as client:
                    def receive():
                        try:
                            while True:
                                chunk=client.recv(1024)
                                if not chunk:break
                                replies.extend(chunk)
                        except OSError:pass
                    reader=threading.Thread(target=receive,daemon=True);reader.start()
                    # Carbonite emits speed changes much faster than Panasonic CGI.
                    for i in range(150):
                        direction=1 if (i//10)%2 else 2
                        client.sendall(bytes([0x81,1,6,1,1+i%24,1+i%20,direction,3,255]))
                        if i%4==0:client.sendall(bytes.fromhex('81 01 04 07 23 FF'))
                        observed.append(dict(sim.model.axes))
                        time.sleep(1/60)
                    start=time.monotonic();client.sendall(bytes.fromhex('81 01 06 01 01 01 03 03 FF 81 01 04 07 00 FF'))
                    wait_for(lambda:all(v==0 for v in sim.model.axes.values()),timeout=2)
                    elapsed=time.monotonic()-start
                    self.assertLess(elapsed,.65,'release should not wait for the 900 ms watchdog')
                    self.assertNotIn(bytes.fromhex('90 60'),replies,'fresh motion and neutral packets must not be rejected')
                    self.assertFalse(engine.cameras['p1']['moving'])
                    self.assertTrue(any(a['pan']>0 for a in observed))
                    self.assertTrue(any(a['pan']<0 for a in observed))
                    self.assertTrue(any(a['zoom']>0 for a in observed))
            finally:
                service.shutdown();service.server_close();engine.close();sim.shutdown();sim.server_close()
