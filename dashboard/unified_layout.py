"""Compose existing control pages with one authenticated camera setup page."""
import copy
import json
import xml.etree.ElementTree as ET
from build_panels import HERE, node, script
from backend.panasonic_models import MODELS,profile_id,label as model_label
from aura_layout import BG, BLUE, label, button, entry


def build():
    root = ET.Element('abs', contexttype='opengear', id='_top', name='CameraBridge',
                      virtualwidth='1366', virtualheight='872', width='1366', height='872',
                      gridaspect='false', style=f'bg#{BG};fg#e2e4e9;size:16;')
    api = node(root, 'api')
    meta = node(root, 'meta'); parameters = node(meta, 'params')
    for oid, value, widget in [('bridge', 'http://127.0.0.1:8088', 3), ('username', '', 3), ('password', '', 4)]:
        node(parameters, 'param', oid=oid, name=oid, type='STRING', value=value, access=1, widget=widget, maxlength=256)
    label(root, 'CameraBridge', 16, 12, 260, 44, size=26)
    button(root, 'Cameras / Setup', 300, 10, 240, 'uSetup();', 52, BLUE)
    button(root, 'Control Selected Camera', 560, 10, 320, 'uControl();', 52)
    label(root, 'Starting…', 900, 10, 450, 52, 'unified_status', size=14)
    tabs = node(root, 'tab', left=0, top=72, width=1366, height=800, tabposition='none')
    setup = node(tabs, 'abs', id='unified_setup', name='Cameras', width=1366, height=800)
    for oid, caption, x, width in [('bridge', 'Bridge URL', 16, 480), ('username', 'Admin / operator', 510, 260), ('password', 'Password', 784, 260)]:
        label(setup, caption, x, 6, width, 24); entry(setup, oid, x, 34, width, 48, None)
    button(setup, 'Sign in', 1060, 34, 132, 'uLogin();', 48, BLUE)
    button(setup, 'Sign out', 1202, 34, 148, 'uLogout();', 48)
    label(setup, 'Configured cameras', 16, 94, 450, 28, size=20)
    button(setup, 'Reload', 16, 130, 136, 'uLoad();', 48)
    button(setup, 'Previous', 164, 130, 136, 'uListPage(-1);', 48)
    button(setup, 'Next', 312, 130, 136, 'uListPage(1);', 48)
    for i in range(8):
        button(setup, '—', 16, 192+i*64, 432, f'uPick({i});', 56, id=f'roster_{i}')
    label(setup, 'No configured cameras', 16, 714, 432, 70, 'setup_selected', size=15)
    form_tabs = node(setup, 'tab', left=468, top=98, width=882, height=686, tabposition='none')
    form = node(form_tabs, 'abs', id='setup_camera_form', name='Camera setup', width=882, height=686)
    access = node(form_tabs, 'abs', id='setup_access_form', name='Camera access', width=882, height=686)
    bridge = node(form_tabs, 'abs', id='setup_bridge_form', name='Bridge / interop', width=882, height=628)
    # Form navigation is outside the hidden tabs.
    button(setup, 'Camera settings', 468, 96, 270, "ogscript.reveal('setup_camera_form');", 48, BLUE)
    button(setup, 'Camera access', 750, 96, 270, "ogscript.reveal('setup_access_form');", 48)
    button(setup, 'Bridge / interop', 1032, 96, 318, "ogscript.reveal('setup_bridge_form');", 48)
    # Tabs start below these buttons.
    form_tabs.set('top', '156'); form_tabs.set('height', '628')
    for child in (form, access): child.set('height', '628')

    def value(key, caption, x, y, width=410, default='', choices=None, low=None, high=None, password=False):
        attrs = dict(oid='setup_'+key, name=caption, access=1)
        if low is not None:
            attrs.update(type='INT32', value=default, constrainttype='INT_RANGE', constraint=f'{low};{high};', widget=5)
        elif choices is not None:
            attrs.update(type='INT32', value=default, constrainttype='INT_CHOICE', widget=7)
        else:
            attrs.update(type='STRING', value=default, widget=4 if password else 3, maxlength=1024)
        p = node(parameters, 'param', **attrs)
        if choices is not None:
            for i, name in enumerate(choices): node(p, 'constraint', key=i).text=name
        parent = bridge if key.startswith('bridge_') else access if key.startswith('access_') or key in ('fingerprint','terms') else form
        label(parent, caption, x, y, width, 26, size=15)
        entry(parent, 'setup_'+key, x, y+28, width, 48, None)

    value('name','Camera name',0,0,default='New camera')
    value('profile','Manufacturer / model',438,0,default=0,choices=['Panasonic AW-HE130','Sony PXW-Z200 / SDK','Marshall CV226','Marshall CV228']+[model_label(m) for m in MODELS if m!='AW-HE130'])
    listener=script(root, "uProfile();", 'onchange');listener.set('oid','setup_profile');listener.set('element','0')
    value('host','Camera IP / host',0,84)
    value('port','Camera port (Sony SDK uses its own transport)',438,84,default=80,low=1,high=65535)
    value('number','Camera number / PIVOTCam port = base + number',0,168,default=1,low=1,high=255)
    value('input','Carbonite input',438,168,default=1,low=1,high=255)
    for key,caption,x,y,default in [('enabled','Camera enabled',0,252,1),('pivot','PIVOTCam enabled',438,252,1),('store','Allow preset store',0,336,0),('tally','Camera tally enabled',438,336,1)]:
        value(key,caption,x,y,default=default,choices=['OFF','ON'])
    value('address','TSL tally address (input 1 defaults to address 1)',0,420,default=1,low=0,high=126)
    value('remove','Type REMOVE to remove the selected camera',438,420)
    label(form,'Select a camera profile.',0,502,870,42,'setup_profile_help',size=13)
    for text,x,width,code in [('New',0,112,'uNew();'),('Save',124,112,'uSave();'),('Remove',248,128,'uRemove();'),('Apply saved setup',390,280,'uApply();')]:
        button(form,text,x,554,width,code,60,BLUE if text=='Save' else '494f5b')
    label(access,'SONY CAMERA ACCESS',0,0,860,34,size=22)
    label(access,'Save the Sony camera on Camera settings first. Select it in the list.\nThe password is stored on the bridge host and is not read back.',0,44,860,62,size=16)
    value('access_user','Camera username',0,120)
    value('access_password','Camera password',438,120,password=True)
    value('fingerprint','Verified SSH fingerprint',0,218,848)
    button(access,'Read fingerprint',0,312,270,'uFingerprint();',56)
    label(access,'Compare this fingerprint with the camera identity before saving access.',288,312,560,56,size=15)
    value('terms','I have read and accept the Sony SDK terms',0,388,848,default=0,choices=['NO','YES'])
    button(access,'Save camera access',0,494,390,'uSaveAccess();',60,BLUE)
    label(access,'Sony SDK terms: support.d-imaging.sony.co.jp/app/sdk/licenseagreement_d/en-US.html\nPanasonic HTTP authentication and Marshall hardware access are not implemented.',0,566,860,58,size=13)
    value('bridge_pivot','PIVOTCam receiver',0,0,default=0,choices=['OFF','ON'])
    value('bridge_first','First camera TCP port (camera number 1)',438,0,default=19011,low=1025,high=65281)
    value('bridge_bind','PIVOTCam listen IP (this bridge host)',0,84,default='127.0.0.1')
    value('bridge_controller','Allowed Carbonite source IP',438,84,default='192.168.96.123')
    value('bridge_tally','TSL 3.1 tally receiver',0,168,default=0,choices=['OFF','ON'])
    value('bridge_tally_port','Tally UDP port',438,168,default=5727,low=1024,high=65535)
    value('bridge_tally_bind','Tally listen IP (this bridge host)',0,252,default='127.0.0.1')
    value('bridge_tally_source','Allowed tally sender IP',438,252,default='192.168.96.123')
    value('bridge_program','Program tally bit (Carbonite default: tally 2)',0,336,default=1,choices=['Tally 1','Tally 2'])
    value('bridge_offset','Input-to-TSL address offset',438,336,default=1,choices=['-1','0','+1'])
    label(bridge,'The listener IP must belong to the Windows/Linux bridge host.\nAllow these ports through its firewall. Save changes, then apply the saved setup.\nPer-camera tally addresses override the input-to-TSL address offset.',0,432,860,92,size=15)
    button(bridge,'Save bridge settings',0,554,390,'uBridgeSave();',60,BLUE)
    button(bridge,'Apply saved setup',414,554,390,'uApply();',60)

    wrappers=[]
    for maker in ('Panasonic','Marshall','Sony'):
        source=ET.parse(HERE/f'SW-{maker}-Camera-Control.grid').getroot()
        original_api=source.find('api').text
        # One login owns all camera pages. Retain lock and tally controls, but
        # replace the old per-manufacturer connection editor.
        config=source.find(".//abs[@id='page_config']")
        for e in list(config):
            if e.tag=='param' or (e.tag=='button' and e.get('name') in ('Sign in','Sign out')):
                config.remove(e)
            elif e.tag=='label' and e.get('name') in ('Bridge URL','Backend','Username','Password','CONNECTION / OPERATOR LOGIN'):
                config.remove(e)
        label(config,'Use Cameras / Setup for connection, camera setup, and shared sign-in.',20,20,1140,80,size=20)
        prefix=maker.lower()+'_'
        # A JavaScript facade namespaces parameter and element references, including
        # computed parameter names. Each existing control script retains its scope.
        wrapper=r'''
var CB_MAKER=(function(nativeParams,nativeScript){
    var prefix=PREFIX,active=false;
    var params={getValue:function(k,i){return nativeParams.getValue(k=='bridge'?'bridge':prefix+k,i);},
      setValue:function(k,i,v){nativeParams.setValue(prefix+k,i,v);},setAccess:function(k,v){nativeParams.setAccess(prefix+k,v);},
      getParam:function(k,i){return nativeParams.getParam(prefix+k,i);}};
    var ogscript={rename:function(k,v){nativeScript.rename(prefix+k,v);},setStyle:function(k,v){nativeScript.setStyle(prefix+k,v);},
      asyncPost:function(u,d,c){nativeScript.asyncPost(u,d,c);},
      setXML:function(k,xml){nativeScript.setXML(prefix+k,String(xml).replace(/\bid="([^"]+)"/g,'id="'+prefix+'$1"'));}};
    ORIGINAL
    var originalPoll=poll;
    poll=function(){
      if(active&&U.config){for(var i=0;i<U.config.cameras.length;i++)if(U.config.cameras[i].id==selected()){
        U.index=i;uRoster();var c=U.config.cameras[i];uStatus('Controlling CAM '+c.number+' / '+c.name);break;}}
      originalPoll();
    };
    var originalCameraAt=cameraAt;
    cameraAt=function(index){cbTouchEnabled=false;if(CB_MANUFACTURER!='Marshall')ogscript.rename('touch_enable','Touch control DISABLED');originalCameraAt(index);};
    var originalSend=send;
    send=function(action,data,callback){if(!active&&action!='stop'){status('Select this camera from Cameras / Setup.');return;}originalSend(action,data,callback);};
    return {run:function(code,source){return function(){return eval(code);}.call(source);},
      enter:function(token,cid){cbToken=token;cbTouchEnabled=false;cbEpoch++;cbPending={};cbEdit={};cbConstraints={};active=true;
        params.setAccess('camera',1);params.setValue('camera',0,cid);params.setAccess('camera',0);
        if(CB_MANUFACTURER!='Marshall')ogscript.rename('touch_enable','Touch control DISABLED');poll();},
      leave:function(callback){cbEpoch++;cbPending={};cbEdit={};cbTouchEnabled=false;active=false;
        if(!cbToken){callback(true);return;}request('command',{camera:selected(),action:'stop',data:{}},function(r){if(r){cbToken='';callback(true);}else callback(false);});}};
})(params,ogscript);
'''.replace('PREFIX',json.dumps(prefix)).replace('ORIGINAL',original_api).replace('CB_MAKER','CB_'+maker)
        wrappers.append(wrapper)
        for p in source.findall('./meta/params/param'):
            p=copy.deepcopy(p);p.set('oid',prefix+p.get('oid'));parameters.append(p)
        child=node(tabs,'abs',id='unified_'+maker,name=maker,width=1366,height=800)
        for element in list(source):
            if element.tag in ('api','meta'):continue
            if element.tag=='ogscript' and element.get('handles') in ('onload','onclose'):continue
            element=copy.deepcopy(element)
            for e in element.iter():
                for attr in ('id','oid','targetid'):
                    if e.get(attr):e.set(attr,prefix+e.get(attr))
                if e.tag in ('task','ogscript','timertask') and e.text:
                    e.text='CB_'+maker+'.run('+json.dumps(e.text)+',this);'
                if e.get('onchange'):
                    e.set('onchange','CB_'+maker+'.run('+json.dumps(e.get('onchange'))+',this);')
            child.append(element)
    node(meta,'timer',id='unified_tick',rate=200,autostart='true')
    node(meta,'timertask',timerid='unified_tick',tasktype='ogscript').text='uTick();'
    api.text='\n'.join(wrappers)+'\nvar U_PANELS={Panasonic:CB_Panasonic,Marshall:CB_Marshall,Sony:CB_Sony};\n'+(HERE/'unified.js').read_text(encoding='utf-8').replace('__PANASONIC_PROFILES__',json.dumps([profile_id(m) for m in MODELS if m!='AW-HE130']))
    script(root,"uNew();uStatus('Set the bridge URL and sign in.');",'onload')
    script(root,'uClose();','onclose')
    path=HERE/'CameraBridge.grid';ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path
