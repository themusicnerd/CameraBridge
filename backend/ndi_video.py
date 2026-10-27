"""NDI receive bindings. Loads the user's runtime; no NDI binaries are distributed."""
import ctypes as C
import ctypes.util
import os
import pathlib
import sys
import time
from functools import lru_cache


class Source(C.Structure):
    _fields_=[('name',C.c_char_p),('address',C.c_char_p)]


class Finder(C.Structure):
    _fields_=[('local',C.c_bool),('groups',C.c_char_p),('extra',C.c_char_p)]


class Receiver(C.Structure):
    _fields_=[('source',Source),('color',C.c_int),('bandwidth',C.c_int),('fields',C.c_bool),('name',C.c_char_p)]


class Video(C.Structure):
    _fields_=[('width',C.c_int),('height',C.c_int),('fourcc',C.c_uint32),('rate_n',C.c_int),
              ('rate_d',C.c_int),('aspect',C.c_float),('format',C.c_int),('timecode',C.c_int64),
              ('data',C.c_void_p),('stride',C.c_int),('metadata',C.c_char_p),('timestamp',C.c_int64)]


def runtime_path():
    name='Processing.NDI.Lib.x64.dll' if sys.platform=='win32' else 'libndi.dylib' if sys.platform=='darwin' else 'libndi.so.6'
    candidates=[]
    for variable in ('NDI_RUNTIME_DIR_V6','NDI_RUNTIME_DIR_V5','NDI_SDK_DIR'):
        if os.environ.get(variable):
            root=pathlib.Path(os.environ[variable]);candidates.extend([root/name,root/'v6'/name,root/'Bin/x64'/name])
    if sys.platform=='win32':
        root=pathlib.Path(os.environ.get('ProgramFiles','C:/Program Files'))/'NDI'
        candidates.extend([root/'NDI 6 Runtime/v6'/name,root/'NDI 6 SDK/Bin/x64'/name,root/'NDI 5 Runtime'/name])
    else:
        for directory in ('/usr/local/lib','/usr/lib','/opt/ndi/lib/x86_64-linux-gnu'):
            candidates.extend([pathlib.Path(directory)/name,pathlib.Path(directory)/'libndi.so'])
    for path in candidates:
        if path.is_file():return str(path)
    found=C.util.find_library('ndi')
    if found:return found
    raise RuntimeError('NDI runtime not found. Install the NDI runtime on this video workstation.')


class NDI:
    def __init__(self):
        self.lib=C.CDLL(runtime_path())
        signatures={
            'NDIlib_initialize':([],C.c_bool),
            'NDIlib_find_create_v2':([C.POINTER(Finder)],C.c_void_p),
            'NDIlib_find_wait_for_sources':([C.c_void_p,C.c_uint32],C.c_bool),
            'NDIlib_find_get_current_sources':([C.c_void_p,C.POINTER(C.c_uint32)],C.POINTER(Source)),
            'NDIlib_find_destroy':([C.c_void_p],None),
            'NDIlib_recv_create_v3':([C.POINTER(Receiver)],C.c_void_p),
            'NDIlib_recv_capture_v2':([C.c_void_p,C.POINTER(Video),C.c_void_p,C.c_void_p,C.c_uint32],C.c_int),
            'NDIlib_recv_free_video_v2':([C.c_void_p,C.POINTER(Video)],None),
            'NDIlib_recv_destroy':([C.c_void_p],None),
        }
        for key,(args,result) in signatures.items():
            fn=getattr(self.lib,key);fn.argtypes=args;fn.restype=result
        if not self.lib.NDIlib_initialize():raise RuntimeError('NDI runtime initialization failed')

    def sources(self):
        finder=self.lib.NDIlib_find_create_v2(C.byref(Finder(True,None,None)))
        if not finder:raise RuntimeError('Cannot start NDI discovery')
        try:
            deadline=time.monotonic()+1.5
            result=[]
            while time.monotonic()<deadline:
                self.lib.NDIlib_find_wait_for_sources(finder,250)
                count=C.c_uint32();sources=self.lib.NDIlib_find_get_current_sources(finder,C.byref(count))
                result=[dict(id=(sources[i].name or b'').decode('utf-8','replace'),
                             label=(sources[i].name or b'').decode('utf-8','replace')) for i in range(min(count.value,512))]
            return result
        finally:self.lib.NDIlib_find_destroy(finder)

    def frames(self,name,stop):
        import numpy as np
        source=Source(name.encode('utf-8'),None)
        receiver=self.lib.NDIlib_recv_create_v3(C.byref(Receiver(source,0,100,False,b'CameraBridge Calibration')))
        if not receiver:raise RuntimeError('Cannot start the NDI receiver')
        last=0
        try:
            while not stop.is_set():
                video=Video();kind=self.lib.NDIlib_recv_capture_v2(receiver,C.byref(video),None,None,250)
                if kind!=1:continue
                try:
                    if time.monotonic()-last<.19:continue
                    last=time.monotonic()
                    if not 16<=video.width<=4096 or not 16<=video.height<=2160:raise ValueError('Calibration video must be at most 4096 x 2160')
                    if video.fourcc not in (int.from_bytes(b'BGRX','little'),int.from_bytes(b'BGRA','little')):raise ValueError('NDI did not return the requested BGRX video format')
                    stride=video.stride or video.width*4
                    if not video.data or not video.width*4<=stride<=video.width*4+65536 or stride*video.height>40*1024*1024:raise ValueError('Invalid NDI frame layout')
                    raw=C.string_at(video.data,stride*video.height)
                    frame=np.frombuffer(raw,dtype=np.uint8).reshape(video.height,stride)[:,:video.width*4].reshape(video.height,video.width,4)[:,:,:3].copy()
                    yield frame
                finally:self.lib.NDIlib_recv_free_video_v2(receiver,C.byref(video))
        finally:self.lib.NDIlib_recv_destroy(receiver)


@lru_cache(maxsize=1)
def runtime():return NDI()
