"""Browser acceptance with generated checkerboard images. Opens no capture hardware."""
import argparse,json,pathlib,sys,threading,time
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.calibration_workstation import start
from backend.calibration_video import cv_modules
from backend.calibration import validate
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshot',type=pathlib.Path);args=parser.parse_args()
    cv,np=cv_modules();server=start();v=server.video;stop=threading.Event();selections=[]
    image=np.full((420,600,3),255,np.uint8)
    for y in range(7):
        for x in range(10):
            if (x+y)%2==0:image[y*60:(y+1)*60,x*60:(x+1)*60]=0
    matrix=np.array([[950.,0,640],[0,945.,360],[0,0,1]])
    mapping=np.array([[25/60,0,-25],[0,25/60,-25],[0,0,1]])
    def board_frame(i):
        rotation,_=cv.Rodrigues(np.array([-.35+.2*(i%4),-.3+.17*(i%5),-.12+.05*(i%6)]))
        translation=np.array([-190.+60*(i%4),-105.+55*(i//4),650.+40*(i%3)])
        h=matrix@np.column_stack((rotation[:,:2],translation))@mapping
        return cv.warpPerspective(image,h,(1280,720),borderValue=(255,255,255))
    def start_input(config):
        selections.append(config)
        with v.lock:v.frame=board_frame(0);v.frame_at=time.monotonic();v.state='Receiving';v.kind=config['type']
    v.start=start_input
    def fresh():
        while not stop.wait(.05):
            with v.lock:v.frame_at=time.monotonic()
    updater=threading.Thread(target=fresh,daemon=True);updater.start()
    try:
        with patch('backend.calibration_workstation.capture_devices',return_value=[dict(id='magewell-fixture',label='Magewell USB Capture HDMI')]),sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1920,'height':1016});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:'+str(server.server_address[1]))
            expect(page.locator('#type')).to_have_value('ndi')
            page.locator('#type').select_option('rtsp');expect(page.locator('#rtsp')).to_be_visible();expect(page.locator('#rtsppassword')).to_be_visible()
            page.locator('#type').select_option('usb');page.locator('#discover').click();expect(page.locator('#source')).to_have_value('magewell-fixture')
            page.locator('#start').click();expect(page.locator('#videostate')).to_contain_text('1280 x 720')
            assert selections[-1]==dict(type='usb',source='magewell-fixture',width=1920,height=1080)
            expect(page.locator('#preview')).to_be_visible();assert page.locator('#preview').evaluate('(img)=>img.naturalWidth')==960
            page.locator('#model').fill('AW-HE40');page.locator('#zoom').fill('1911');page.locator('#focus').fill('2873')
            for i in range(12):
                with v.lock:v.frame=board_frame(i);v.frame_at=time.monotonic()
                page.locator('#capture').click()
                expect(page.locator('#samples')).to_have_text(str(i+1)+' Board Images Saved',timeout=15000)
            page.locator('#solve').click();expect(page.locator('#resultsummary')).to_contain_text('RMS',timeout=15000)
            assert v.result['rms_pixels']<.7,v.result
            assert abs(v.result['camera_matrix'][0][0]-950)<40,v.result
            page.reload();expect(page.locator('#resultsummary')).to_contain_text('RMS');expect(page.locator('#samples')).to_have_text('12 Board Images Saved')
            expect(page.locator('#zoom')).to_have_value('1911');expect(page.locator('#focus')).to_have_value('2873');expect(page.locator('#type')).to_have_value('usb')
            assert page.locator('.app-logo').evaluate('(img)=>img.complete&&img.naturalWidth>0')
            with page.expect_download() as received:page.locator('#export').click()
            bundle=json.loads(pathlib.Path(received.value.path()).read_text())
            assert bundle['format']=='CameraBridgeOpticalCalibration';validate(bundle['lens'])
            assert bundle['lens']['optical_solutions'][0]['zoom']==1911
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(args.screenshot),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors,errors
            browser.close()
        print('PASS: NDI/RTSP/Magewell source UI, native dimensions, preview, 12 image detections, optical solve, and tagged profile export')
    finally:stop.set();updater.join(2);server.close()


if __name__=='__main__':main()
