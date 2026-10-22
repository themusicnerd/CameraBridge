import json,pathlib,tempfile,unittest
from unittest.mock import Mock
from backend.drivers import Panasonic,PanasonicRejected
from backend.core import Engine

class CameraControlsTests(unittest.TestCase):
    def test_direction_changes_only_send_changed_axes_and_release_stops_active_axes(self):
        c=Panasonic('192.0.2.1',model='AW-HE40');c.send=Mock(side_effect=lambda cmd: 'pTS'+cmd[4:] if cmd.startswith('#PTS') else cmd[1].lower()+'S'+cmd[2:])
        c.move(pan=-12);self.assertEqual(c.send.call_count,3)
        c.send.reset_mock();c.move(pan=12)
        self.assertEqual([x.args[0] for x in c.send.call_args_list],['#PTS6250'])
        c.send.reset_mock();c.move(pan=12);c.send.assert_not_called()
        c.stop(active_only=True);self.assertEqual([x.args[0] for x in c.send.call_args_list],['#PTS5050'])
        c.send.reset_mock();c.stop();self.assertEqual(c.send.call_count,3)

    def test_gain_wire_and_public_normalization(self):
        c=Panasonic('192.0.2.1',model='AW-HE40');c.send=Mock(return_value='ORG:1E')
        self.assertEqual(c.query('red_gain'),150);c.send.assert_called_with('QGR')
        c.send=Mock(side_effect=['ORG:1F','ORG:1F']);self.assertEqual(c.write('red_gain',155),155)
        self.assertEqual(c.send.call_args_list[0].args,('ORG:1F',))
        with self.assertRaises(ValueError):c.write('red_gain',151)

    def test_speed_is_read_back_before_recall_and_failed_speed_does_not_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg={'cameras':[{'id':'p1','manufacturer':'Panasonic','model':'AW-HE40','driver':'panasonic','host':'192.0.2.1'}]}
            e=Engine(cfg,pathlib.Path(tmp));c=e.cameras['p1']['driver'];c.stop=Mock();c.send=Mock(side_effect=['uPVS625','uPVS625','s00'])
            e.command('p1','label_preset',{'number':1,'name':'Wide','speed':15},'user')
            self.assertEqual(Engine(cfg,pathlib.Path(tmp)).preset_speeds['p1']['1'],15)
            e.command('p1','preset',{'number':1},'user')
            self.assertEqual([x.args[0] for x in c.send.call_args_list],['#UPVS625','#UPVS','#R00'])
            c.send=Mock(side_effect=['uPVS750','uPVS750','s00']);e.command('p1','preset',{'number':1,'speed':20},'user')
            self.assertEqual(e.preset_speeds['p1']['1'],15,'recall override must not replace saved speed')
            c.send=Mock(side_effect=['uPVS625','uPVS999'])
            with self.assertRaises(ValueError):e.command('p1','preset',{'number':1},'user')
            self.assertNotIn('#R00',[x.args[0] for x in c.send.call_args_list])
            c.preset=Mock(side_effect=TimeoutError())
            with self.assertRaises(TimeoutError):e.command('p1','preset',{'number':2,'store':True,'confirm':'OVERWRITE','speed':12},'user')
            self.assertNotIn('2',e.preset_speeds['p1'])
            with self.assertRaises(ValueError):e.command('p1','preset',{'number':1,'speed':True},'user')

    def test_one_shot_uses_no_response_mode_and_never_claims_completion(self):
        c=Panasonic('192.0.2.1',model='AW-HE40');c.query=Mock(return_value=2);c.send=Mock(return_value='')
        result=c.white_balance_once();c.send.assert_called_once_with('OWS',response=False)
        self.assertEqual(result['status'],'sent');self.assertEqual(result['completion'],'unavailable')
        c.query.return_value=0
        with self.assertRaises(ValueError):c.white_balance_once()

    def test_preset_wire_speed_endpoints(self):
        c=Panasonic('192.0.2.1',model='AW-HE40')
        for speed,wire in ((1,275),(15,625),(30,999)):
            c.send=Mock(side_effect=['uPVS'+str(wire),'uPVS'+str(wire)])
            self.assertEqual(c.recall_speed(speed),speed)
            self.assertEqual(c.send.call_args_list[0].args,('#UPVS'+str(wire),))

    def test_ambiguous_motion_failure_is_stopped_even_if_previous_state_was_neutral(self):
        c=Panasonic('192.0.2.1',model='AW-HE40');c.send=Mock(side_effect=lambda cmd: 'pTS'+cmd[4:] if cmd.startswith('#PTS') else cmd[1].lower()+'S'+cmd[2:]);c.stop()
        c.send=Mock(side_effect=TimeoutError('ack lost'))
        with self.assertRaises(TimeoutError):c.move(pan=12)
        c.send=Mock(side_effect=lambda cmd: 'pTS'+cmd[4:] if cmd.startswith('#PTS') else cmd[1].lower()+'S'+cmd[2:]);c.stop(active_only=True)
        self.assertEqual([x.args[0] for x in c.send.call_args_list],['#PTS5050'])

    def test_malformed_motion_ack_does_not_mark_axis_known(self):
        c=Panasonic('192.0.2.1',model='AW-HE40');c.send=Mock(return_value='unexpected')
        with self.assertRaises(ValueError):c.move(pan=12)
        self.assertNotIn('#PTS',c.motion_state)
