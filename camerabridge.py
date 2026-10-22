"""Entry point for source use and platform release packages."""
import argparse
import json
import pathlib
import shutil
import sys
import tomllib
import xml.etree.ElementTree as ET
from backend.server import ROOT

def export_panels(output):
    destination=pathlib.Path(output).resolve();destination.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'dashboard/assets',destination/'assets',dirs_exist_ok=True)
    for manufacturer in ('Panasonic','Marshall','Sony'):
        tree=ET.parse(ROOT/'dashboard'/f'SW-{manufacturer}-Camera-Control.grid')
        for image in tree.iter('image'):
            image.set('src',(destination/'assets'/f'{manufacturer.lower()}.png').as_uri())
        target=destination/f'CameraBridge-{manufacturer}.grid';tree.write(target,encoding='utf-8',xml_declaration=True)
        print(target)
    tree=ET.parse(ROOT/'dashboard/CameraBridge.grid')
    for image in tree.iter('image'):
        image.set('src',(destination/'assets'/image.get('src').rsplit('/',1)[-1]).as_uri())
    target=destination/'CameraBridge.grid';tree.write(target,encoding='utf-8',xml_declaration=True)
    print(target)

def main():
    args=sys.argv[1:]
    if (not args and not pathlib.Path(sys.executable).stem.lower().endswith('-cli')) or (args and args[0]=='--tray'):
        from backend.tray import main as desktop
        desktop();return
    if args and args[0]=='--serve':
        args=args[1:];sys.argv=[sys.argv[0]]+args
    if args and args[0]=='--version':
        print('CameraBridge '+tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']);return
    if args and args[0]=='panels':
        p=argparse.ArgumentParser(description='Export native DashBoard panels and local logo files.')
        p.add_argument('--output',required=True);a=p.parse_args(args[1:]);export_panels(a.output);return
    if args and args[0]=='diagnostic':
        from tools.host_diagnostic import collect
        p=argparse.ArgumentParser(description='Read host facts.');p.add_argument('--output');a=p.parse_args(args[1:])
        data=json.dumps(collect(),indent=2)
        if a.output:pathlib.Path(a.output).write_text(data,encoding='utf-8')
        else:print(data)
        return
    commands={'panel-host':'tools.td_panel_host','ross-relay':'tools.ross_dev_relay'}
    if args and args[0] in commands:
        import importlib
        module=importlib.import_module(commands[args[0]]);sys.argv=[sys.argv[0]]+args[1:];module.main();return
    if '--help' in args or '-h' in args:print('Desktop: --tray. Console service: --serve. Commands: panels, panel-host, ross-relay, diagnostic.\n')
    from backend.server import main as serve
    serve()

if __name__=='__main__':main()
