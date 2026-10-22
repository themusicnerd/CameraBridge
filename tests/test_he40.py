import unittest
from unittest.mock import Mock
from backend.drivers import Panasonic,PanasonicRejected
from backend.protocol import panasonic_parameters

class HE40Tests(unittest.TestCase):
    def test_he2_digital_ptz_has_no_focus_and_only_nine_shots(self):
        camera=Panasonic('192.0.2.1',model='AW-HE2');camera.send=Mock(return_value='ack')
        camera.move(pan=5,zoom=5)
        self.assertEqual([c.args[0] for c in camera.send.call_args_list],['#PTS5550','#Z55'])
        camera.send.reset_mock();camera.stop()
        self.assertEqual([c.args[0] for c in camera.send.call_args_list],['#PTS5050','#Z50'])
        with self.assertRaises(NotImplementedError):camera.move(focus=1)
        with self.assertRaises(ValueError):camera.preset(10)
        self.assertIsNone(camera.query('focus'))
        camera.send=Mock(return_value='giABC0')
        self.assertEqual(camera.query('iris'),0xABC)
        camera.send=Mock(side_effect=['OAW:1','OAW:1'])
        self.assertEqual(camera.write('wb_mode',1),1)

    def test_catalog_and_fixed_cameras(self):
        from backend.panasonic_models import MODELS
        from backend.server import validate_config
        for model in MODELS:
            validate_config({'cameras':[{'id':'test','number':1,'manufacturer':'Panasonic','model':model,'driver':'panasonic','host':'192.0.2.1'}]})
            camera=Panasonic('192.0.2.1',model=model)
            self.assertEqual(set(camera.parameters),set(panasonic_parameters(model)))
        camera=Panasonic('192.0.2.1',model='AK-UB300');camera.send=Mock()
        camera.stop();camera.send.assert_not_called()
        with self.assertRaises(NotImplementedError):camera.move(pan=1)

    def test_focus_neutral_rejection_requires_confirmed_autofocus(self):
        camera=Panasonic('192.0.2.1',model='AW-HE40')
        camera.send=Mock(side_effect=[PanasonicRejected('eR3:F50'),'d11'])
        camera.send_motion('#F50')
        camera.send=Mock(side_effect=[PanasonicRejected('eR3:F50'),'d10'])
        with self.assertRaises(PanasonicRejected):camera.send_motion('#F50')
        camera.send=Mock(side_effect=PanasonicRejected('eR3:F51'))
        with self.assertRaises(PanasonicRejected):camera.send_motion('#F51')
    def test_white_balance_memory_normalization(self):
        for model,replies in [('AW-HE40',('OAW:2','OAW:3')),('AW-HE130',('OAW:2','OAW:3'))]:
            camera=Panasonic('192.0.2.1',model=model)
            for public,reply in zip((2,3),replies):
                camera.send=Mock(side_effect=['ack',reply])
                self.assertEqual(camera.write('wb_mode',public),public)
                self.assertEqual(camera.send.call_args_list[0].args,('OAW:'+str(public-1),))

    def test_detail_range_and_model_rejection(self):
        self.assertEqual(panasonic_parameters('AW-HE40')['detail'].decode('ODT:2'),2)
        with self.assertRaises(ValueError):panasonic_parameters('AW-HE130')['detail'].validate(2)
        with self.assertRaises(ValueError):panasonic_parameters('unknown')

    def test_mode_restriction_is_retested_and_does_not_hide_transport_errors(self):
        camera=Panasonic('192.0.2.1',model='AW-HE40')
        camera.send=Mock(side_effect=[PanasonicRejected('ER3:QRI'),'ORI:096'])
        self.assertIsNone(camera.query('red_gain'))
        self.assertEqual(camera.query('red_gain'),150)
        for error in (PanasonicRejected('ER2:QRI'),TimeoutError('offline'),ValueError('malformed')):
            camera.send=Mock(side_effect=error)
            with self.assertRaises(type(error)):camera.query('red_gain')
        camera.send=Mock(side_effect=PanasonicRejected('ER3:ORI'))
        with self.assertRaises(PanasonicRejected):camera.write('red_gain',150)
