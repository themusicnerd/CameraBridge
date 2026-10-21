"""Generate two native OGLML panels using documented DashBoard APIs."""
import pathlib
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from backend.protocol import PANASONIC
from backend.core import MARSHALL_LAB

HERE=pathlib.Path(__file__).resolve().parent
COMMON=r'''
var cbToken = '';
var cbUpdating = false;
var cbPending = {};
var cbEdit = {};
var cbCameras = [];
var cbIndex = 0;
var cbEpoch = 0;
var cbBusy = false;
var cbTick = 0;
var cbLastFeedback = 0;
function status(text) { ogscript.rename('status', text); }
function request(path, data, callback) {
    data.token = cbToken;
    var base = String(params.getValue('bridge', 0));
    ogscript.asyncPost(base + '/api/' + path, 'request=' + encodeURIComponent(JSON.stringify(data)), function(raw) {
        try {
            var result = JSON.parse(String(raw));
            if (result.error) { status(result.error); if (callback) callback(null); return; }
            if (callback) callback(result);
        } catch (e) { status('BRIDGE ERROR — feedback may be stale'); if (callback) callback(null); }
    });
}
function login() {
    var data = {username:String(params.getValue('username',0)),password:String(params.getValue('password',0))};
    params.setValue('password',0,'');
    request('login', data, function(r) { if(r) {cbToken = r.token; status('Authenticated ' + r.role); poll();} });
}
function selected() { return String(params.getValue('camera',0)); }
function send(action, data, callback) {
    if (!cbToken) { status('Sign in to control cameras. Lab feedback is read-only.'); return; }
    request('command',{camera:selected(),action:action,data:data || {}},callback);
}
function nextCamera() {
    var old = selected();
    if(cbToken) request('command',{camera:old,action:'stop',data:{}},null);
    cbEpoch++; cbPending = {}; cbEdit = {};
    if(cbCameras.length) { cbIndex=(cbIndex+1)%cbCameras.length; params.setValue('camera',0,cbCameras[cbIndex].id); }
    poll();
}
function stop() { cbEpoch++; cbPending={}; send('stop',{},function(r){if(r)status('STOP sent — verify physical motion');}); }
function jog(pan,tilt,zoom,focus) {
    var camera=selected(),epoch=cbEpoch;
    send('claim',{},function(r) {
        if(!r || epoch!=cbEpoch || camera!=selected())return;
        var speed=Number(params.getValue('speed',0));
        send('move',{pan:pan*speed,tilt:tilt*speed,zoom:zoom*speed,focus:focus*speed,generation:r.generation},null);
    });
}
function changed(key) {
    if(cbUpdating)return;
    if(!cbToken){status('Sign in before adjustment');return;}
    cbPending[key]=Number(params.getValue(key,0)); cbEdit[key]=new Date().getTime();
}
function preset(number) {
    var store=Number(params.getValue('store',0))==1;
    if(store && String(params.getValue('confirmation',0))!='OVERWRITE') {status('Type OVERWRITE to store; then select preset');return;}
    send('preset',{number:number,store:store,confirm:String(params.getValue('confirmation',0))},function(r){if(r)status(r.status);});
    params.setValue('store',0,0);params.setValue('confirmation',0,'');
}
function poll() {
    if(cbBusy)return; cbBusy=true;
    var camera=selected(),epoch=cbEpoch;
    request('state',{},function(r){
        cbBusy=false; if(!r || epoch!=cbEpoch || camera!=selected())return;
        cbLastFeedback=new Date().getTime();cbCameras=[];
        for(var i=0;i<r.cameras.length;i++)if(r.cameras[i].manufacturer==CB_MANUFACTURER)cbCameras.push(r.cameras[i]);
        var c=null;for(var i=0;i<cbCameras.length;i++)if(cbCameras[i].id==camera){c=cbCameras[i];cbIndex=i;}
        if(!c){status('Camera ID not configured; use Next camera');return;}
        ogscript.rename('identity',c.name+' | '+c.model+' | input '+c.carbonite_input);
        ogscript.rename('connection',(c.simulator?'SIMULATOR | ':'HARDWARE | ')+c.health+' | '+(c.host || c.gateway || '')+' | '+(c.locked?'LOCKED':'Available'));
        cbUpdating=true;
        try {
            for(var key in c.parameters) {
                var p=c.parameters[key];
                var value=p.value===null?'unknown':String(p.value);
                ogscript.rename('actual_'+key,value+' | '+p.confirmation+' | '+(p.age_seconds===null?'never read':Math.round(p.age_seconds)+'s'));
                if(p.confirmation=='confirmed' && !cbPending.hasOwnProperty(key) && (!cbEdit[key] || new Date().getTime()-cbEdit[key]>1000))params.setValue(key,0,p.value);
                var enabled=!!cbToken && !c.locked && p.confirmation=='confirmed';
                if(p.dependency){var pair=p.dependency.split('=');var m=c.parameters[pair[0]];enabled=enabled && m && m.confirmation=='confirmed' && (','+pair[1]+',').indexOf(','+m.value+',')>=0;}
                if(CB_MANUFACTURER=='Marshall' && (key=='red_gain'||key=='blue_gain'))enabled=enabled && c.parameters.wb_mode.value==1;
                params.setAccess(key,enabled?1:0);
            }
        } finally {cbUpdating=false;}
        status('Feedback refreshed | '+(cbToken?'control authenticated':'read-only; sign in to control')+' | Ross positioner: UNVERIFIED');
    });
}
function tick() {
    cbTick++;
    if(cbToken)for(var key in cbPending){var value=cbPending[key];delete cbPending[key];send('write',{parameter:key,value:value},null);break;}
    if(cbTick%5==0)poll();
    if(cbLastFeedback && new Date().getTime()-cbLastFeedback>4000)status('STALE — no bridge feedback for '+Math.round((new Date().getTime()-cbLastFeedback)/1000)+'s');
}
'''

def node(parent,tag,**attributes):return ET.SubElement(parent,tag,{k:str(v) for k,v in attributes.items()})
def script(parent,text,event=None):
    n=node(parent,'ogscript',**({'handles':event} if event else {}));n.text=text;return n
def task(parent,text):n=node(parent,'task',tasktype='ogscript');n.text=text
def label(parent,text,x,y,w=400,h=24,id=None):
    return node(parent,'label',name=text,left=x,top=y,width=w,height=h,style='txt-align:west;fg#dbe5ee;font:bold;',**({'id':id} if id else {}))
def button(parent,text,x,y,w,code,h=40,colour='2d4356'):
    n=node(parent,'button',name=text,left=x,top=y,width=w,height=h,buttontype='push',style='bg#'+colour+';fg#ffffff;font:bold;size:14;');task(n,code);return n
def field(parent,oid,x,y,w=130,h=32,widget=None):return node(parent,'param',oid=oid,left=x,top=y,width=w,height=h,showlabel='false',**({'widget':widget} if widget else {}))

def build(manufacturer,defs):
    root=ET.Element('abs',{'contexttype':'opengear','id':'_top','name':'CameraBridge '+manufacturer,'width':'1280','height':'880','gridsize':'10','keepalive':'false','style':'bg#141d26;fg#e3edf5;size:14;'})
    api=node(root,'api');api.text="var CB_MANUFACTURER = '"+manufacturer+"';\n"+COMMON
    meta=node(root,'meta');params=node(meta,'params')
    for oid,name,value,widget,access in [('bridge','Backend URL','http://127.0.0.1:8088',3,1),('username','Username','',3,1),('password','Password','',4,1),('camera','Camera ID','pana1' if manufacturer=='Panasonic' else 'marshall1',3,0),('confirmation','Type OVERWRITE','',3,1)]:
        node(params,'param',oid=oid,name=name,type='STRING',value=value,widget=widget,access=access,maxlength=256)
    for oid,name,low,high,value in [('speed','Jog speed',1,49,12),('store','Store armed: 0 recall / 1 store',0,1,0)]:
        node(params,'param',oid=oid,name=name,type='INT32',value=value,access=1,constrainttype='INT_RANGE',constraint=f'{low};{high};')
    for key,p in defs.items():
        n=node(params,'param',oid=key,name=p.label,type='INT32',value=p.low,access=0)
        if p.allowed:
            n.set('constrainttype','INT_CHOICE')
            for v in p.allowed:node(n,'constraint',key=v).text=str(v)
        else:n.set('constrainttype','INT_RANGE');n.set('constraint',f'{p.low};{p.high};')
    timer=node(meta,'timer',id='bridge_tick',rate=200,autostart='true')
    t=node(meta,'timertask',timerid='bridge_tick',tasktype='ogscript');t.text='tick();'
    script(root,'poll();','onload')
    script(root,"if(cbToken)request('command',{camera:selected(),action:'stop',data:{}},null);",'onclose')
    label(root,'CAMERABRIDGE / '+manufacturer.upper(),20,12,700,35)
    label(root,'Native DashBoard control · '+('AW-HE130' if manufacturer=='Panasonic' else 'CV226 / CV228 LAB — serial protocol pending'),20,48,1140)
    label(root,'Bridge',20,86,65);field(root,'bridge',85,80,280)
    label(root,'User',380,86,45);field(root,'username',425,80,140)
    label(root,'Password',580,86,85);field(root,'password',665,80,160)
    button(root,'Sign in',835,80,110,'login();',34)
    button(root,'Sign out',955,80,110,"stop();cbToken='';status('Signed out');",34)
    label(root,'Starting…',20,120,1230,28,'status')
    label(root,'Camera identification pending',20,154,1230,30,'identity')
    label(root,'Unknown',20,188,1230,28,'connection')
    field(root,'camera',20,228,160);button(root,'Next camera',190,224,170,'nextCamera();')
    button(root,'STOP ALL AXES',380,224,220,'stop();',44,'923e3e')
    button(root,'Refresh feedback',620,224,190,'poll();')
    button(root,'Lock',830,224,110,"send('lock',{value:true},null);")
    button(root,'Unlock',950,224,110,"send('lock',{value:false},null);")
    left=node(root,'abs',left=20,top=285,width=370,height=545,style='bg#1c2935;')
    paint=node(root,'abs',left=410,top=285,width=850,height=545,style='bg#1c2935;')
    label(paint,'PAINT / confirmed value · state · age',16,10,800)
    # Two compact columns; draft widgets never constitute confirmed camera feedback.
    keys=list(defs)
    for i,key in enumerate(keys):
        p=defs[key];col=i//8;row=i%8;x=16+col*420;y=45+row*61
        label(paint,p.label,x,y,405,18)
        ui=field(paint,key,x,y+19,290,25,3);script(ui,f"changed('{key}');",'onchange')
        entry=field(paint,key,x+300,y+19,92,25,6);script(entry,f"changed('{key}');",'onchange')
        feedback=label(paint,'unknown',x,y+44,400,17,'actual_'+key)
        feedback.set('style','fg#83cfc2;size:11;txt-align:west;')
    if manufacturer=='Panasonic':
        label(left,'PTZ · press to jog, release to stop',14,8,345)
        label(left,'Speed',14,40,60);field(left,'speed',80,36,270,32,3)
        for text,x,y,axes in [('↖',18,85,(-1,1,0,0)),('UP',126,85,(0,1,0,0)),('↗',234,85,(1,1,0,0)),('LEFT',18,132,(-1,0,0,0)),('RIGHT',234,132,(1,0,0,0)),('↙',18,179,(-1,-1,0,0)),('DOWN',126,179,(0,-1,0,0)),('↘',234,179,(1,-1,0,0)),('WIDE',18,231,(0,0,-1,0)),('TELE',126,231,(0,0,1,0)),('NEAR',18,279,(0,0,0,-1)),('FAR',126,279,(0,0,0,1))]:
            b=node(left,'button',name=text,left=x,top=y,width=98,height=40,style='bg#2d4356;fg#ffffff;font:bold;')
            script(b,'jog('+','.join(map(str,axes))+');','onmousedown')
            script(b,'stop();','onmouseup');script(b,'stop();','onmouseexit')
        button(left,'STOP',126,132,98,'stop();',40,'923e3e')
        label(left,'0.9s motion watchdog · tap again to continue',14,324,345,28)
        label(left,'PTZ PRESETS 1–20',14,360,345)
        for i in range(20):button(left,str(i+1),14+(i%5)*68,392+(i//5)*34,62,f'preset({i+1});',30)
        # Storage confirmation lives outside PTZ container to avoid cramped hit targets.
        label(root,'Store armed (0 recall / 1 store)',20,835,270,24);field(root,'store',285,835,60,24,6)
        label(root,'Type OVERWRITE',365,835,160,24);field(root,'confirmation',535,835,180,24)
    else:
        label(left,'FIXED CAMERA / NO MECHANICAL PTZ',12,10,350)
        label(left,'RS485 address: 1 · gateway: LAB',12,42,350)
        label(left,'Firmware: unknown · feedback: simulated',12,73,350)
        label(left,'OSD NAVIGATION — simulator only',12,125,350)
        for key,text,x,y in [('menu','MENU',126,175),('up','UP',126,222),('left','LEFT',18,269),('enter','ENTER',126,269),('right','RIGHT',234,269),('down','DOWN',126,316),('back','BACK',126,363)]:button(left,text,x,y,98,"send('osd',{key:'"+key+"'},function(r){if(r)status(r.status);});")
        label(left,'Direct serial commands are disabled.',12,430,350)
        label(left,'Lab ranges do not certify wire support.',12,463,350)
    path=HERE/('SW-'+manufacturer+'-Camera-Control.grid')
    ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path

if __name__=='__main__':
    for manufacturer,defs in [('Panasonic',PANASONIC),('Marshall',MARSHALL_LAB)]:print(build(manufacturer,defs))
