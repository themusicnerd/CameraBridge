"""Persistent desktop settings, separate from the Qt interface."""
import dataclasses
import ipaddress
import json
import pathlib
from .server import ROOT,validate_config

@dataclasses.dataclass
class DesktopSettings:
    port:int=8088
    bind:str='127.0.0.1'
    trusted_hosts:str='127.0.0.1/32,::1/128'
    lab:bool=True
    visca:bool=False
    allow_store:bool=False
    auto_start:bool=True
    config_path:str=''

    @classmethod
    def load(cls,storage):
        path=pathlib.Path(storage)/'desktop-settings.json'
        data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        return cls(**{k:v for k,v in data.items() if k in cls.__dataclass_fields__})

    def prepare(self,storage):
        if type(self.port) is not int or not 1024<=self.port<=65535:raise ValueError('Port must be 1024 through 65535.')
        if ipaddress.ip_address(self.bind).version!=4:raise ValueError('Use an IPv4 listen address.')
        for name in ('lab','visca','allow_store','auto_start'):
            if type(getattr(self,name)) is not bool:raise ValueError('Invalid desktop option: '+name)
        if self.visca and not self.lab:raise ValueError('VISCA lab requires simulator mode.')
        if self.allow_store and not self.visca:raise ValueError('Remote store requires the VISCA lab.')
        source=pathlib.Path(self.config_path) if self.config_path else ROOT/'config.example.json'
        config=json.loads(source.read_text(encoding='utf-8'))
        config.update(bind=self.bind,port=self.port,trusted_hosts=[n.strip() for n in self.trusted_hosts.split(',') if n.strip()])
        validate_config(config)
        if self.lab and (not ipaddress.ip_address(self.bind).is_loopback or any(not c.get('simulator') for c in config['cameras'] if c.get('enabled',True))):
            raise ValueError('Simulator mode requires loopback and simulator camera entries.')
        if self.visca and config.get('pivotcam',{}).get('enabled'):raise ValueError('Disable the legacy VISCA lab when configured PIVOTCam endpoints are enabled.')
        storage=pathlib.Path(storage);storage.mkdir(parents=True,exist_ok=True)
        active=storage/'desktop-config.json';temporary=active.with_suffix('.tmp')
        temporary.write_text(json.dumps(config,indent=2),encoding='utf-8');temporary.replace(active)
        self.config_path=str(active)
        target=storage/'desktop-settings.json';temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps(dataclasses.asdict(self),indent=2),encoding='utf-8');temporary.replace(target)
        return active

    def service_args(self,storage):
        args=['--serve','--config',self.config_path,'--storage',str(storage),'--desktop-control']
        if self.lab:args.append('--lab')
        if self.visca:args.append('--visca-lab')
        if self.allow_store:args.append('--visca-allow-store')
        return args

    def web_url(self):return 'http://'+('127.0.0.1' if self.bind=='0.0.0.0' else self.bind)+':'+str(self.port)+'/'
