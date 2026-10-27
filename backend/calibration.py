"""Stationary encoder capture and measured-target lens calibration profiles."""
import math
import time
from .tracking import SUPPORTED, parse_pan_tilt, parse_lens


def number(value, low, high, name, integer=False):
    if type(value) not in ((int,) if integer else (int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError('Invalid calibration '+name)
    return value


def validate(profile):
    if not isinstance(profile,dict) or set(profile)-{'version','name','model','video_width','video_height','lens_points','optical_solutions'}:
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
    solutions=profile.get('optical_solutions',[])
    if not isinstance(solutions,list) or len(solutions)>16:raise ValueError('Use up to 16 optical lens settings per profile')
    encoders=set()
    for solution in solutions:
        validate_optical(solution)
        if (solution['width'],solution['height'])!=(profile['video_width'],profile['video_height']):raise ValueError('Optical calibration dimensions do not match the profile')
        if solution['zoom'] in encoders:raise ValueError('Use one optical solve per zoom encoder in a profile')
        encoders.add(solution['zoom'])


def validate_optical(s):
    keys={'model','width','height','camera_matrix','distortion','rms_pixels','view_errors','views','board_columns','board_rows','square_mm','hfov','captured_at','normalized_intrinsics','nodal_offset_calibrated','timing_calibrated','warnings','zoom','focus'}
    if not isinstance(s,dict) or set(s)!=keys or s['model']!='opencv-pinhole-5':raise ValueError('Invalid optical calibration schema')
    for k,low,high in [('width',16,4096),('height',16,2160),('views',12,30),('board_columns',4,20),('board_rows',4,20),('zoom',0,0xffffff),('focus',0,0xffffff)]:number(s[k],low,high,k,True)
    number(s['rms_pixels'],0,100,'reprojection error');number(s['square_mm'],1,500,'checkerboard square size');number(s['captured_at'],1,1e12,'capture time')
    m=s['camera_matrix']
    if not isinstance(m,list) or len(m)!=3 or any(not isinstance(row,list) or len(row)!=3 for row in m):raise ValueError('Invalid camera matrix')
    for row in m:
        for v in row:number(v,-1e9,1e9,'matrix value')
    if m[0][0]<=0 or m[1][1]<=0 or not 0<m[0][2]<s['width'] or not 0<m[1][2]<s['height'] or m[2]!=[0,0,1] or abs(m[0][1])+abs(m[1][0])>1e-8:raise ValueError('Invalid camera intrinsic matrix')
    for key,count,low,high in [('distortion',5,-100,100),('view_errors',s['views'],0,100)]:
        values=s[key]
        if not isinstance(values,list) or len(values)!=count:raise ValueError('Invalid optical '+key)
        for value in values:number(value,low,high,key)
    expected=math.degrees(2*math.atan(s['width']/(2*m[0][0])))
    number(s['hfov'],.01,179.99,'optical field of view')
    if type(s['hfov']) not in (int,float) or not math.isfinite(s['hfov']) or abs(s['hfov']-expected)>1e-5:raise ValueError('Optical field of view does not match the intrinsic matrix')
    expected_norm=dict(fx=m[0][0]/s['width'],fy=m[1][1]/s['height'],cx=m[0][2]/s['width'],cy=m[1][2]/s['height'])
    if not isinstance(s['normalized_intrinsics'],dict) or set(s['normalized_intrinsics'])!=set(expected_norm):raise ValueError('Invalid normalized intrinsics')
    for k,v in expected_norm.items():
        actual=s['normalized_intrinsics'][k];number(actual,-1e9,1e9,'normalized intrinsic')
        if abs(actual-v)>1e-8:raise ValueError('Normalized intrinsic does not match the camera matrix')
    if s['nodal_offset_calibrated'] is not False or s['timing_calibrated'] is not False:raise ValueError('This solver does not measure nodal offset or video timing')
    if not isinstance(s['warnings'],list) or len(s['warnings'])>8 or any(not isinstance(w,str) or len(w)>300 for w in s['warnings']):raise ValueError('Invalid optical warnings')


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
