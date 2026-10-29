import copy
import tempfile
import unittest
from backend.runtime import Runtime
from backend.server import validate_config


class CameraOrderTests(unittest.TestCase):
    def test_reorder_changes_snapshot_order_without_restarting_or_remapping(self):
        configuration=validate_config({'pivotcam':{'enabled':True,'bind':'127.0.0.1','base_port':19010,'controller':'127.0.0.1'},'cameras':[
            dict(id='first',number=1,name='First',manufacturer='Panasonic',model='AW-HE130',driver='panasonic',host='192.0.2.1',pivotcam=True,carbonite_input=4),
            dict(id='second',number=3,name='Second',manufacturer='Panasonic',model='AW-HE2',driver='panasonic',host='192.0.2.2',pivotcam=True,carbonite_input=6)]})
        with tempfile.TemporaryDirectory() as folder:
            runtime=Runtime(configuration,folder);engine=runtime.engine;camera=engine.cameras['first'];listeners=runtime.listeners
            camera.update(owner='operator',generation=12,moving=True)
            changed=copy.deepcopy(configuration);changed['cameras'].reverse()
            self.assertEqual(runtime.transport_settings(configuration),runtime.transport_settings(changed))
            self.assertTrue(runtime.update_metadata(changed));self.assertIs(runtime.engine,engine);self.assertIs(runtime.listeners,listeners)
            self.assertIs(engine.cameras['first'],camera)
            self.assertEqual((camera['owner'],camera['generation'],camera['moving']),('operator',12,True))
            snapshot=engine.snapshot()['cameras']
            self.assertEqual([c['id'] for c in snapshot],['second','first'])
            self.assertEqual([(c['number'],c['carbonite_input']) for c in snapshot],[(3,6),(1,4)])
            self.assertEqual([configuration['pivotcam']['base_port']+c['number'] for c in snapshot],[19013,19011])


if __name__=='__main__':unittest.main()
