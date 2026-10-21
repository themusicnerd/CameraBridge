import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from backend.server import default_storage,ROOT
from camerabridge import export_panels

class ReleaseTests(unittest.TestCase):
    def test_source_storage_keeps_existing_runtime(self):
        with patch('backend.server.sys.frozen',False,create=True):self.assertEqual(default_storage(),ROOT/'runtime')

    def test_frozen_storage_is_writable_user_data(self):
        with patch('backend.server.sys.frozen',True,create=True):
            with patch('backend.server.sys.platform','win32'),patch.dict('os.environ',{'LOCALAPPDATA':'C:/Users/test/AppData/Local'}):
                self.assertEqual(default_storage(),pathlib.Path('C:/Users/test/AppData/Local/CameraBridge'))
            with patch('backend.server.sys.platform','darwin'):
                self.assertEqual(default_storage(),pathlib.Path.home()/'Library/Application Support/CameraBridge')
            with patch('backend.server.sys.platform','linux'),patch.dict('os.environ',{'XDG_DATA_HOME':'/tmp/data'}):
                self.assertEqual(default_storage(),pathlib.Path('/tmp/data/camerabridge'))

    def test_exported_panels_have_local_assets_and_no_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_panels(tmp)
            for maker in ('Panasonic','Marshall'):
                root=ET.parse(pathlib.Path(tmp)/f'CameraBridge-{maker}.grid').getroot()
                self.assertEqual(root.find('.//image').get('src'),(pathlib.Path(tmp)/'assets'/f'{maker.lower()}.png').as_uri())
                self.assertEqual(root.find('./meta/params/param[@oid="password"]').get('value'),'')
                self.assertIsNotNone(root.find('.//button[@id="open_bridge"]'))

if __name__=='__main__':unittest.main()
