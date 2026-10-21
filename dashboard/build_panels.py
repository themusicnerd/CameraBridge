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
var cbHandover = false;
var cbTouchEnabled = false;
var cbNoticeUntil = 0;
function status(text) {
    if(String(text).indexOf('Feedback refreshed')==0 && new Date().getTime()<cbNoticeUntil)return;
    ogscript.rename('status', text);
}
function highlightPage(name) {
    var pages=CB_MANUFACTURER=='Panasonic'?['PTZ','Presets','Paint','TD1C','Config']:['Paint','Image','Exposure','OSD','Config'];
    for(var i=0;i<pages.length;i++)ogscript.setStyle('nav_'+pages[i].toLowerCase(),'bg#'+(pages[i]==name?'7433bd':'494f5b')+';fg#ffffff;bdr:none;');
}
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
var cbLinkUrl = '';
function refreshBridgeLink() {
    var url=String(params.getValue('bridge',0)).replace(/\/+$/,'')+'/';
    if(url==cbLinkUrl)return;
    var valid=/^https?:\/\/[A-Za-z0-9.\-:\[\]]+\/$/.test(url);
    var html=valid?'<html><p>Select this link to open setup:</p><a href="'+url+'"><font size="5" color="#80d9eb">'+url+'</font></a><p>Sign in in the browser to control cameras.</p></html>':'<html>Set a valid HTTP or HTTPS backend URL on Config.</html>';
    ogscript.setXML('bridge_launcher','<help id="open_bridge" left="0" top="0" width="180" height="56" name="Open setup" title="CameraBridge setup" popupwidth="600" popupheight="180" style="bg#49a8d8;fg#ffffff;size:16;"><![CDATA['+html+']]></help>');
    cbLinkUrl=url;
}
function selected() { return String(params.getValue('camera',0)); }
function send(action, data, callback) {
    if (!cbToken) { status('Sign in to control cameras. Lab feedback is read-only.'); return; }
    if (cbHandover && action!='stop') { status('Camera handover: waiting for previous stop'); return; }
    request('command',{camera:selected(),action:action,data:data || {}},callback);
}
function nextCamera() {
    if(cbCameras.length)cameraAt((cbIndex+1)%cbCameras.length);
}
function cameraAt(index) {
    if(index>=cbCameras.length || cbHandover)return;
    var old=selected(),target=cbCameras[index].id;
    if(old==target)return;
    cbEpoch++;cbPending={};cbEdit={};cbHandover=true;
    var finish=function(r){
        cbHandover=false;
        if(!r){status('Handover stopped: previous camera stop not confirmed');return;}
        cbIndex=index;params.setValue('camera',0,target);poll();
    };
    if(cbToken)request('command',{camera:old,action:'stop',data:{}},finish);
    else finish({readOnly:true});
}
function touchEnable() {
    if(!cbToken){status('Sign in on the Config page first');return;}
    cbTouchEnabled=!cbTouchEnabled;
    ogscript.rename('touch_enable',cbTouchEnabled?'Touch control ENABLED':'Touch control DISABLED');
    if(!cbTouchEnabled)stop();
}
function stop() { cbEpoch++; cbPending={}; send('stop',{},function(r){if(r)status('STOP sent — verify physical motion');}); }
function jog(pan,tilt,zoom,focus) {
    if(!cbTouchEnabled){status('Enable touch control before jogging');return;}
    var camera=selected(),epoch=cbEpoch;
    send('claim',{},function(r) {
        if(!r || epoch!=cbEpoch || camera!=selected())return;
        var speed=Number(params.getValue('speed',0));
        send('move',{pan:pan*speed,tilt:tilt*speed,zoom:zoom*speed,focus:focus*speed,generation:r.generation},null);
    });
}
function renamePreset() {
    send('label_preset',{number:Number(params.getValue('shot_number',0)),name:String(params.getValue('shot_name',0))},function(r){if(r)poll();});
}
function labBus(bus) {
    request('lab/ross/bus',{bus:bus,camera:selected()},function(r){if(r)poll();});
}
function changed(key) {
    if(cbUpdating)return;
    if(!cbToken){status('Sign in before adjustment');return;}
    cbPending[key]=Number(params.getValue(key,0)); cbEdit[key]=new Date().getTime();
}
function adjust(key,delta,low,high) {
    if(!cbToken){status('Sign in before adjustment');return;}
    var value=Number(params.getValue(key,0));
    params.setValue(key,0,Math.max(low,Math.min(high,value+delta)));
}
function preset(number) {
    var store=Number(params.getValue('store',0))==1;
    if(store && String(params.getValue('confirmation',0))!='OVERWRITE') {status('Type OVERWRITE to store; then select preset');return;}
    send('preset',{number:number,store:store,confirm:String(params.getValue('confirmation',0))},function(r){if(r)status(r.status);});
    params.setValue('store',0,0);params.setValue('confirmation',0,'');
}
function poll() {
    refreshBridgeLink();
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
        for(var n=0;n<6;n++) {
            var caption=n<cbCameras.length?String(cbCameras[n].name).split(' — ')[0]:'';
            ogscript.rename('camera_pick_'+n,n<cbCameras.length?'CAM '+(cbCameras[n].number || (n+1))+'\n'+caption.slice(0,12):'—');
            ogscript.setStyle('camera_pick_'+n,'bg#'+(n==cbIndex?'7433bd':'494f5b')+';fg#ffffff;bdr:none;size:15;');
        }
        ogscript.setStyle('connection','fg#'+(c.health=='online'||c.health=='simulated'?'8dca95':'d7bb8c')+';size:12;txt-align:west;');
        if(CB_MANUFACTURER=='Panasonic') {
            for(var n=1;n<=20;n++)ogscript.rename('shot_'+n,('0'+n).slice(-2)+'\n'+((c.preset_names||{})[String(n)] || 'Shot '+n));
            var ross=r.ross||{};
            ogscript.rename('ross_state','TouchDrive / Carbonite: '+(ross.state||'unverified')+' | Preset follow: '+(ross.preset_follow||'unverified'));
        }
        cbUpdating=true;
        try {
            for(var key in c.parameters) {
                var p=c.parameters[key];
                var value=p.value===null?'unknown':String(CB_MANUFACTURER=='Panasonic' && (key=='red_gain'||key=='blue_gain')?p.value-150:p.value);
                ogscript.rename('actual_'+key,value+' | '+p.confirmation+' | '+(p.age_seconds===null?'never read':Math.round(p.age_seconds)+'s'));
                if(p.confirmation=='confirmed' && !cbPending.hasOwnProperty(key) && (!cbEdit[key] || new Date().getTime()-cbEdit[key]>1000)) {
                    // DashBoard blocks local setValue while the parameter is read-only.
                    params.setAccess(key,1);params.setValue(key,0,p.value);
                }
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
    attrs={'handles':event} if event else {}
    if event=='onchange' and parent.tag=='param':attrs.update(oid=parent.get('oid'),element='0')
    n=node(parent,'ogscript',**attrs);n.text=text;return n
def task(parent,text):n=node(parent,'task',tasktype='ogscript');n.text=text
def label(parent,text,x,y,w=400,h=24,id=None):
    return node(parent,'label',name=text,left=x,top=y,width=w,height=h,style='txt-align:west;fg#dbe5ee;font:bold;',**({'id':id} if id else {}))
def button(parent,text,x,y,w,code,h=40,colour='2d4356'):
    n=node(parent,'button',name=text,left=x,top=y,width=w,height=h,buttontype='push',style='bg#'+colour+';fg#ffffff;font:bold;size:14;');task(n,code);return n
def field(parent,oid,x,y,w=130,h=32,widget=None):return node(parent,'param',oid=oid,left=x,top=y,width=w,height=h,showlabel='false',**({'widget':widget} if widget else {}))

def build(manufacturer,defs):
    from aura_layout import build as build_aura
    return build_aura(manufacturer,defs)

if __name__=='__main__':
    for manufacturer,defs in [('Panasonic',PANASONIC),('Marshall',MARSHALL_LAB)]:print(build(manufacturer,defs))
