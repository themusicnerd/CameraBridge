"""Fetch verified Sony SDK packages and build CameraBridge's native adapter."""
import argparse
import hashlib
import pathlib
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[1]
PACKAGES={
    'Windows':('Win64','4d4cc0bee7fdd60e1e947bfa7a524cbfb5550465ceccc8647eb7b7cdc383ef77'),
    'Linux':('Linux64PC','467f2346270b438ed15d4a957c4558ef2f99756b4ee030219ef71168e5ba2aba'),
}
def extract(archive,dest):
    dest=dest.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if any(not (dest/n).resolve().is_relative_to(dest) for n in z.namelist()):raise ValueError('Unsafe SDK archive path')
        if z.testzip():raise ValueError('SDK archive integrity check failed')
        z.extractall(dest)

def main():
    p=argparse.ArgumentParser();p.add_argument('--sdk-root',type=pathlib.Path);a=p.parse_args()
    if platform.system() not in PACKAGES or platform.machine().lower() not in ('amd64','x86_64'):raise SystemExit('Sony builds currently support Windows and Linux x64')
    build=ROOT/'build/sony';build.mkdir(parents=True,exist_ok=True)
    if a.sdk_root:sample=a.sdk_root.resolve()
    else:
        suffix,digest=PACKAGES[platform.system()];archive=build/f'CrSDK_v2.02.00_20260610a_{suffix}.zip'
        if not archive.exists():urllib.request.urlretrieve('https://di.update.sony.net/NEX/Uhfc28896b/'+archive.name,archive)
        with archive.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=digest:raise SystemExit('Sony SDK checksum does not match the verified development package')
        extract(archive,build/'sdk');extract(build/'sdk/RemoteCli.zip',build/'RemoteCli');sample=build/'RemoteCli'
    native=build/'native'
    subprocess.run(['cmake','-S',str(ROOT/'native/sony'),'-B',str(native),'-DSONY_SAMPLE_ROOT='+str(sample)],check=True)
    subprocess.run(['cmake','--build',str(native),'--config','Release','--parallel','2'],check=True)
    exe='CameraBridge-Sony'+('.exe' if platform.system()=='Windows' else '')
    source=native/'Release' if platform.system()=='Windows' else native
    target=ROOT/'sony';target.mkdir(exist_ok=True)
    shutil.copy2(source/exe,target/exe)
    shutil.copytree(sample/'external/crsdk',target,dirs_exist_ok=True)
    class LicenseParser(HTMLParser):
        def __init__(self):super().__init__();self.active=False;self.parts=[]
        def handle_starttag(self,t,a):
            if t=='textarea':self.active=True
        def handle_endtag(self,t):
            if t=='textarea':self.active=False
        def handle_data(self,d):
            if self.active:self.parts.append(d)
    license_url='https://support.d-imaging.sony.co.jp/app/sdk/licenseagreement_d/en-US.html'
    parser=LicenseParser()
    with urllib.request.urlopen(license_url,timeout=30) as response:parser.feed(response.read().decode('utf-8'))
    text=''.join(parser.parts)
    if 'GRANT OF LICENSE' not in text:raise SystemExit('Could not obtain Sony SDK license text')
    (target/'SONY-SDK-LICENSE.txt').write_text(text,encoding='utf-8')
    for name,entry in [('libssh2','libssh2/COPYING'),('libusb','libusb/COPYING'),('openssl','openssl/LICENSE.txt')]:
        source=(sample.parent if a.sdk_root else build/'sdk')/'SourceCodeOfOpenSourceSoftware'/(name+'.zip')
        if not source.exists():raise SystemExit('Missing Sony SDK open source license archive')
        with zipfile.ZipFile(source) as z:
            licenses=target/'licenses';licenses.mkdir(exist_ok=True)
            (licenses/(name+'-LICENSE.txt')).write_bytes(z.read(entry))
    if platform.system()!='Windows':(target/exe).chmod(0o755)
    probe=subprocess.run([str(target/exe)],input='version\nquit\n',text=True,capture_output=True,timeout=15,check=True,cwd=target)
    if '"adapter":1' not in probe.stdout:raise SystemExit('Sony native adapter startup check failed')
    print('Sony SDK adapter compiled and initialized successfully')

if __name__=='__main__':main()
