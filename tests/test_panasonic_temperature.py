import unittest
from backend.protocol import PANASONIC, panasonic_parameters
from backend.drivers import Panasonic
from backend.simulator import PanasonicModel
from backend.server import validate_config


class TemperatureTests(unittest.TestCase):
    def test_he130_documented_wire_table_and_nearest_kelvin(self):
        parameter=PANASONIC['colour_temperature']
        self.assertEqual(len(parameter.wire_values),121)
        self.assertEqual(parameter.encode(5600),'OSD:B1:05C')
        self.assertEqual(parameter.decode('OSD:B1:06E'),9200)
        self.assertEqual(parameter.snap(4500),4520)
        for kelvin in parameter.wire_values:
            self.assertEqual(parameter.decode(parameter.encode(kelvin)),kelvin)
        for value in (1999,15001,True,'5600'):
            with self.assertRaises(ValueError):parameter.encode(value)
        with self.assertRaises(ValueError):parameter.decode('OSD:B1:079')

    def test_he40_has_a_different_kelvin_table(self):
        parameter=panasonic_parameters('AW-HE40')['colour_temperature']
        self.assertEqual((parameter.low,parameter.high),(2400,9900))
        self.assertEqual(parameter.encode(5600),'OSD:B1:020')
        self.assertEqual(parameter.decode('OSD:B1:04B'),9900)
        self.assertFalse(Panasonic('127.0.0.1',model='AW-HE2').metadata('colour_temperature')['supported'])
        self.assertNotIn(9,panasonic_parameters('AW-HE2')['wb_mode'].allowed)

    def test_driver_uses_real_readback_and_simulator_uses_wire_indices(self):
        model=PanasonicModel();driver=Panasonic('127.0.0.1')
        driver.send=model.command
        self.assertEqual(driver.write('colour_temperature',5600),5600)
        self.assertEqual(model.history[-2:],['OSD:B1:05C','QSD:B1'])
        self.assertEqual(model.values['colour_temperature'],5600)

    def test_duplicate_real_camera_endpoint_is_rejected(self):
        configuration={'cameras':[
            dict(id='p1',number=1,manufacturer='Panasonic',model='AW-HE130',driver='panasonic',host='127.0.0.1',port=80),
            dict(id='p2',number=2,manufacturer='Panasonic',model='AW-HE2',driver='panasonic',host='127.0.0.1',port=80)]}
        with self.assertRaisesRegex(ValueError,'already used by camera 1'):validate_config(configuration)
        configuration['cameras'][1]['port']=81
        validate_config(configuration)


if __name__=='__main__':unittest.main()
