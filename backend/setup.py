"""Revision-checked camera roster edits for native DashBoard clients."""
import copy
import hashlib
import json


def roster(server, data):
    # Caller must check administrator role before entering this function.
    from .server import validate_config
    target = server.engine.storage / 'config.pending.json'
    with server.setup_lock:
        configuration = json.loads(target.read_text(encoding='utf-8')) if target.exists() else copy.deepcopy(server.engine.config)
        revision = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
        pending = configuration != server.engine.config
        operation = data.get('operation', 'load')
        if operation == 'load':
            return {'configuration': configuration, 'revision': revision, 'pending': pending}
        if data.get('revision') != revision:
            raise ValueError('Camera setup changed. Reload the list before saving.')
        if operation == 'autosave':
            configuration=validate_config(data['configuration'])
            if server.apply_configuration is None:raise ValueError('Live setup is unavailable in this service')
            server.apply_configuration(configuration)
            return {'configuration':configuration,'revision':hashlib.sha256(json.dumps(configuration,sort_keys=True).encode()).hexdigest(),'pending':False,'status':'Saved'}
        if operation == 'save':
            camera = data['camera']
            previous = data.get('previous', '')
            if previous and not any(c['id'] == previous for c in configuration['cameras']):
                raise ValueError('Camera no longer exists. Reload the list.')
            if previous and camera['id'] != previous:
                raise ValueError('Camera ID cannot change during an edit')
            if not previous and any(c['id'] == camera['id'] for c in configuration['cameras']):
                raise ValueError('Camera ID is already assigned')
            configuration['cameras'] = [camera if c['id'] == previous else c for c in configuration['cameras']]
            if not previous:
                configuration['cameras'].append(camera)
        elif operation == 'remove':
            if data.get('confirmation') != 'REMOVE':
                raise ValueError('Type REMOVE to remove this camera')
            if not any(c['id'] == data['camera'] for c in configuration['cameras']):
                raise ValueError('Camera no longer exists')
            configuration['cameras'] = [c for c in configuration['cameras'] if c['id'] != data['camera']]
        elif operation == 'bridge':
            for section in ('pivotcam', 'tally'):
                configuration[section] = data[section]
        elif operation != 'apply':
            raise ValueError('Unknown camera setup operation')
        configuration = validate_config(configuration)
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(configuration, indent=2), encoding='utf-8')
        temporary.replace(target)
        status = 'Camera setup saved. Select Apply saved setup to update the running service.'
        if operation == 'apply':
            if server.desktop_control:
                restart = server.engine.storage / 'desktop-restart.json'
                temporary = restart.with_suffix('.tmp')
                temporary.write_text('{"apply":true}', encoding='utf-8')
                temporary.replace(restart)
                status = 'Saved setup apply requested. Wait for the service to restart, then sign in again.'
            else:
                status = 'Saved setup is pending. Restart the console service with config.pending.json to apply it.'
        return {'configuration': configuration,
                'revision': hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest(),
                'pending': configuration != server.engine.config, 'status': status}
