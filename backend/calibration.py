"""Stationary encoder capture and measured-target lens calibration profiles."""
import math
import time
from .tracking import SUPPORTED, parse_pan_tilt, parse_lens


def number(value, low, high, name, integer=False):
    if type(value) not in ((int,) if integer else (int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError('Invalid calibration '+name)
    return value


def validate(profile):
    if not isinstance(profile,dict) or set(profile)-{'version','name','model','video_width','video_height','lens_points'}:
        raise ValueError('Invalid camera calibration profile')
    if type(profile.get('version')) is not int or profile['version']!=1:raise ValueError('Unknown calibration profile version')
    for key in ('name','model'):
        if not isinstance(profile.get(key),str) or not 1<=len(profile[key])<=80:raise ValueError('Invalid calibration '+key)
    for key in ('video_width','video_height'):number(profile.get(key),16,16384,key,True)
    points=profile.get('lens_points',[])
    if not isinstance(points,list) or len(points)>64:raise ValueError('Use up to 64 lens calibration points')
    encoders=set()
    for point in points:
        if not isinstance(point,dict) or set(point)!={'zoom','focus','hfov','target_width_mm','distance_mm','target_pixels','captured_at'}:
            raise ValueError('Invalid lens calibration point')
        zoom=number(point['zoom'],0x555,0xfff,'zoom',True)
        number(point['focus'],0x555,0xfff,'focus',True)
        number(point['hfov'],.01,179.99,'horizontal field of view')
        number(point['target_width_mm'],1,100000,'target width')
        number(point['distance_mm'],1,1000000,'target distance')
        number(point['target_pixels'],1,profile['video_width'],'target image width')
        number(point['captured_at'],1,1e12,'capture time')
        expected=horizontal_fov(profile['video_width'],point['target_width_mm'],point['distance_mm'],point['target_pixels'])
        if abs(expected-point['hfov'])>.00001:raise ValueError('Lens field of view does not match the target measurements')
        if zoom in encoders:raise ValueError('Use one lens sample per zoom encoder in this profile')
        encoders.add(zoom)


def horizontal_fov(image_width, target_width_mm, distance_mm, target_pixels):
    number(image_width,16,16384,'image width',True)
    number(target_width_mm,1,100000,'target width')
    number(distance_mm,1,1000000,'target distance')
    number(target_pixels,1,image_width,'target image width')
    return math.degrees(2*math.atan(target_width_mm*image_width/(2*distance_mm*target_pixels)))


def capture(engine, cid):
    c=engine.cameras[cid]
    if c['config']['driver']!='panasonic' or c['config']['model'] not in SUPPORTED or c['config'].get('simulator'):
        raise ValueError('Calibration capture needs a supported mechanical Panasonic camera')
    def query(command):
        with c['io'].priority(15):
            with engine.lock:
                if engine.closed.is_set():raise ValueError('Camera setup is changing. Try again.')
                if c['moving'] or c['pending']:raise ValueError('Stop the camera and lens before calibration capture')
            return c['driver'].send(command)
    first_pt=parse_pan_tilt(query('#APC'));first_lens=parse_lens(query('#LPI'))
    last_pt=parse_pan_tilt(query('#APC'));last_lens=parse_lens(query('#LPI'))
    with engine.lock:
        if c['moving'] or c['pending'] or first_pt!=last_pt or first_lens!=last_lens:
            raise ValueError('Camera or lens moved during capture. Hold the shot still and try again.')
    return dict(pan=last_pt[0],tilt=last_pt[1],zoom=last_lens[0],focus=last_lens[1],iris=last_lens[2],
                captured_at=time.time(),model=c['config']['model'],host=c['config']['host'],port=c['config'].get('port',80))
