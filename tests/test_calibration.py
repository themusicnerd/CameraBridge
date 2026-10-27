import copy
import tempfile
import unittest
from unittest.mock import Mock
from backend.calibration import capture, horizontal_fov, validate
from backend.core import Engine
from backend.runtime import Runtime
from backend.server import validate_config


def configuration():
    return validate_config(dict(cameras=[dict(id='cam',number=1,name='Camera',model='AW-HE40',manufacturer='Panasonic',driver='panasonic',host='192.0.2.1')]))


def profile():
    return dict(version=1,name='Test Lens',model='AW-HE40',video_width=1920,video_height=1080,lens_points=[
        dict(zoom=1365,focus=2800,hfov=90,target_width_mm=2000,distance_mm=1000,target_pixels=1920,captured_at=1)])


class CalibrationTests(unittest.TestCase):
    def test_target_geometry_full_frame_and_partial_image(self):
        self.assertAlmostEqual(horizontal_fov(1920,2000,1000,1920),90)
        self.assertAlmostEqual(horizontal_fov(1920,1000,1000,960),90)
        for args in [(1920,0,1000,960),(1920,1000,0,960),(1920,1000,1000,1921),(True,1000,1000,960),(1920,float('nan'),1000,960)]:
            with self.assertRaises(ValueError):horizontal_fov(*args)

    def test_profile_rejects_forged_fov_duplicate_encoder_and_bad_schema(self):
        validate(profile())
        for modify in (lambda p:p.update(version=True),lambda p:p.update(video_width=0),
                       lambda p:p['lens_points'].append(copy.deepcopy(p['lens_points'][0])),
                       lambda p:p['lens_points'][0].update(hfov=50),lambda p:p.update(unknown=1)):
            p=profile();modify(p)
            with self.assertRaises(ValueError):validate(p)

    def test_capture_reads_twice_without_motion_or_store_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=Engine(configuration(),folder);camera=engine.cameras['cam']
            camera['driver'].send=Mock(side_effect=['aPC79F082A5','lPI777B5DF94']*2)
            result=capture(engine,'cam')
            self.assertEqual((result['pan'],result['tilt'],result['zoom'],result['focus']),(0x79f0,0x82a5,0x777,0xb5d))
            self.assertEqual([call.args[0] for call in camera['driver'].send.call_args_list],['#APC','#LPI','#APC','#LPI'])
            self.assertIsNone(camera['io'].owner)
            self.assertEqual(result['host'],'192.0.2.1')

    def test_capture_rejects_motion_focus_drift_unsupported_sources_and_shutdown(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=Engine(configuration(),folder);camera=engine.cameras['cam']
            camera['driver'].send=Mock(side_effect=['aPC80008000','lPI777B5DF94','aPC80018000','lPI777B5DF94'])
            with self.assertRaisesRegex(ValueError,'moved during capture'):capture(engine,'cam')
            camera['driver'].send=Mock(side_effect=['aPC80008000','lPI777B5DF94','aPC80008000','lPI777B5EF94'])
            with self.assertRaisesRegex(ValueError,'moved during capture'):capture(engine,'cam')
            camera['moving']=True;camera['driver'].send=Mock()
            with self.assertRaisesRegex(ValueError,'Stop the camera'):capture(engine,'cam')
            camera['driver'].send.assert_not_called();camera['moving']=False
            engine.closed.set()
            with self.assertRaisesRegex(ValueError,'setup is changing'):capture(engine,'cam')
            camera['config']['model']='AW-HE2'
            with self.assertRaisesRegex(ValueError,'supported mechanical'):capture(engine,'cam')

    def test_saved_profile_does_not_restart_runtime_or_change_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            config=configuration();runtime=Runtime(config,folder);engine=runtime.engine
            updated=copy.deepcopy(config);updated['cameras'][0]['tracking_calibration']=profile()
            validate_config(updated);self.assertTrue(runtime.update_metadata(updated));self.assertIs(runtime.engine,engine)
            self.assertEqual(engine.cameras['cam']['config']['tracking_calibration']['lens_points'][0]['hfov'],90)
