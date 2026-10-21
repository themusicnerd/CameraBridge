import io,json,pathlib,socket,tempfile,threading,time,unittest
from unittest.mock import patch
from tools.ross_dev_relay import verify_lab
from tools.ross_dev_relay import Capture,Relay

class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'capture.jsonl';self.capture=Capture(self.path)
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen();self.listener.settimeout(2)
        self.calls=[];self.relay=Relay(('127.0.0.1',0),'127.0.0.1',self.listener.getsockname()[1],self.capture,validator=self.calls.append)
        self.thread=threading.Thread(target=self.relay.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.relay.shutdown();self.relay.server_close();self.thread.join();self.listener.close();time.sleep(.1);self.capture.close();self.tmp.cleanup()
    def test_duplex_fragments_and_disconnect(self):
        client=socket.create_connection(self.relay.server_address,timeout=2)
        upstream,_=self.listener.accept();upstream.settimeout(2)
        with upstream,client:
            for packet in (b'\x81\x09',b'\x04\x38\xff'):
                client.sendall(packet);self.assertEqual(upstream.recv(len(packet)),packet)
            upstream.sendall(bytes.fromhex('90 50 02 FF'));self.assertEqual(client.recv(4),bytes.fromhex('90 50 02 FF'))
            client.shutdown(socket.SHUT_RDWR);self.assertEqual(upstream.recv(1),b'')
        self.assertEqual(len(self.calls),1)
        events=[json.loads(x) for x in self.path.read_text().splitlines()]
        self.assertTrue(any(e['direction']=='frame-to-lab' for e in events));self.assertTrue(any(e['direction']=='lab-to-frame' for e in events))
    def test_ascii_driver_traffic_is_captured_without_forwarding(self):
        with socket.create_connection(self.relay.server_address,timeout=2) as client:
            upstream,_=self.listener.accept();upstream.settimeout(.2)
            with upstream:
                client.sendall(bytes.fromhex('02 30 30 30 20 4E 43 03'))
                self.assertEqual(upstream.recv(16),b'')
        events=[json.loads(x) for x in self.path.read_text().splitlines()]
        self.assertTrue(any(e['direction']=='unsupported-framing-disconnect' for e in events))
    def test_broadcast_address_initialization_is_forwarded(self):
        with socket.create_connection(self.relay.server_address,timeout=2) as client:
            upstream,_=self.listener.accept();upstream.settimeout(2)
            with upstream:
                client.sendall(bytes.fromhex('88 30 01 FF'))
                self.assertEqual(upstream.recv(4),bytes.fromhex('88 30 01 FF'))
                upstream.sendall(bytes.fromhex('88 30 02 FF'))
                self.assertEqual(client.recv(4),bytes.fromhex('88 30 02 FF'))
    def test_wrong_peer_denied_before_upstream(self):
        self.relay.frame='192.168.96.123'
        with socket.create_connection(self.relay.server_address,timeout=2) as c:self.assertEqual(c.recv(1),b'')
        self.assertEqual(self.calls,[])
    def test_shutdown_closes_active_controller_and_upstream(self):
        with socket.create_connection(self.relay.server_address,timeout=2) as client:
            upstream,_=self.listener.accept();upstream.settimeout(2)
            with upstream:
                client.sendall(b'\x81\xff');self.assertEqual(upstream.recv(2),b'\x81\xff')
                self.relay.shutdown();self.relay.server_close()
                self.assertEqual(upstream.recv(1),b'');self.assertEqual(client.recv(1),b'')
                self.assertFalse(self.relay.clients)
    def test_lab_guard_rejects_hardware_and_nonloopback_target(self):
        def response(value):return io.BytesIO(json.dumps(value).encode())
        camera=dict(id='pana1',simulator=True,manufacturer='Panasonic',host='127.0.0.1')
        with patch('tools.ross_dev_relay.urllib.request.urlopen',side_effect=[response({'mode':'LAB'}),response({'cameras':[camera]})]):verify_lab(19011)
        with patch('tools.ross_dev_relay.urllib.request.urlopen',return_value=response({'mode':'hardware'})):
            with self.assertRaises(ValueError):verify_lab(19011)
        for changes in ({'simulator':False},{'host':'192.168.96.50'}):
            with patch('tools.ross_dev_relay.urllib.request.urlopen',side_effect=[response({'mode':'LAB'}),response({'cameras':[dict(camera,**changes)]})]):
                with self.assertRaises(ValueError):verify_lab(19011)
    def test_capture_limit_fails_closed(self):
        self.capture.limit=1
        with self.assertRaises(OSError):self.capture.record('127.0.0.1','frame-to-lab',b'\x81\xff')

if __name__=='__main__':unittest.main()
