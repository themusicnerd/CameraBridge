"""Visible interactive setup; passwords never appear in arguments, files or logs."""
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from backend.server import Auth,ROOT,provision_user

if __name__=='__main__':
    storage=ROOT/'runtime';storage.mkdir(parents=True,exist_ok=True)
    try:
        provision_user(Auth(storage/'credentials.sqlite'),'admin','admin')
    except KeyboardInterrupt:
        print('\nAccount setup cancelled.')
    except Exception as exc:
        print('Account setup failed: '+type(exc).__name__)
    input('Press Enter to close this setup window. ')
