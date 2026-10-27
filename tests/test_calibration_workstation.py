import copy
import json
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import Mock,patch
from backend.calibration_workstation import Bridge,start
from backend.calibration import validate
from .test_calibration_video import optical_fixture
from .test_calibration import configuration


class WorkstationTests(unittest.TestCase):
    def test_loopback_host_token_and_origin_checks(self):
        server=start()
        try:
            url='http://127.0.0.1:'+str(server.server_address[1])
            self.assertIn(b'USB Capture (Magewell)',urllib.request.urlopen(url).read())
            self.assertIn(b'<svg',urllib.request.urlopen(url+'/assets/camerabridge.svg').read())
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+'/api/state')
            request=urllib.request.Request(url+'/api/state',headers={'Authorization':'Bearer '+server.token})
            self.assertEqual(json.load(urllib.request.urlopen(request))['state'],'Stopped')
            request=urllib.request.Request(url+'/api/stop',data=b'{}',headers={'Authorization':'Bearer '+server.token,'Content-Type':'application/json','Origin':'https://unrelated.example'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,403)
            request=urllib.request.Request(url+'/api/stop',data=b'{}',headers={'Authorization':'Bearer '+server.token,'Content-Type':'application/json','Host':'unrelated.example'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,403)
        finally:server.close()

    def test_workstation_save_preserves_camera_head_network_and_other_roster_values(self):
        bridge=Bridge();bridge.token='test';original=configuration()
        original['cameras'][0]['tracking_output']=dict(host='192.0.2.8',port=40000,pan_zero=32000)
        saved=[]
        def api(path,data=None):
            if path=='config':return original
            if data['operation']=='load':return dict(configuration=copy.deepcopy(original),revision='r1')
            saved.append(data);return dict(status='Saved')
        bridge.api=Mock(side_effect=api)
        bridge.save('cam',optical_fixture(),dict(camera_model='AW-HE40',camera_host='192.0.2.1',camera_port=80))
        result=saved[0]['configuration']['cameras'][0]
        self.assertEqual(result['tracking_output'],original['cameras'][0]['tracking_output'])
        self.assertNotIn('tracking_calibration',original['cameras'][0])
        self.assertEqual(result['number'],1);validate(result['tracking_calibration'])
        self.assertEqual(result['tracking_calibration']['optical_solutions'][0]['distortion'],optical_fixture()['distortion'])

    def test_workstation_will_not_apply_unrelated_pending_setup(self):
        bridge=Bridge();bridge.token='test';active=configuration();pending=copy.deepcopy(active);pending['cameras'][0]['number']=4
        bridge.api=Mock(side_effect=[dict(configuration=pending,revision='r1'),active])
        with self.assertRaisesRegex(ValueError,'pending setup'):bridge.save('cam',optical_fixture(),dict(camera_model='AW-HE40',camera_host='192.0.2.1',camera_port=80))
        self.assertEqual(bridge.api.call_count,2)

    def test_optical_profile_validation_and_invariant_checks(self):
        solution=optical_fixture();profile=dict(version=1,name='Lens',model='AW-HE40',video_width=1280,video_height=720,lens_points=[],optical_solutions=[solution])
        validate(profile)
        for modify in (lambda p:p['optical_solutions'][0].update(hfov=10),lambda p:p.update(video_width=1920),
                       lambda p:p['optical_solutions'][0].update(timing_calibrated=True),
                       lambda p:p['optical_solutions'][0]['camera_matrix'][0].__setitem__(0,float('nan')),
                       lambda p:p['optical_solutions'].append(copy.deepcopy(p['optical_solutions'][0]))):
            candidate=copy.deepcopy(profile);modify(candidate)
            with self.assertRaises(ValueError):validate(candidate)
