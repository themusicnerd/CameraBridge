"""Measured Panasonic pose to FreeD D1. Output repetition is not a new measurement."""
import copy
import ipaddress
import math
import re
import socket
import threading
import time

SUPPORTED = {'AW-HE40', 'AW-HE130', 'AW-HE120', 'AW-HE50', 'AW-HE60', 'AW-UE70', 'AW-HE42', 'AW-UE150'}
DEFAULTS = dict(enabled=False, xpression_enabled=False, host='', port=40000,
                xpression_port=40001, camera_id=1, rate=50, sample_rate=2,
                stale_seconds=1.5, pan_zero=32768, tilt_zero=32768,
                degrees_per_count=0.00825, pan_invert=False, tilt_invert=True,
                x_mm=0, y_mm=0, z_mm=0, roll=0)


def settings(camera):
    return {**DEFAULTS, 'camera_id':camera.get('number', 1), **camera.get('tracking_output', {})}


def validate(camera):
    supplied = camera.get('tracking_output', {})
    if not isinstance(supplied, dict) or set(supplied) - set(DEFAULTS):
        raise ValueError('Invalid tracking output settings')
    cfg = settings(camera)
    for key in ('enabled', 'xpression_enabled', 'pan_invert', 'tilt_invert'):
        if type(cfg[key]) is not bool: raise ValueError('Invalid tracking switch: ' + key)
    for key, low, high in [('port',1024,65535),('xpression_port',1024,65535),('camera_id',0,255),
                           ('rate',1,60),('pan_zero',0,65535),('tilt_zero',0,65535)]:
        if type(cfg[key]) is not int or not low <= cfg[key] <= high:
            raise ValueError('Invalid tracking value: ' + key)
    for key, low, high in [('sample_rate',0.2,3),('stale_seconds',0.5,5),('degrees_per_count',0.00001,0.02),
                          ('x_mm',-131071,131071),('y_mm',-131071,131071),('z_mm',-131071,131071),('roll',-180,180)]:
        if type(cfg[key]) not in (int,float) or not math.isfinite(cfg[key]) or not low <= cfg[key] <= high:
            raise ValueError('Invalid tracking value: ' + key)
    if cfg['stale_seconds'] < 1/cfg['sample_rate']:
        raise ValueError('Tracking stale limit must be at least one sample interval')
    if not isinstance(cfg['host'],str): raise ValueError('Invalid tracking destination')
    if cfg['enabled'] or cfg['xpression_enabled']:
        address = ipaddress.IPv4Address(cfg['host'])
        if address.is_unspecified or address.is_multicast or str(address)=='255.255.255.255':
            raise ValueError('Use a unicast tracking destination')
        if camera.get('driver')!='panasonic' or camera.get('model') not in SUPPORTED or camera.get('simulator'):
            raise ValueError('Measured tracking is available for the listed mechanical Panasonic profiles only')
        if cfg['enabled'] and cfg['xpression_enabled'] and cfg['port']==cfg['xpression_port']:
            raise ValueError('Use separate Unreal and XPression adapter ports')


def parse_pan_tilt(reply):
    if not re.fullmatch(r'aPC[0-9A-Fa-f]{8}', reply): raise ValueError('Invalid absolute pan/tilt reply')
    return int(reply[3:7],16), int(reply[7:11],16)


def parse_lens(reply):
    if not re.fullmatch(r'lPI[0-9A-Fa-f]{9}', reply): raise ValueError('Invalid lens reply')
    values = tuple(int(reply[i:i+3],16) for i in (3,6,9))
    if any(not 0x555 <= v <= 0xfff for v in values): raise ValueError('Lens encoder out of range')
    return values


def pose(raw, cfg):
    pan = (raw['pan']-cfg['pan_zero'])*cfg['degrees_per_count']*(-1 if cfg['pan_invert'] else 1)
    tilt = (raw['tilt']-cfg['tilt_zero'])*cfg['degrees_per_count']*(-1 if cfg['tilt_invert'] else 1)
    return dict(pan=(pan+180)%360-180, tilt=tilt, roll=cfg['roll'],
                x=cfg['x_mm'], y=cfg['y_mm'], z=cfg['z_mm'], zoom=raw['zoom'], focus=raw['focus'])


def encode_d1(camera_id, value):
    if type(camera_id) is not int or not 0 <= camera_id <= 255: raise ValueError('Invalid FreeD camera ID')
    packet = bytearray([0xd1, camera_id])
    for key, scale, limit in [('pan',32768,180),('tilt',32768,90),('roll',32768,180),
                              ('x',64,131071),('y',64,131071),('z',64,131071)]:
        v=value[key]
        if not math.isfinite(v) or abs(v)>limit: raise ValueError('FreeD range exceeded: '+key)
        packet.extend(round(v*scale).to_bytes(3,'big',signed=True))
    for key in ('zoom','focus'):
        v=value[key]
        if type(v) is not int or not 0<=v<=0xffffff: raise ValueError('Invalid FreeD lens encoder')
        packet.extend(v.to_bytes(3,'big'))
    packet.extend(b'\x00\x00')
    packet.append((0x40-sum(packet)) & 255)
    return bytes(packet)


class Tracking:
    def __init__(self, engine):
        self.engine=engine
        self.samples={}
        for cid,c in engine.cameras.items():
            c['tracking_status']=dict(state='Disabled', packets=0, samples=0, error=None,
                                      measured_hz=None, age_seconds=None)

    def start(self):
        for cid in self.engine.cameras:
            for target in (self.sample, self.transmit):
                t=threading.Thread(target=target,args=(cid,),daemon=True,name='tracking-'+target.__name__+'-'+cid)
                self.engine.threads.append(t);t.start()

    def sample(self,cid):
        e=self.engine;c=e.cameras[cid]
        previous=None
        while not e.closed.is_set():
            with e.lock: cfg=copy.deepcopy(settings(c['config']))
            if not (cfg['enabled'] or cfg['xpression_enabled']):
                with e.lock:
                    self.samples.pop(cid,None);c['tracking_status'].update(state='Disabled',error=None,age_seconds=None)
                e.closed.wait(.2);previous=None;continue
            started=time.monotonic()
            try:
                # Release access after each request. Stop and movement have priority.
                with c['io'].priority(15): pan,tilt=parse_pan_tilt(c['driver'].send('#APC'))
                measured=time.monotonic()
                if e.closed.is_set():break
                with c['io'].priority(15): zoom,focus,iris=parse_lens(c['driver'].send('#LPI'))
                with e.lock:
                    if cfg==settings(c['config']):
                        self.samples[cid]=(cfg,dict(pan=pan,tilt=tilt,zoom=zoom,focus=focus,iris=iris),measured)
                        c['tracking_status'].update(state='Measured',error=None,raw=dict(self.samples[cid][1]),
                            samples=c['tracking_status']['samples']+1,
                            measured_hz=None if previous is None else round(1/max(.001,measured-previous),2))
                        previous=measured
            except Exception as exc:
                with e.lock:
                    self.samples.pop(cid,None);c['tracking_status'].update(state='Read Error',error=str(exc),age_seconds=None)
                previous=None
            e.closed.wait(max(.01,1/cfg['sample_rate']-(time.monotonic()-started)))

    def transmit(self,cid):
        e=self.engine;c=e.cameras[cid]
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            udp.setblocking(False)
            while not e.closed.is_set():
                with e.lock:
                    cfg=copy.deepcopy(settings(c['config']));sample=self.samples.get(cid)
                    if sample and sample[0]!=cfg:sample=None
                    if sample:
                        age=time.monotonic()-sample[2];c['tracking_status']['age_seconds']=round(age,3)
                        if age>cfg['stale_seconds']:
                            c['tracking_status']['state']='Stale';sample=None
                    if sample:
                        try:
                            packet=encode_d1(cfg['camera_id'],pose(sample[1],cfg))
                            # Hold the lock through send to prevent an old destination after disable/save.
                            for enabled,port in [('enabled','port'),('xpression_enabled','xpression_port')]:
                                if cfg[enabled]:udp.sendto(packet,(cfg['host'],cfg[port]));c['tracking_status']['packets']+=1
                            c['tracking_status'].update(state='Sending',error=None)
                        except Exception as exc:
                            c['tracking_status'].update(state='Output Error',error=str(exc))
                e.closed.wait(1/cfg['rate'])
