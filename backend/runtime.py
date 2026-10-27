"""Camera and receiver lifecycle, separate from the authenticated HTTP session."""
import threading
import copy
from .core import Engine

class Runtime:
    @staticmethod
    def transport_settings(config):
        result=copy.deepcopy(config)
        result.pop('authentication_enabled',None)
        for camera in result['cameras']:
            for key in ('name','carbonite_input','tally_address','tally_enabled','tracking_output'):camera.pop(key,None)
        return result

    def update_metadata(self,config):
        if self.transport_settings(config)!=self.transport_settings(self.config):return False
        with self.engine.lock:
            self.config=config;self.engine.config=config
            for camera in config['cameras']:
                if camera['id'] in self.engine.cameras:
                    current=self.engine.cameras[camera['id']];current['config']=camera
                    enabled=camera.get('tally_enabled',True)
                    if enabled!=current['tally']['enabled']:current['tally'].update(enabled=enabled,status='unknown' if enabled else 'disabled')
        return True

    def __init__(self,config,storage,visca=False,allow_store=False):
        self.config=config;self.storage=storage;self.visca=visca;self.allow_store=allow_store
        self.engine=Engine(config,storage);self.listeners=[];self.simulators=[]

    def start_listener(self,listener):
        self.listeners.append(listener)
        threading.Thread(target=listener.serve_forever,daemon=True).start()

    def start(self):
        from .ross import PresetFollower,LabViscaServer,FixedCameraController,PivotCamServer
        from .tally import TallyServer
        from .simulator import server
        for c in self.config['cameras']:
            if c.get('simulator') and c.get('enabled',True) and c['driver']=='panasonic':
                sim=server(port=c['port']);self.simulators.append(sim)
                threading.Thread(target=sim.serve_forever,daemon=True).start()
        self.engine.start()
        tally=self.config.get('tally',{})
        if tally.get('enabled'):
            self.start_listener(TallyServer((tally.get('bind','127.0.0.1'),tally.get('port',5727)),self.engine,tally['source'],tally.get('address_offset',0),tally.get('program_tally',2)))
        if self.visca:
            if self.config.get('pivotcam',{}).get('enabled'):raise ValueError('Use PIVOTCam or the legacy test listener, not both')
            self.engine.ross_follower=PresetFollower(self.engine)
            for c in self.config['cameras']:
                if c.get('enabled',True) and c['manufacturer']=='Panasonic':
                    self.start_listener(LabViscaServer(('127.0.0.1',19010+c['number']),self.engine,c['id'],self.engine.ross_follower,self.allow_store))
        pivot=self.config.get('pivotcam',{})
        if pivot.get('enabled'):
            for c in self.config['cameras']:
                if c.get('enabled',True) and c.get('pivotcam'):
                    follower=FixedCameraController(self.engine,c['id'])
                    self.start_listener(PivotCamServer((pivot.get('bind','127.0.0.1'),pivot.get('base_port',19010)+c['number']),self.engine,c['id'],follower,pivot['controller'],c.get('allow_store',False)))

    def close(self):
        for listener in self.listeners:
            listener.shutdown();listener.server_close()
        self.listeners=[]
        self.engine.close()
        for simulator in self.simulators:
            simulator.shutdown();simulator.server_close()
        self.simulators=[]
