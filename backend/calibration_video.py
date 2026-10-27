"""Workstation video input and checkerboard calibration. Never moves a camera."""
import copy
import io
import json
import math
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
from functools import lru_cache

PNG=b'\x89PNG\r\n\x1a\n'
MAX_FRAME=40*1024*1024


def cv_modules():
    try:
        import cv2,numpy
        return cv2,numpy
    except ImportError as exc:raise RuntimeError('Install the CameraBridge video dependencies on this workstation') from exc


def ffmpeg_path():
    path=os.environ.get('CAMERABRIDGE_FFMPEG') or shutil.which('ffmpeg')
    if not path or not pathlib.Path(path).is_file():raise RuntimeError('FFmpeg not found. Install it or set CAMERABRIDGE_FFMPEG to its executable.')
    return str(pathlib.Path(path).resolve())


def popen_options():
    return {'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}


@lru_cache(maxsize=4)
def rtsp_timeout_option(executable):
    result=subprocess.run([executable,'-hide_banner','-h','demuxer=rtsp'],capture_output=True,timeout=5,**popen_options())
    text=(result.stdout+result.stderr).decode('utf-8','replace')
    if re.search(r'\s-stimeout\s',text):return '-stimeout'
    if re.search(r'\s-timeout\s',text):return '-timeout'
    raise ValueError('This FFmpeg build does not expose the required RTSP input options')


def capture_devices():
    if sys.platform=='win32':
        result=subprocess.run([ffmpeg_path(),'-hide_banner','-list_devices','true','-f','dshow','-i','dummy'],
            capture_output=True,timeout=10,**popen_options())
        devices=[]
        for line in result.stderr.decode('utf-8','replace').splitlines():
            match=re.search(r'"(.*?)" \((?:audio, )?video\)',line)
            if match:devices.append(dict(id=match[1],label=match[1]))
            elif devices and 'Alternative name' in line:
                match=re.search(r'Alternative name "(.*?)"',line)
                if match:devices[-1]['id']=match[1]
        return devices
    if sys.platform.startswith('linux'):
        return [dict(id=str(pathlib.Path('/dev')/p.name),label=(p/'name').read_text().strip()+' ('+p.name+')')
                for p in sorted(pathlib.Path('/sys/class/video4linux').glob('video*')) if (p/'name').is_file()]
    raise ValueError('USB capture discovery is available on Windows and Linux')


def input_args(config):
    kind=config.get('type');source=config.get('source','')
    if not isinstance(source,str) or not 1<=len(source)<=2048 or '\0' in source:raise ValueError('Select a video source')
    if kind=='rtsp':
        parsed=urllib.parse.urlsplit(source)
        if parsed.scheme not in ('rtsp','rtsps') or not parsed.hostname:raise ValueError('Enter an RTSP or RTSPS camera URL')
        return ['-rtsp_transport','tcp','-timeout','5000000','-i',source]
    if kind=='usb':
        width=config.get('width');height=config.get('height');format_args=[]
        if width is not None or height is not None:
            if type(width) is not int or type(height) is not int or not 16<=width<=4096 or not 16<=height<=2160:raise ValueError('Set both USB capture dimensions, or leave both blank for device default')
            format_args=['-video_size',str(width)+'x'+str(height)]
        if sys.platform=='win32':return ['-f','dshow','-rtbufsize','64M']+format_args+['-i','video='+source]
        if sys.platform.startswith('linux') and re.fullmatch(r'/dev/video\d+',source):return ['-f','v4l2']+format_args+['-i',source]
        raise ValueError('Select a supported USB capture device')
    raise ValueError('Choose NDI, RTSP, or USB Capture (Magewell)')


def read_exact(stream,size):
    data=bytearray()
    while len(data)<size:
        part=stream.read(size-len(data))
        if not part:raise EOFError('Video input stopped')
        data.extend(part)
    return bytes(data)


def read_png(stream):
    result=bytearray(read_exact(stream,8))
    if result!=PNG:raise ValueError('Invalid video frame header')
    chunks=0
    while True:
        header=read_exact(stream,8);size=struct.unpack('>I',header[:4])[0];chunks+=1
        if size>MAX_FRAME or len(result)+size+12>MAX_FRAME or chunks>16384:raise ValueError('Video frame exceeds calibration limits')
        chunk=read_exact(stream,size+4)
        if header[4:]==b'IHDR':
            if size!=13:raise ValueError('Invalid PNG image header')
            width,height=struct.unpack('>II',chunk[:8])
            if not 16<=width<=4096 or not 16<=height<=2160:raise ValueError('Calibration video must be at most 4096 x 2160')
        result.extend(header);result.extend(chunk)
        if header[4:]==b'IEND':return bytes(result)


class VideoSession:
    def __init__(self):
        self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None;self.process=None
        self.frame=None;self.frame_at=0;self.sequence=0;self.state='Stopped';self.error=None;self.kind=None
        self.samples=[];self.board=None;self.size=None;self.result=None;self.busy=False

    def stop(self):
        self.stop_event.set()
        with self.lock:process=self.process;thread=self.thread
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(3)
            except subprocess.TimeoutExpired:process.kill();process.wait(3)
        if thread and thread is not threading.current_thread():thread.join(5)
        if thread and thread.is_alive():raise RuntimeError('Video source is still stopping. Try again.')
        with self.lock:self.frame=None;self.frame_at=0;self.state='Stopped';self.error=None;self.thread=None;self.process=None

    def start(self,config):
        cv_modules()
        kind=config.get('type')
        if kind=='ndi':
            from .ndi_video import runtime as ndi_runtime
            runtime=ndi_runtime();source=config.get('source','')
            if not isinstance(source,str) or not 1<=len(source)<=2048:raise ValueError('Select an NDI source')
            args=None
        else:
            executable=ffmpeg_path();selected=input_args(config)
            if kind=='rtsp':selected[selected.index('-timeout')]=rtsp_timeout_option(executable)
            args=[executable,'-hide_banner','-loglevel','error']+selected;runtime=None
        self.stop()
        with self.lock:
            self.stop_event=threading.Event();self.state='Connecting';self.error=None;self.kind=kind
            self.samples=[];self.board=None;self.size=None;self.result=None
            self.thread=threading.Thread(target=self.run,args=(kind,config.get('source'),args,runtime),daemon=True,name='calibration-video')
            self.thread.start()

    def run(self,kind,source,args,runtime):
        cv,np=cv_modules();generator=None
        try:
            if kind=='ndi':generator=runtime.frames(source,self.stop_event)
            else:
                command=args+['-an','-vf','fps=5','-threads','1','-c:v','png','-pix_fmt','rgb24','-compression_level','1','-f','image2pipe','pipe:1']
                process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**popen_options())
                with self.lock:self.process=process
                def frames():
                    while not self.stop_event.is_set():
                        image=cv.imdecode(np.frombuffer(read_png(process.stdout),dtype=np.uint8),cv.IMREAD_COLOR)
                        if image is None:raise ValueError('Cannot decode video frame')
                        yield image
                generator=frames()
            for image in generator:
                if self.stop_event.is_set():break
                height,width=image.shape[:2]
                if not 16<=width<=4096 or not 16<=height<=2160:raise ValueError('Calibration video must be at most 4096 x 2160')
                with self.lock:
                    if self.size and self.size!=(width,height):
                        raise ValueError('Video dimensions changed. Start a new calibration batch.')
                    self.frame=image;self.frame_at=time.monotonic();self.sequence+=1;self.state='Receiving'
        except Exception as exc:
            if not self.stop_event.is_set():
                # FFmpeg URLs can contain credentials. Do not return process command lines or stderr.
                with self.lock:self.state='Error';self.error=str(exc) if isinstance(exc,ValueError) else 'Cannot receive video. Check the source, runtime, and device access.'
        finally:
            if generator:generator.close()
            with self.lock:process=self.process
            if process and process.poll() is None:process.terminate()
            if process:
                try:process.wait(3)
                except subprocess.TimeoutExpired:process.kill();process.wait(3)
                if process.stdout:process.stdout.close()

    def snapshot(self):
        with self.lock:
            age=None if not self.frame_at else time.monotonic()-self.frame_at
            state='Stale' if self.state=='Receiving' and age is not None and age>2 else self.state
            return dict(state=state,error=self.error,type=self.kind,age_seconds=None if age is None else round(age,2),
                        width=None if self.frame is None else self.frame.shape[1],height=None if self.frame is None else self.frame.shape[0],
                        samples=len(self.samples),busy=self.busy,result=copy.deepcopy(self.result),
                        board=None if self.board is None else dict(columns=self.board[0],rows=self.board[1],square_mm=self.board[2]))

    def current(self):
        with self.lock:
            if self.state!='Receiving' or self.frame is None or time.monotonic()-self.frame_at>2:raise ValueError('Wait for a fresh video frame')
            return self.frame.copy()

    def preview(self):
        cv,_=cv_modules();frame=self.current();height,width=frame.shape[:2]
        if width>960:frame=cv.resize(frame,(960,round(height*960/width)),interpolation=cv.INTER_AREA)
        ok,data=cv.imencode('.jpg',frame,[cv.IMWRITE_JPEG_QUALITY,85])
        if not ok:raise ValueError('Cannot encode preview')
        return data.tobytes()

    def reset(self):
        with self.lock:
            if self.busy:raise ValueError('Wait for calibration to finish')
            self.samples=[];self.board=None;self.size=None;self.result=None

    def capture(self,config):
        cv,np=cv_modules()
        columns=config.get('columns',9);rows=config.get('rows',6);square=config.get('square_mm',25)
        if type(columns) is not int or type(rows) is not int or not 4<=columns<=20 or not 4<=rows<=20 or columns*rows>240:raise ValueError('Use 4 to 20 inner corners per board direction, up to 240 total')
        if type(square) not in (int,float) or not math.isfinite(square) or not 1<=square<=500:raise ValueError('Set the measured checkerboard square size in mm')
        image=self.current();height,width=image.shape[:2];board=(columns,rows,square)
        with self.lock:
            if self.busy:raise ValueError('Wait for calibration to finish')
            if len(self.samples)>=30:raise ValueError('Use up to 30 images in one lens-setting batch')
            if self.board and self.board!=board:raise ValueError('Board settings changed. Start a new batch.')
            self.busy=True
        try:
            gray=cv.cvtColor(image,cv.COLOR_BGR2GRAY)
            found,corners=cv.findChessboardCornersSB(gray,(columns,rows),flags=cv.CALIB_CB_NORMALIZE_IMAGE)
            if not found:raise ValueError('Checkerboard not found. Show the complete board, including its outer border.')
            points=corners.reshape(-1,2)
            hull=cv.convexHull(points);coverage=float(cv.contourArea(hull)/(width*height))
            if coverage<.015:raise ValueError('Checkerboard is too small in the image. Move it closer.')
            with self.lock:
                for previous in self.samples:
                    distance=float(np.sqrt(np.mean(np.sum((previous['corners'].reshape(-1,2)-points)**2,axis=1))))
                    if distance/math.hypot(width,height)<.012:raise ValueError('This board view is too similar to a saved view. Move and tilt the board.')
                self.samples.append(dict(corners=corners,coverage=coverage));self.board=board;self.size=(width,height);self.result=None
                return dict(samples=len(self.samples),coverage=round(coverage,3),message='Board image accepted')
        finally:
            with self.lock:self.busy=False

    def solve(self):
        cv,np=cv_modules()
        with self.lock:
            if self.busy:raise ValueError('Wait for calibration to finish')
            if len(self.samples)<12:raise ValueError('Capture at least 12 varied checkerboard views')
            self.busy=True;samples=[s['corners'].copy() for s in self.samples];columns,rows,square=self.board;size=self.size
        try:
            target=np.zeros((columns*rows,3),np.float32);target[:,:2]=np.mgrid[0:columns,0:rows].T.reshape(-1,2)*square
            constraints=[]
            def product(h,i,j):return np.array([h[0,i]*h[0,j],h[0,i]*h[1,j]+h[1,i]*h[0,j],h[1,i]*h[1,j],h[2,i]*h[0,j]+h[0,i]*h[2,j],h[2,i]*h[1,j]+h[1,i]*h[2,j],h[2,i]*h[2,j]])
            for observed in samples:
                h,_=cv.findHomography(target[:,:2]/max(columns*square,rows*square),(observed.reshape(-1,2)-np.array(size)/2)/np.array(size))
                if h is None:raise ValueError('Cannot estimate a checkerboard pose')
                constraints.extend([product(h,0,1),product(h,0,0)-product(h,1,1)])
            singular=np.linalg.svd(np.asarray(constraints),compute_uv=False)
            if singular[4]/max(singular[0],1e-12)<1e-4:raise ValueError('Board views do not constrain the lens. Capture more tilted board angles, not only flat translations.')
            rms,matrix,distortion,rotations,translations=cv.calibrateCamera([target.copy() for _ in samples],samples,size,None,None,
                criteria=(cv.TERM_CRITERIA_EPS+cv.TERM_CRITERIA_MAX_ITER,100,1e-9))
            if not np.isfinite(matrix).all() or not np.isfinite(distortion).all() or not math.isfinite(rms):raise ValueError('Calibration did not produce finite results')
            width,height=size;fx,fy=float(matrix[0,0]),float(matrix[1,1]);cx,cy=float(matrix[0,2]),float(matrix[1,2])
            if fx<=0 or fy<=0 or not 0<cx<width or not 0<cy<height:raise ValueError('Calibration is implausible. Capture more varied board positions and angles.')
            errors=[]
            for observed,r,t in zip(samples,rotations,translations):
                projected,_=cv.projectPoints(target,r,t,matrix,distortion)
                errors.append(float(np.sqrt(np.mean(np.sum((observed-projected)**2,axis=2)))))
            result=dict(model='opencv-pinhole-5',width=width,height=height,camera_matrix=matrix.tolist(),
                        distortion=distortion.ravel().tolist(),rms_pixels=float(rms),view_errors=errors,views=len(samples),
                        board_columns=columns,board_rows=rows,square_mm=square,
                        hfov=math.degrees(2*math.atan(width/(2*fx))),captured_at=time.time(),
                        normalized_intrinsics=dict(fx=fx/width,fy=fy/height,cx=cx/width,cy=cy/height),
                        nodal_offset_calibrated=False,timing_calibrated=False,
                        warnings=['Inspect independent images and overlay alignment before use.']+(['High reprojection error. Check board flatness, focus, image crop, and view variety.'] if rms>1 else []))
            from .calibration import validate_optical
            validate_optical(dict(result,zoom=0,focus=0))
            with self.lock:self.result=result
            return copy.deepcopy(result)
        finally:
            with self.lock:self.busy=False
