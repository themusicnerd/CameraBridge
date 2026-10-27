"""Build one native package on its target operating system."""
import argparse
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import shutil
import ssl
import subprocess
import sys
import tarfile
import tomllib
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--target',required=True,choices=['windows-x64','linux-x64','macos-x64','macos-arm64']);p.add_argument('--package-root',default='build/package');a=p.parse_args()
    expected={'Windows':'windows','Linux':'linux','Darwin':'macos'}[platform.system()]
    arch='arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64'
    if a.target!=expected+'-'+arch:raise SystemExit('Build on the requested operating system and architecture.')
    version=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    build=ROOT/'build';build.mkdir(exist_ok=True)
    datas=[(str(ROOT/source),destination) for source,destination in [('web','web'),('dashboard','dashboard'),('config.example.json','.'),('pyproject.toml','.')]]
    if expected in ('windows','linux'):
        if not (ROOT/'sony').is_dir():raise SystemExit('Build the Sony SDK adapter with tools/build_sony.py first')
        datas.append((str(ROOT/'sony'),'sony'))
    # Some managed Python distributions require an extra CA policy resource.
    # Preserve that distribution's TLS policy in its frozen runtime.
    runtime_ca=pathlib.Path(ssl.__file__).with_name('codex-rejected-cas.pem')
    if runtime_ca.is_file():datas.append((str(runtime_ca),'.'))
    spec=build/'CameraBridge.spec'
    body=f'''a = Analysis([{str(ROOT/'camerabridge.py')!r}], pathex=[{str(ROOT)!r}], datas={datas!r}, hiddenimports=['tools.td_panel_host','tools.ross_dev_relay','tools.host_diagnostic'], excludes=['PySide6.QtQml','PySide6.QtQuick','PySide6.QtOpenGL','PySide6.QtPdf','PySide6.QtSql','PySide6.QtTest','PySide6.QtXml','PySide6.QtPrintSupport'])
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CameraBridge', console={expected!='windows'!r}, upx=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CameraBridge-cli', console=True, upx=False)
collection = COLLECT(gui, cli, a.binaries, a.datas, strip=False, upx=False, name='CameraBridge')
'''
    if expected=='macos':body+="app = BUNDLE(collection, name='CameraBridge.app', bundle_identifier='com.camerabridge.desktop', info_plist={'LSUIElement': True})\n"
    spec.write_text(body,encoding='utf-8')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean',str(spec)],cwd=ROOT,check=True)
    bundle=(ROOT/a.package_root/'CameraBridge').resolve()
    if not bundle.is_relative_to(ROOT.resolve()):raise SystemExit('Package output must stay inside the repository')
    if bundle.exists():shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    if expected=='macos':
        shutil.copytree(ROOT/'dist/CameraBridge.app',bundle/'CameraBridge.app',symlinks=True)
        wrapper=bundle/'CameraBridge-cli'
        wrapper.write_text('#!/bin/sh\nexec "$(dirname "$0")/CameraBridge.app/Contents/MacOS/CameraBridge-cli" "$@"\n',encoding='utf-8');wrapper.chmod(0o755)
    else:shutil.copytree(ROOT/'dist/CameraBridge',bundle,dirs_exist_ok=True,symlinks=True)
    if expected=='windows':
        # The separate Sony child process needs its own MSVC runtime search path.
        # Reuse the redistributable DLLs already shipped with the Qt application.
        sony=bundle/'_internal/sony';found=set()
        for directory in (bundle/'_internal',bundle/'_internal/PySide6'):
            for dll in directory.glob('*.dll'):
                if '140' in dll.name and dll.name.lower().startswith(('msvcp','vcruntime')):
                    shutil.copy2(dll,sony/dll.name);found.add(dll.name.lower())
        if not {'msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'}<=found:raise SystemExit('Missing bundled Sony MSVC runtime dependency')
    shutil.copytree(ROOT/'docs',bundle/'docs',dirs_exist_ok=True)
    shutil.copytree(ROOT/'deployment',bundle/'deployment',dirs_exist_ok=True)
    for name in ('README.md','CHANGELOG.md','THIRD-PARTY-NOTICES.md','config.example.json'):
        shutil.copy2(ROOT/name,bundle/name)
    python_license=pathlib.Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.is_file():
        (bundle/'licenses/Python').mkdir(parents=True,exist_ok=True)
        shutil.copy2(python_license,bundle/'licenses/Python/LICENSE.txt')
    for package in ('pyinstaller','PySide6-Essentials','shiboken6','numpy','opencv-python-headless'):
        distribution=importlib.metadata.distribution(package)
        for file in distribution.files or []:
            if 'licenses' not in file.parts:continue
            source=distribution.locate_file(file)
            if source.is_file():
                target=bundle/'licenses'/package/pathlib.Path(*file.parts[file.parts.index('licenses')+1:])
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    import cv2
    for source in pathlib.Path(cv2.__file__).parent.glob('LICENSE*'):
        target=bundle/'licenses/opencv-python-headless'/source.name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    (bundle/'BUILD.json').write_text(json.dumps(dict(version=version,target=a.target,python=platform.python_version(),
        os=platform.platform(),signed=False,hardware_accepted=False),indent=2)+'\n',encoding='utf-8')
    output=ROOT/'release';output.mkdir(exist_ok=True);stem='CameraBridge-'+version+'-'+a.target
    if expected=='windows':
        archive=output/(stem+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():z.write(path,path.relative_to(bundle.parent))
    else:
        archive=output/(stem+'.tar.gz')
        with tarfile.open(archive,'w:gz') as tar:tar.add(bundle,arcname='CameraBridge')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    print(archive)

if __name__=='__main__':main()
