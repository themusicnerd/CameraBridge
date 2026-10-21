import http.client
import threading
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch,MagicMock
from tools.td_panel_host import PanelHost,panel_bytes

class TouchDrivePanelHostTests(unittest.TestCase):
    def setUp(self):
        self.host=PanelHost(('127.0.0.1',0),'192.168.96.122')
        self.thread=threading.Thread(target=self.host.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.host.shutdown();self.host.server_close();self.thread.join()
    def request(self,path,body=None,headers=None):
        c=http.client.HTTPConnection(*self.host.server_address,timeout=2)
        c.request('POST' if body is not None else 'GET',path,body,headers or {})
        r=c.getresponse();result=r.status,r.read(),dict(r.getheaders());c.close();return result
    def test_cross_platform_panels(self):
        for maker in ('Panasonic','Marshall','Sony'):
            root=ET.fromstring(panel_bytes(maker,'http://192.168.96.61:8089'))
            bridge=next(p for p in root.iter('param') if p.get('oid')=='bridge' and 'value' in p.attrib)
            self.assertEqual(bridge.get('value'),'http://192.168.96.61:8089')
            self.assertEqual(next(root.iter('image')).get('src'),'http://192.168.96.61:8089/assets/'+maker.lower()+'.png')
            self.assertNotIn(b'file://',ET.tostring(root))
        status,body,headers=self.request('/Panasonic.grid')
        self.assertEqual(status,200);ET.fromstring(body)
        self.assertIn('attachment',headers['Content-Disposition'])
    def test_denied_host_and_private_files(self):
        self.host.allowed={'192.168.96.122'}
        self.assertEqual(self.request('/Panasonic.grid')[0],403)
        self.host.allowed={'127.0.0.1'}
        for path in ('/runtime/credentials.sqlite','/../config.example.json','/assets/../runtime/credentials.sqlite'):
            self.assertEqual(self.request(path)[0],404)
        for path in ('/api/service/stop','/api/command?x=1'):
            self.assertEqual(self.request(path,b'{}')[0],403)
    def test_proxy_preserves_auth_and_payload(self):
        upstream=MagicMock();response=upstream.getresponse.return_value;response.status=403;response.read.return_value=b'{"error":"Authentication required"}'
        original=http.client.HTTPConnection
        def connection(host,port,**kw):
            return upstream if (host,port)==('127.0.0.1',8088) else original(host,port,**kw)
        with patch('tools.td_panel_host.http.client.HTTPConnection',side_effect=connection):
            result=self.request('/api/command',b'{"action":"stop"}',{'Authorization':'Bearer test-session'})
        self.assertEqual(result[0],403)
        args=upstream.request.call_args.args
        self.assertEqual(args[:3],('POST','/api/command',b'{"action":"stop"}'))
        self.assertEqual(args[3]['Authorization'],'Bearer test-session')
    def test_origin_and_body_limits(self):
        self.assertEqual(self.request('/api/login',b'{}',{'Origin':'http://untrusted.example'})[0],403)
        # Reject from the declared size before the body is sent. Sending an unread
        # oversized body can make Windows reset the socket before HTTP is read.
        self.assertEqual(self.request('/api/login',b'',{'Content-Length':'65537'})[0],400)

    def test_admin_page_and_authenticated_get_forwarding(self):
        status,body,headers=self.request('/')
        self.assertEqual(status,200);self.assertIn(b'<html',body)
        upstream=MagicMock();response=upstream.getresponse.return_value;response.status=401;response.read.return_value=b'{"error":"Authentication required"}'
        original=http.client.HTTPConnection
        def connection(host,port,**kw):return upstream if (host,port)==('127.0.0.1',8088) else original(host,port,**kw)
        with patch('tools.td_panel_host.http.client.HTTPConnection',side_effect=connection):
            self.assertEqual(self.request('/api/config',headers={'Authorization':'Bearer test-session'})[0],401)
        self.assertEqual(upstream.request.call_args.args[0:2],('GET','/api/config'))
        self.assertEqual(upstream.request.call_args.args[3]['Authorization'],'Bearer test-session')

if __name__=='__main__':unittest.main()
