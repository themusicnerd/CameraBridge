"""Generate two native OGLML panels using documented DashBoard APIs."""
import pathlib
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from backend.protocol import PANASONIC
from backend.core import MARSHALL_LAB
from backend.sony import SONY

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
var cbConstraints = {};
var cbRanges = {};
var cbGainStep=1;
var cbCapabilities = {};
var cbPresetSpeeds = {};
var cbMotionFlight=false, cbMotionIntent=null, cbMotionHeld=null, cbMotionLast=0, cbMotionStop=false, cbMotionFull=false;
function status(text) {
    if(String(text).indexOf('Feedback refreshed')==0 && new Date().getTime()<cbNoticeUntil)return;
    ogscript.rename('status', text);
}
function highlightPage(name) {
    var pages=CB_MANUFACTURER=='Sony'?['Lens','Paint','Tally','Config']:CB_MANUFACTURER=='Panasonic'?['PTZ','Presets','Paint','TD1C','Config']:['Paint','Image','Exposure','OSD','Config'];
    for(var i=0;i<pages.length;i++)ogscript.setStyle('nav_'+pages[i].toLowerCase(),'bg#'+(pages[i]==name?'7433bd':'494f5b')+';fg#ffffff;bdr:none;');
}
function request(path, data, callback) {
    data.token = cbToken;
    var base = String(params.getValue('bridge', 0));
    ogscript.asyncPost(base + '/api/' + path, 'request=' + encodeURIComponent(JSON.stringify(data)), function(raw) {
        try {
            var result = JSON.parse(String(raw));
            if(!result){if(path!='state')status('No Command Reply; Check Feedback');if(callback)callback(null);return;}
            if (result.error) { status(result.error); if (callback) callback(null); return; }
            if (callback) callback(result);
        } catch (e) { cbNoticeUntil=new Date().getTime()+10000;status('Panel Error: '+String(e)); if (callback) callback(null); }
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
    cbEpoch++;cbPending={};cbEdit={};cbMotionHeld=null;cbMotionIntent=null;cbHandover=true;
    var finish=function(r){
        cbHandover=false;
        if(!r){status('Handover stopped: previous camera stop not confirmed');return;}
        cbIndex=index;params.setAccess('camera',1);params.setValue('camera',0,target);params.setAccess('camera',0);poll();
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
function pumpMotion() {
    if(cbMotionFlight || cbHandover)return;
    if(cbMotionStop) {
        cbMotionStop=false;var full=cbMotionFull;cbMotionFull=false;cbMotionFlight=true;
        request('command',{camera:selected(),action:'stop',data:{active_only:!full}},function(r){
            cbMotionFlight=false;
            if(!r){cbMotionIntent=null;cbMotionHeld=null;cbTouchEnabled=false;ogscript.rename('touch_enable','Touch control DISABLED');status('Stop failed; movement remains disabled');return;}
            pumpMotion();
        });return;
    }
    var intent=cbMotionIntent;if(!intent)return;cbMotionIntent=null;cbMotionFlight=true;
    request('command',{camera:intent.camera,action:'claim',data:{}},function(r){
        if(!r || intent.epoch!=cbEpoch || intent.camera!=selected() || cbMotionStop || cbMotionIntent){cbMotionFlight=false;pumpMotion();return;}
        var d=intent.axes;d.generation=r.generation;
        request('command',{camera:intent.camera,action:'move',data:d},function(result){
            cbMotionFlight=false;if(!result)cbMotionIntent=null;pumpMotion();
        });
    });
}
function release() {
    if(!cbToken)return;
    cbEpoch++;cbMotionIntent=null;cbMotionHeld=null;cbMotionStop=true;pumpMotion();
}
function stop() {
    if(!cbToken)return;
    cbEpoch++;cbPending={};cbMotionIntent=null;cbMotionHeld=null;cbMotionStop=true;cbMotionFull=true;pumpMotion();
}
function jog(pan,tilt,zoom,focus) {
    if(!cbTouchEnabled){status('Enable touch control before jogging');return;}
    if(!cbToken)return;
    var speed=Number(params.getValue('speed',0));
    cbMotionLast=new Date().getTime();
    cbMotionIntent={camera:selected(),epoch:cbEpoch,axes:{pan:pan*speed,tilt:tilt*speed,zoom:zoom*speed,focus:focus*speed}};
    cbMotionHeld=cbMotionIntent;pumpMotion();
}
function whiteBalance(mode) {
    if(cbCapabilities.pan_tilt_type=='digital' && mode>0)mode--;
    send('write',{parameter:'wb_mode',value:mode},function(r){if(r)poll();});
}
function oneShot() {
    send('white_balance_once',{},function(r){if(r){status('One Shot Sent; completion is not reported');poll();}});
}
function renamePreset() {
    var d={number:Number(params.getValue('shot_number',0)),name:String(params.getValue('shot_name',0))};
    if(cbCapabilities.preset_speed)d.speed=Number(params.getValue('recall_speed',0));
    send('label_preset',d,function(r){if(r)poll();});
}
function labBus(bus) {
    request('lab/ross/bus',{bus:bus,camera:selected()},function(r){if(r)poll();});
}
function changed(key) {
    if(cbUpdating)return;
    if(!cbToken){status('Sign in before adjustment');return;}
    var value=Number(params.getValue(key,0));
    if(key=='red_gain'||key=='blue_gain')value=Math.round(value/cbGainStep)*cbGainStep;
    cbPending[key]=value; cbEdit[key]=new Date().getTime();
}
function adjust(key,delta,low,high) {
    if(!cbToken){status('Sign in before adjustment');return;}
    if(cbRanges[key]){low=cbRanges[key][0];high=cbRanges[key][1];}
    var value=Number(params.getValue(key,0));
    if(key=='red_gain'||key=='blue_gain')delta*=cbGainStep;
    params.setValue(key,0,Math.max(low,Math.min(high,value+delta)));
}
function preset(number) {
    if(cbCapabilities.preset_max!==undefined && number>cbCapabilities.preset_max){status('Shot unavailable for this camera model');return;}
    var store=Number(params.getValue('store',0))==1;
    if(store && String(params.getValue('confirmation',0))!='OVERWRITE') {status('Type OVERWRITE to store; then select preset');return;}
    var d={number:number,store:store,confirm:String(params.getValue('confirmation',0))};
    if(cbCapabilities.preset_speed && (store || Number(params.getValue('use_saved_speed',0))==0))d.speed=Number(params.getValue('recall_speed',0));
    send('preset',d,function(r){if(r){status(r.status);poll();}});
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
        if(!c && cbCameras.length){c=cbCameras[0];cbIndex=0;cbEpoch++;cbPending={};cbTouchEnabled=false;params.setAccess('camera',1);params.setValue('camera',0,c.id);params.setAccess('camera',0);if(CB_MANUFACTURER!='Marshall')ogscript.rename('touch_enable','Touch control DISABLED');}
        if(!c){status('No enabled '+CB_MANUFACTURER+' cameras; add one in CameraBridge setup');return;}
        ogscript.rename('identity',c.name+' | '+c.model+' | input '+c.carbonite_input);
        ogscript.rename('connection',''+c.health+' | '+(c.host || c.gateway || '')+' | '+(c.locked?'LOCKED':'Available'));
        for(var n=0;n<6;n++) {
            var caption=n<cbCameras.length?String(cbCameras[n].name).split(' - ')[0]:'';
            ogscript.rename('camera_pick_'+n,n<cbCameras.length?'CAM '+(cbCameras[n].number || (n+1))+'\n'+caption.slice(0,12):'-');
            ogscript.setStyle('camera_pick_'+n,'bg#'+(n==cbIndex?'7433bd':'494f5b')+';fg#ffffff;bdr:none;size:15;');
        }
        ogscript.setStyle('connection','fg#'+(c.health=='online'||c.health=='simulated'?'8dca95':'d7bb8c')+';size:12;txt-align:west;');
        cbCapabilities=c.capabilities||{};cbGainStep=cbCapabilities.gain_display_divisor||1;
        if(CB_MANUFACTURER=='Panasonic') {
            cbPresetSpeeds=c.preset_speeds||{};
            ogscript.rename('paint_help','Auto ATW follows the scene. Manual A / B hold white balance and allow gain adjustment.');
            if(c.white_balance_once)ogscript.rename('awb_result','One Shot: '+c.white_balance_once.status+(c.white_balance_once.error?' | '+c.white_balance_once.error:' | completion not reported'));
            var active=c.active_preset||{};
            ogscript.rename('preset_feedback',active.number?'Shot '+active.number+' | Speed '+(active.speed||'Camera Default')+' | '+active.state:'No Shot Recalled');
            for(var n=1;n<=20;n++)ogscript.rename('shot_'+n,('0'+n).slice(-2)+'\n'+((c.preset_names||{})[String(n)] || 'Shot '+n)+(cbPresetSpeeds[String(n)]?' | S'+cbPresetSpeeds[String(n)]:''));
            var ross=r.ross||{};
            ogscript.rename('ross_state','TouchDrive / Carbonite: '+(ross.state||'not connected')+' | Preset follow: '+(ross.preset_follow||'not connected'));
        }
        cbUpdating=true;
        var tally=c.tally||{};
        if(CB_MANUFACTURER!='Marshall')ogscript.rename('tally_state','Tally: '+(tally.enabled?'enabled':'disabled')+' | '+(tally.status||'unknown')+(tally.error?' | '+tally.error:''));
        try {
            for(var key in c.parameters) {
                var p=c.parameters[key];cbRanges[key]=[p.low,p.high];
                try {
                if(CB_MANUFACTURER=='Panasonic' && (key=='red_gain'||key=='blue_gain') && cbConstraints[key]!='gain_'+cbGainStep){params.replaceConstraint(key,'gain_range_'+cbGainStep);cbConstraints[key]='gain_'+cbGainStep;}
                if((CB_MANUFACTURER=='Sony' && key!='shutter' && key!='zoom' && p.supported || CB_MANUFACTURER=='Panasonic' && key=='detail') && p.low<=p.high) {
                    var range=String(p.low)+';'+String(p.high)+';';
                    if(cbConstraints[key]!=range){params.setAccess(key,1);if(CB_MANUFACTURER=='Panasonic')params.replaceConstraint(key,'detail_range_'+p.high);else params.getParam(key,0).replaceConstraint(String(range));cbConstraints[key]=range;}
                }
                var value=p.value===null?'unknown':String(CB_MANUFACTURER=='Panasonic' && (key=='red_gain'||key=='blue_gain')?(p.value-150)/(p.display_divisor||1):p.value);
                if(CB_MANUFACTURER=='Panasonic' && key=='wb_mode'){var wbNames=cbCapabilities.pan_tilt_type=='digital'?{0:'Auto ATW',1:'Manual A',2:'Manual B',3:'Auto ATW',4:'3200K',5:'5600K'}:{0:'Auto ATW',2:'Manual A',3:'Manual B',4:'3200K',5:'5600K',9:'Variable'};value=wbNames[p.value]||value;}
                ogscript.rename('actual_'+key,value+' | '+p.confirmation+' | '+(p.age_seconds===null?'never read':Math.round(p.age_seconds)+'s'));
                if(p.confirmation=='confirmed' && !cbPending.hasOwnProperty(key) && (!cbEdit[key] || new Date().getTime()-cbEdit[key]>1000)) {
                    // DashBoard blocks local setValue while the parameter is read-only.
                    params.setAccess(key,1);params.setValue(key,0,CB_MANUFACTURER=='Sony' && (key=='shutter'||key=='zoom')?String(p.value):p.value);
                }
                var enabled=!!cbToken && !c.locked && p.confirmation=='confirmed' && p.writable!==false;
                if(p.dependency){var pair=p.dependency.split('=');var m=c.parameters[pair[0]];enabled=enabled && m && m.confirmation=='confirmed' && (','+pair[1]+',').indexOf(','+m.value+',')>=0;}
                if(CB_MANUFACTURER=='Marshall' && (key=='red_gain'||key=='blue_gain'))enabled=enabled && c.parameters.wb_mode.value==1;
                params.setAccess(key,enabled?1:0);
                } catch(panelError) { cbNoticeUntil=new Date().getTime()+10000;status('Panel '+key+': '+String(panelError)); }
            }
        } finally {cbUpdating=false;}
        status('Feedback refreshed | '+(cbToken?'control authenticated':'read-only; sign in to control'));
    });
}
function tick() {
    cbTick++;
    if(cbMotionHeld && !cbMotionFlight && !cbHandover && new Date().getTime()-cbMotionLast>=300){cbMotionIntent=cbMotionHeld;cbMotionLast=new Date().getTime();pumpMotion();}
    if(cbToken)for(var key in cbPending){var value=cbPending[key];delete cbPending[key];send('write',{parameter:key,value:value,snap:CB_MANUFACTURER=='Sony'},null);break;}
    if(cbTick%5==0)poll();
    if(cbLastFeedback && new Date().getTime()-cbLastFeedback>4000)status('STALE - no bridge feedback for '+Math.round((new Date().getTime()-cbLastFeedback)/1000)+'s');
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
    if manufacturer=='Sony':
        from sony_layout import build as build_sony
        return build_sony(defs)
    from aura_layout import build as build_aura
    return build_aura(manufacturer,defs)

if __name__=='__main__':
    from build_model_options import build as build_options
    build_options()
    for manufacturer,defs in [('Panasonic',PANASONIC),('Marshall',MARSHALL_LAB),('Sony',SONY)]:print(build(manufacturer,defs))
    from unified_layout import build as build_unified
    print(build_unified())
