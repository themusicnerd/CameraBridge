"""Read-only, credential-free compatibility report. Run locally on the target host."""
import argparse
import datetime
import json
import os
import pathlib
import platform
import shutil
import socket
import subprocess

def run(*args):
    if not shutil.which(args[0]):return {'available':False}
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=5)
        return {'available':True,'exit':p.returncode,'output':p.stdout[:40000]}
    except Exception as exc:return {'error':type(exc).__name__}

def collect():
    report={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'architecture':platform.machine(),'cpu':platform.processor(),'os':platform.platform(),
        'python':platform.python_version(),'hostname':socket.gethostname(),
        'storage':dict(zip(('total','used','free'),shutil.disk_usage(pathlib.Path.home()))),
        'home_writable':os.access(pathlib.Path.home(),os.W_OK),
        'vendor_permission':'Not established; confirm with Ross before TD1C deployment',
        'update_persistence':'Unknown; verify vendor-supported persistent location',
        'loopback':False}
    try:
        with socket.socket() as s:s.bind(('127.0.0.1',0));report['loopback']=True
    except OSError:pass
    if platform.system()=='Linux':
        for file,key in [('/etc/os-release','distribution'),('/proc/meminfo','memory'),('/proc/1/comm','init')]:
            try:report[key]=pathlib.Path(file).read_text()[:10000]
            except OSError:report[key]='unavailable'
        report.update(identity=run('id'),mounts=run('findmnt','-o','TARGET,FSTYPE,OPTIONS'),
            processes=run('ps','-eo','pid,comm,rss'),listeners=run('ss','-lntu'),
            systemd=run('systemctl','--version'),user_services=run('systemctl','--user','is-system-running'),
            persistent_users=run('loginctl','show-user',str(os.getuid()),'-p','Linger'))
    else:report['note']=platform.system()+' host; this is not TD1C evidence'
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();text=json.dumps(collect(),indent=2)
    if a.output:pathlib.Path(a.output).write_text(text,encoding='utf-8')
    else:print(text)
