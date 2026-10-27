import io
import math
import struct
import threading
import time
import unittest
from unittest.mock import patch
from backend.calibration_video import VideoSession,cv_modules,input_args,read_png,PNG,MAX_FRAME,ffmpeg_path
from backend.calibration import validate_optical

try:
    cv,np=cv_modules();HAS_CV=True
except RuntimeError:HAS_CV=False


def optical_fixture():
    return dict(model='opencv-pinhole-5',width=1280,height=720,camera_matrix=[[950.,0,640],[0,945.,360],[0,0,1]],
        distortion=[-.08,.02,.001,-.001,.005],rms_pixels=.1,view_errors=[.1]*12,views=12,
        board_columns=9,board_rows=6,square_mm=25,hfov=math.degrees(2*math.atan(1280/1900)),captured_at=1,
        normalized_intrinsics=dict(fx=950/1280,fy=945/720,cx=.5,cy=.5),nodal_offset_calibrated=False,
        timing_calibrated=False,warnings=[],zoom=1911,focus=2873)


@unittest.skipUnless(HAS_CV,'Install requirements-video.txt')
class VideoCalibrationTests(unittest.TestCase):
    def test_flat_board_translations_do_not_count_as_a_constrained_calibration(self):
        v=VideoSession();v.board=(9,6,25);v.size=(1280,720)
        target=np.zeros((54,3),np.float32);target[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*25
        for i in range(12):
            points,_=cv.projectPoints(target,np.zeros(3),np.array([-130.+i*8,-70.+i*3,700.]),np.array(optical_fixture()['camera_matrix']),np.zeros(5))
            v.samples.append(dict(corners=points,coverage=.1))
        with self.assertRaisesRegex(ValueError,'tilted board angles'):v.solve()

    def test_png_pipe_preserves_frame_boundaries_and_rejects_oversized_chunks(self):
        image=np.zeros((48,64,3),np.uint8);image[:,:,1]=177
        ok,data=cv.imencode('.png',image);self.assertTrue(ok)
        pipe=io.BytesIO(data.tobytes()*2)
        for _ in range(2):self.assertTrue(np.array_equal(cv.imdecode(np.frombuffer(read_png(pipe),np.uint8),cv.IMREAD_COLOR),image))
        with self.assertRaises(ValueError):read_png(io.BytesIO(PNG+struct.pack('>I',MAX_FRAME+1)+b'IDAT'))
        with self.assertRaises(EOFError):read_png(io.BytesIO(data.tobytes()[:-5]))

    def test_input_selection_never_treats_urls_or_device_names_as_shell_code(self):
        args=input_args(dict(type='rtsp',source='rtsp://user:secret@192.0.2.1/stream'))
        self.assertEqual(args[-2:],['-i','rtsp://user:secret@192.0.2.1/stream'])
        for source in ('file:///etc/passwd','https://example.com/','rtsp://',''):
            with self.assertRaises(ValueError):input_args(dict(type='rtsp',source=source))
        with patch('backend.calibration_video.sys.platform','win32'):
            self.assertEqual(input_args(dict(type='usb',source='Magewell USB Capture HDMI'))[-1],'video=Magewell USB Capture HDMI')
        with patch('backend.calibration_video.sys.platform','linux'):
            self.assertEqual(input_args(dict(type='usb',source='/dev/video2')),['-f','v4l2','-i','/dev/video2'])
            with self.assertRaises(ValueError):input_args(dict(type='usb',source='/tmp/not-a-video-device'))

    def test_checkerboard_detection_duplicate_rejection_and_stale_video(self):
        image=np.full((600,800,3),255,np.uint8)
        for y in range(7):
            for x in range(10):
                if (x+y)%2==0:image[120+y*45:120+(y+1)*45,150+x*45:150+(x+1)*45]=0
        v=VideoSession();v.frame=image;v.frame_at=time.monotonic();v.state='Receiving'
        result=v.capture(dict(columns=9,rows=6,square_mm=25))
        self.assertEqual(result['samples'],1);self.assertGreater(result['coverage'],.1)
        v.frame_at=time.monotonic()
        with self.assertRaisesRegex(ValueError,'too similar'):v.capture(dict(columns=9,rows=6,square_mm=25))
        v.frame_at=time.monotonic()
        with self.assertRaisesRegex(ValueError,'settings changed'):v.capture(dict(columns=8,rows=6,square_mm=25))
        v.frame_at=time.monotonic()-3
        self.assertEqual(v.snapshot()['state'],'Stale')
        with self.assertRaisesRegex(ValueError,'fresh video'):v.capture(dict(columns=9,rows=6,square_mm=25))

    def test_solver_recovers_known_intrinsics_from_varied_noisy_board_views(self):
        v=VideoSession();v.board=(9,6,25);v.size=(1280,720)
        target=np.zeros((54,3),np.float32);target[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*25
        matrix=np.array([[950.,0,640],[0,945,360],[0,0,1]])
        distortion=np.array([-.08,.02,.001,-.001,.005])
        rng=np.random.default_rng(412)
        for i in range(18):
            rotation=np.array([-.4+.16*(i%5),-.35+.13*(i%6),-.15+.05*(i%7)])
            translation=np.array([-160.+45*(i%4),-105.+32*(i%3),650.+55*(i%5)])
            points,_=cv.projectPoints(target,rotation,translation,matrix,distortion)
            points=(points+rng.normal(0,.025,points.shape)).astype(np.float32)
            v.samples.append(dict(corners=points,coverage=.15))
        result=v.solve()
        self.assertLess(result['rms_pixels'],.1)
        self.assertAlmostEqual(result['camera_matrix'][0][0],950,delta=8)
        self.assertAlmostEqual(result['camera_matrix'][1][1],945,delta=8)
        self.assertAlmostEqual(result['camera_matrix'][0][2],640,delta=5)
        self.assertFalse(result['nodal_offset_calibrated']);self.assertFalse(result['timing_calibrated'])
        validate_optical(dict(result,zoom=1911,focus=2873))
        malformed=dict(result,zoom=1911,focus=2873,nodal_offset_calibrated=True)
        with self.assertRaises(ValueError):validate_optical(malformed)
        v.reset()
        with self.assertRaisesRegex(ValueError,'12 varied'):v.solve()

    def test_real_ffmpeg_png_pipeline_and_stop(self):
        try:path=ffmpeg_path()
        except RuntimeError:self.skipTest('FFmpeg not installed')
        v=VideoSession();v.thread=threading.Thread(target=v.run,args=('test',None,[path,'-hide_banner','-loglevel','error','-re','-f','lavfi','-i','testsrc=size=640x360:rate=10'],None),daemon=True)
        v.thread.start()
        try:
            deadline=time.monotonic()+8
            while v.frame is None and time.monotonic()<deadline:time.sleep(.05)
            self.assertIsNotNone(v.frame,v.snapshot());self.assertEqual(v.current().shape,(360,640,3))
            self.assertGreater(len(v.preview()),1000)
        finally:v.stop()
        self.assertEqual(v.state,'Stopped');self.assertIsNone(v.process)
