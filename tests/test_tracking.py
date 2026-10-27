import copy
import socket
import tempfile
import threading
import time
import unittest
import pathlib
import subprocess
import sys
from backend.core import Engine
from backend.runtime import Runtime
from backend.server import validate_config
from backend.tracking import Tracking, settings, parse_pan_tilt, parse_lens, pose, encode_d1, interpolated_pose


def config(**tracking):
    return validate_config({'cameras':[dict(id='cam',number=1,name='Camera',manufacturer='Panasonic',
        model='AW-HE40',driver='panasonic',host='192.0.2.1',tracking_output=tracking)]})


class TrackingTests(unittest.TestCase):
    def test_interpolation_uses_separate_head_and_lens_clocks_without_prediction(self):
        cfg=settings({});cfg.update(interpolation_enabled=True,interpolation_delay=.75)
        first=dict(pan=32768,tilt=32768,zoom=1500,focus=2000)
        last=dict(pan=32868,tilt=32668,zoom=2500,focus=3000)
        history=[(first,10,10.2),(last,10.5,10.7)]
        value,state=interpolated_pose(history,cfg,11.1) # target 10.35
        self.assertEqual(state,'Interpolating')
        self.assertAlmostEqual(value['pan'],.5775)
        self.assertAlmostEqual(value['tilt'],.5775)
        self.assertEqual(value['zoom'],1800)
        self.assertEqual(value['focus'],2300)
        self.assertEqual(len(encode_d1(1,value)),29)
        value,state=interpolated_pose(history,cfg,12)
        self.assertEqual(state,'Holding Latest')
        self.assertEqual(value,pose(last,cfg))
        self.assertEqual(interpolated_pose(history[:1],cfg,11.1),(None,'Buffering'))
        self.assertEqual(interpolated_pose(history,cfg,10.8),(None,'Buffering'))

    def test_interpolation_handles_pan_angle_wrap_and_rejects_feedback_gaps(self):
        cfg=settings({});cfg.update(pan_zero=0,degrees_per_count=.01,interpolation_delay=.5)
        a=dict(pan=17900,tilt=32768,zoom=1500,focus=2000)
        b=dict(a,pan=18100)
        value,state=interpolated_pose([(a,10,10),(b,11,11)],cfg,11)
        self.assertEqual(state,'Interpolating');self.assertAlmostEqual(value['pan'],-180)
        self.assertEqual(interpolated_pose([(a,10,10),(b,12,12)],cfg,11.5),(None,'Buffering'))

    def test_interpolated_udp_stops_when_stale_and_configuration_changes(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            udp.bind(('127.0.0.1',0));udp.settimeout(.5)
            e=Engine(config(enabled=True,host='127.0.0.1',port=udp.getsockname()[1],
                            interpolation_enabled=True,interpolation_delay=.25,stale_seconds=.5),folder)
            manager=Tracking(e);c=e.cameras['cam'];cfg=settings(c['config']);now=time.monotonic()
            a=dict(pan=32768,tilt=32768,zoom=1500,focus=2000)
            b=dict(a,pan=32868)
            manager.samples['cam']=(cfg,b,now)
            manager.history['cam']=[(a,now-.4,now-.4),(b,now,now)]
            t=threading.Thread(target=manager.transmit,args=('cam',));t.start()
            try:
                packet=udp.recv(100)
                pan=int.from_bytes(packet[2:5],'big',signed=True)/32768
                self.assertGreater(pan,0);self.assertLess(pan,.825)
                with e.lock:c['config']['tracking_output']['interpolation_delay']=.3
                udp.setblocking(False)
                while True:
                    try:udp.recv(100)
                    except BlockingIOError:break
                udp.settimeout(.12)
                with self.assertRaises(socket.timeout):udp.recv(100)
                with e.lock:
                    c['config']['tracking_output']['interpolation_delay']=.25
                    manager.samples['cam']=(cfg,b,time.monotonic()-1)
                time.sleep(.05)
                with self.assertRaises(socket.timeout):udp.recv(100)
                self.assertEqual(c['tracking_status']['state'],'Stale')
                self.assertNotIn('cam',manager.history)
            finally:e.closed.set();t.join(2)

    @unittest.skipUnless(sys.platform=='win32' and pathlib.Path('C:/Program Files/XPressionStudio/net/xpression.net.dll').exists(),'Requires the locally installed Ross SDK')
    def test_xpression_adapter_compiles_and_decodes_independent_golden_packet(self):
        source=pathlib.Path(__file__).resolve().parents[1]/'deployment/xpression/CameraBridgeTracking.cs'
        script="""$ErrorActionPreference='Stop';
Add-Type -Path 'C:/Program Files/XPressionStudio/net/xpression.net.dll';
Add-Type -Path 'SOURCE' -ReferencedAssemblies 'C:/Program Files/XPressionStudio/net/xpression.net.dll';
$p=[byte[]](0xd1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0x6e);
$v=[CameraBridgeTracking]::Decode($p,1); if($v.Length -ne 8 -or $v[0] -ne 0){throw 'decode failed'};
$p[28]=0; if($null -ne [CameraBridgeTracking]::Decode($p,1)){throw 'checksum accepted'};
$points=New-Object 'System.Collections.Generic.List[double[]]';$points.Add([double[]](1000,60));$points.Add([double[]](3000,20));
if([CameraBridgeTracking]::LensFov($points,2000) -ne 40){throw 'interpolation failed'};
if($null -ne [CameraBridgeTracking]::LensFov($points,999)){throw 'extrapolation accepted'};
""".replace('SOURCE',str(source).replace("'","''"))
        result=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_official_d1_layout_signed_values_units_and_checksum(self):
        zero=dict(pan=0,tilt=0,roll=0,x=0,y=0,z=0,zoom=0,focus=0)
        self.assertEqual(encode_d1(1,zero),bytes.fromhex('d101'+'00'*26+'6e'))
        value=dict(pan=-90,tilt=45,roll=-1,x=-1000,y=2000,z=1500,zoom=0x777,focus=0xb5d)
        p=encode_d1(7,value)
        self.assertEqual(len(p),29);self.assertEqual(p[:2],b'\xd1\x07')
        self.assertEqual(p[2:5],bytes.fromhex('d30000'))
        self.assertEqual(p[5:8],bytes.fromhex('168000'))
        self.assertEqual(p[11:14],(-64000).to_bytes(3,'big',signed=True))
        self.assertEqual(p[20:26],bytes.fromhex('000777000b5d'))
        self.assertEqual(p[26:28],b'\0\0');self.assertEqual(sum(p)&255,0x40)
        for bad in (dict(value,tilt=91),dict(value,x=131072),dict(value,pan=float('nan'))):
            with self.assertRaises(ValueError):encode_d1(1,bad)

    def test_live_he40_reply_parsing_and_axis_calibration(self):
        self.assertEqual(parse_pan_tilt('aPC79F082A5'),(0x79f0,0x82a5))
        self.assertEqual(parse_lens('lPI777B5DF94'),(0x777,0xb5d,0xf94))
        for bad in ('aPC00000000extra','aPC8000','ER1','aPC1234zzzz'):
            with self.assertRaises(ValueError):parse_pan_tilt(bad)
        for bad in ('lPI000FFF555','lPI777B5DF94extra','lPIFFFFFFFF'):
            with self.assertRaises(ValueError):parse_lens(bad)
        cfg=settings({'number':4});cfg.update(pan_zero=0x79f0,tilt_zero=0x82a5)
        value=pose(dict(pan=0x79f0+100,tilt=0x82a5-100,zoom=0x777,focus=0xb5d),cfg)
        self.assertAlmostEqual(value['pan'],.825);self.assertAlmostEqual(value['tilt'],.825)
        self.assertEqual(cfg['camera_id'],4)

    def test_configuration_limits_and_no_guessed_pose_for_fixed_or_digital_cameras(self):
        config();config(enabled=True,host='127.0.0.1',camera_id=9)
        for fields in (dict(enabled=True),dict(rate=0),dict(sample_rate=10),dict(rate=True),dict(stale_seconds=float('nan')),
                       dict(enabled=True,host='0.0.0.0'),dict(enabled=True,host='239.1.2.3'),
                       dict(enabled=True,xpression_enabled=True,host='127.0.0.1',xpression_port=40000),
                       dict(interpolation_enabled=1),dict(interpolation_delay=0),dict(interpolation_delay=float('nan')),
                       dict(interpolation_enabled=True,interpolation_delay=1.5)):
            with self.assertRaises(ValueError):config(**fields)
        for model in ('AW-HE2','AG-CX350','Other'):
            c=config();c['cameras'][0].update(model=model,tracking_output=dict(enabled=True,host='127.0.0.1'))
            with self.assertRaises(ValueError):validate_config(c)
        c=config(enabled=True,host='127.0.0.1');other=copy.deepcopy(c['cameras'][0]);other.update(id='cam2',number=2)
        other['tracking_output']['camera_id']=1;c['cameras'].append(other)
        with self.assertRaises(ValueError):validate_config(c)

    def test_tracking_autosave_does_not_restart_pivotcam_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Runtime(config(),folder);engine=runtime.engine
            updated=config(enabled=True,host='127.0.0.1')
            self.assertTrue(runtime.update_metadata(updated));self.assertIs(runtime.engine,engine)

    def test_udp_stale_disable_and_invalid_measurements_stop_output(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            udp.bind(('127.0.0.1',0));udp.settimeout(.8)
            e=Engine(config(enabled=True,host='127.0.0.1',port=udp.getsockname()[1],stale_seconds=.5),folder)
            manager=Tracking(e);c=e.cameras['cam'];cfg=settings(c['config'])
            manager.samples['cam']=(cfg,dict(pan=32768,tilt=32768,zoom=0x555,focus=0xfff),time.monotonic())
            t=threading.Thread(target=manager.transmit,args=('cam',));t.start()
            try:
                self.assertEqual(len(udp.recv(100)),29)
                time.sleep(.65)
                udp.setblocking(False)
                while True:
                    try:udp.recv(100)
                    except BlockingIOError:break
                udp.settimeout(.12)
                with self.assertRaises(socket.timeout):udp.recv(100)
                self.assertEqual(c['tracking_status']['state'],'Stale')
                with e.lock:
                    c['config']['tracking_output']['enabled']=False
                    manager.samples['cam']=(cfg,dict(pan=0,tilt=0,zoom=0x555,focus=0xfff),time.monotonic())
                with self.assertRaises(socket.timeout):udp.recv(100)
            finally:e.closed.set();t.join(2)

    def test_source_reads_release_camera_access_between_queries_and_reject_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            e=Engine(config(enabled=True,host='127.0.0.1'),folder);c=e.cameras['cam'];manager=Tracking(e)
            calls=[]
            def send(command):
                calls.append(command)
                if len(calls)>2:raise ValueError('camera disconnected')
                return 'aPC80008000' if command=='#APC' else 'lPI777B5DF94'
            c['driver'].send=send
            t=threading.Thread(target=manager.sample,args=('cam',));t.start()
            try:
                deadline=time.monotonic()+1
                while 'cam' not in manager.samples and time.monotonic()<deadline:time.sleep(.01)
                self.assertIn('cam',manager.samples)
                deadline=time.monotonic()+1
                while c['tracking_status']['state']!='Read Error' and time.monotonic()<deadline:time.sleep(.01)
                self.assertNotIn('cam',manager.samples);self.assertEqual(calls[:2],['#APC','#LPI'])
            finally:e.closed.set();t.join(2)
