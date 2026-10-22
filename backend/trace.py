"""Opt-in asynchronous control timing capture. No credentials are recorded."""
import datetime
import json
import os
from pathlib import Path
import queue
import threading
import time

_local=threading.local()
_queue=queue.Queue(maxsize=20000)
_target=None
_dropped=0
try:
    marker=Path(os.environ.get('LOCALAPPDATA',''))/'CameraBridge'/'trace.enabled'
    if marker.is_file():
        _target=Path(marker.read_text(encoding='utf-8').strip())
        _target.parent.mkdir(parents=True,exist_ok=True)
except OSError:
    pass

def context(value):
    _local.request=value

def record(event,**fields):
    global _dropped
    if _target is None:return
    entry=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds'),
               mono=time.monotonic(),event=event,thread=threading.current_thread().name,
               request=getattr(_local,'request',None),**fields)
    try:_queue.put_nowait(entry)
    except queue.Full:_dropped+=1

def _write():
    try:
        with _target.open('a',encoding='utf-8',buffering=1) as stream:
            while True:
                entry=_queue.get()
                entry['capture_dropped_total']=_dropped
                stream.write(json.dumps(entry,separators=(',',':'))+'\n')
    except OSError:
        pass

if _target is not None:
    threading.Thread(target=_write,name='control-trace-writer',daemon=True).start()
    record('capture-start',pid=os.getpid())
