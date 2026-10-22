// Shared native camera setup. Passwords are cleared before each HTTP request.
var U={token:'',role:'',config:null,revision:'',index:0,editing:'',maker:'',switching:false};
var U_PROFILES=['panasonic','sony-sdk','marshall-CV226','marshall-CV228'].concat(__PANASONIC_PROFILES__);
function uValue(key){return params.getValue('setup_'+key,0);}
function uSet(key,value){params.setValue('setup_'+key,0,value);}
function uStatus(text){ogscript.rename('unified_status',String(text));}
function uRequest(path,data,callback){
    data.token=U.token;
    ogscript.asyncPost(String(params.getValue('bridge',0)).replace(/\/+$/,'')+'/api/'+path,'request='+encodeURIComponent(JSON.stringify(data)),function(raw){
        var r;try{r=JSON.parse(String(raw));}
        catch(e){uStatus('Cannot read CameraBridge response. Check the connection.');if(callback)callback(null);return;}
        if(!r){if(path!='state')uStatus('No reply received. Check the connection.');if(callback)callback(null);return;}
        if(r.error){uStatus(r.error);if(callback)callback(null);return;}
        if(callback)try{callback(r);}catch(e){uStatus('Panel update failed: '+String(e).slice(0,160));}
    });
}
function uLogin(){
    var data={username:String(params.getValue('username',0)),password:String(params.getValue('password',0))};
    params.setValue('password',0,'');
    uRequest('login',data,function(r){if(!r)return;U.token=r.token;U.role=r.role;uStatus('Signed in as '+r.role);uLoad();});
}
function uLeave(callback){
    if(U.switching){uStatus('Wait for the previous camera to stop.');return;}
    if(!U.maker){callback();return;}
    U.switching=true;
    U_PANELS[U.maker].leave(function(ok){U.switching=false;if(ok){U.maker='';callback();}else uStatus('Previous camera stop failed. Check CameraBridge before changing cameras.');});
}
function uSetup(){uLeave(function(){ogscript.reveal('unified_setup');});}
function uLogout(){uLeave(function(){uRequest('logout',{},function(){U.token='';U.role='';uStatus('Signed out');});ogscript.reveal('unified_setup');});}
function uLoad(){
    if(!U.token){uStatus('Sign in to load camera setup.');return;}
    if(U.role!='admin'){uStatus('Operator signed in. Administrator access is required to change camera setup.');uLive();return;}
    uRequest('setup',{operation:'load'},function(r){if(!r)return;U.config=r.configuration;U.revision=r.revision;U.index=Math.min(U.index,Math.max(0,U.config.cameras.length-1));uBridgeRead();uRoster();uStatus(r.pending?'Loaded saved setup. Apply it to update the running service.':'Loaded running camera setup.');});
}
function uLive(){uRequest('state',{},function(r){if(!r)return;U.config={cameras:r.cameras};uRoster();});}
function uRoster(){
    var cameras=U.config?U.config.cameras:[];
    for(var n=0;n<8;n++){
        var i=Math.floor(U.index/8)*8+n,c=cameras[i];
        ogscript.rename('roster_'+n,c?'CAM '+c.number+'  '+c.name+'\n'+c.manufacturer+' '+c.model+(c.enabled===false?' / disabled':''):'-');
        ogscript.setStyle('roster_'+n,'bg#'+(i==U.index?'7433bd':'494f5b')+';fg#ffffff;size:16;');
    }
    var c=cameras[U.index];ogscript.rename('setup_selected',c?'Selected: CAM '+c.number+' / '+c.name:'No configured cameras');
}
function uPick(slot){if(!U.config)return;var index=Math.floor(U.index/8)*8+slot;if(index>=U.config.cameras.length)return;U.index=index;uEdit();uRoster();}
function uListPage(delta){if(!U.config||!U.config.cameras.length)return;U.index=(Math.floor(U.index/8)*8+delta*8+Math.ceil(U.config.cameras.length/8)*8)%(Math.ceil(U.config.cameras.length/8)*8);uRoster();}
function uProfile(){
    var p=U_PROFILES[Number(uValue('profile'))];
    if(p.indexOf('marshall-CV')==0){uSet('pivot',0);uSet('enabled',0);}
    ogscript.rename('setup_profile_help',p=='sony-sdk'?'Sony: save the camera, then set access on the Camera access page.':p.indexOf('marshall-CV')==0?'Marshall hardware control is pending. Save this profile disabled.':p=='marshall-lab'?'Marshall simulator only. No serial packets are sent.':'Panasonic CGI compatibility profile. HE2: digital PTZ, shots 1–9, no focus. Unsupported controls stay read-only. HTTP authentication is not implemented.');
}
function uNew(){
    U.editing='';var used={},number=1;
    if(U.config)for(var i=0;i<U.config.cameras.length;i++)used[U.config.cameras[i].number]=true;
    while(used[number]&&number<255)number++;
    var defaults={name:'Camera '+number,profile:0,host:'',port:80,number:number,input:number,enabled:1,pivot:1,store:0,tally:1,address:Math.min(number,126),remove:'',access_user:'',access_password:'',fingerprint:'',terms:0};
    for(var key in defaults)uSet(key,defaults[key]);uProfile();uStatus('New camera. Save the camera, then apply the saved setup.');
}
function uEdit(){
    if(!U.config||!U.config.cameras[U.index])return;var c=U.config.cameras[U.index];U.editing=c.id;
    var p=c.driver=='panasonic'?(c.simulator?'panasonic-sim':c.model=='AW-HE130'?'panasonic':'panasonic:'+c.model):c.driver=='marshall-pending'?'marshall-'+c.model:c.driver;
    var values={name:c.name,profile:Math.max(0,U_PROFILES.indexOf(p)),host:c.host||'',port:c.port||80,number:c.number,input:c.carbonite_input,enabled:c.enabled===false?0:1,pivot:c.pivotcam?1:0,store:c.allow_store?1:0,tally:c.tally_enabled===false?0:1,address:c.tally_address===undefined?Math.min(c.carbonite_input,126):c.tally_address,remove:'',access_user:'',access_password:'',fingerprint:'',terms:0};
    for(var key in values)uSet(key,values[key]);uProfile();uStatus('Editing '+c.name+'. Access passwords are not read back.');
}
function uSave(){
    if(U.role!='admin'||!U.config){uStatus('Sign in as administrator, then load the camera list.');return;}
    var p=U_PROFILES[Number(uValue('profile'))],old=null;
    for(var i=0;i<U.config.cameras.length;i++)if(U.config.cameras[i].id==U.editing)old=U.config.cameras[i];
    var c={};if(old)for(var key in old)c[key]=old[key];
    c.number=Number(uValue('number'));c.id=U.editing||'camera_'+c.number;
    c.name=String(uValue('name')).replace(/^\s+|\s+$/g,'');
    if(!c.name){uStatus('Enter a camera name.');return;}
    c.driver=p.indexOf('panasonic')==0?'panasonic':p.indexOf('marshall-CV')==0?'marshall-pending':p;
    c.manufacturer=p=='sony-sdk'?'Sony':p.indexOf('marshall')==0?'Marshall':'Panasonic';
    c.model=p=='sony-sdk'?'PXW-Z200':p=='marshall-CV226'?'CV226':c.manufacturer=='Marshall'?'CV228':p.indexOf('panasonic:')==0?p.substring(10):'AW-HE130';
    c.host=String(uValue('host')).replace(/^\s+|\s+$/g,'');c.port=Number(uValue('port'));c.carbonite_input=Number(uValue('input'));
    c.simulator=p=='panasonic-sim'||p=='marshall-lab';c.enabled=Number(uValue('enabled'))==1;c.pivotcam=Number(uValue('pivot'))==1;
    c.allow_store=Number(uValue('store'))==1;c.tally_enabled=Number(uValue('tally'))==1;c.tally_address=Number(uValue('address'));
    if(c.driver=='marshall-lab'){c.gateway='LAB ONLY';c.address=1;}
    uRequest('setup',{operation:'save',revision:U.revision,previous:U.editing,camera:c},function(r){if(!r)return;U.config=r.configuration;U.revision=r.revision;U.editing=c.id;for(var i=0;i<U.config.cameras.length;i++)if(U.config.cameras[i].id==c.id)U.index=i;uRoster();uStatus(r.status);});
}
function uRemove(){
    if(!U.editing){uStatus('Select a saved camera first.');return;}
    var confirmation=String(uValue('remove'));uSet('remove','');
    uRequest('setup',{operation:'remove',revision:U.revision,camera:U.editing,confirmation:confirmation},function(r){if(!r)return;U.config=r.configuration;U.revision=r.revision;U.index=0;uNew();uRoster();uStatus(r.status);});
}
function uApply(){uLeave(function(){uRequest('setup',{operation:'apply',revision:U.revision},function(r){if(r)uStatus(r.status);});});}
function uControl(){
    if(!U.config||!U.config.cameras[U.index]){uStatus('Load the list and select a camera first.');return;}
    var c=U.config.cameras[U.index];
    uRequest('state',{},function(r){if(!r)return;var found=false,live=null;for(var i=0;i<r.cameras.length;i++)if(r.cameras[i].id==c.id){found=true;live=r.cameras[i];}
        if(!found){uStatus('Camera is not running. Enable it and apply the saved setup first.');return;}
        var keys=['host','port','driver','manufacturer','model','number','carbonite_input','enabled','simulator'];
        for(var k=0;k<keys.length;k++)if(String(c[keys[k]])!=String(live[keys[k]])){uStatus('Camera setup differs from the running camera. Apply saved setup, then reload the list.');return;}
        uLeave(function(){U.maker=c.manufacturer;U_PANELS[U.maker].enter(U.token,c.id);ogscript.reveal('unified_'+U.maker);uStatus('Controlling CAM '+c.number+' / '+c.name);});
    });
}
function uFingerprint(){
    if(U_PROFILES[Number(uValue('profile'))]!='sony-sdk'){uStatus('SSH access applies to the Sony SDK profile.');return;}
    uRequest('sony/fingerprint',{host:String(uValue('host'))},function(r){if(r){uSet('fingerprint',r.fingerprint);uStatus('Compare the fingerprint with the camera identity before saving access.');}});
}
function uSaveAccess(){
    var data={camera:U.editing,username:String(uValue('access_user')),password:String(uValue('access_password')),fingerprint:String(uValue('fingerprint')),acknowledge_terms:Number(uValue('terms'))==1};
    uSet('access_password','');
    if(!U.editing||U_PROFILES[Number(uValue('profile'))]!='sony-sdk'){uStatus('Save or select a Sony camera first.');return;}
    uRequest('sony/credentials',data,function(r){if(r)uStatus(r.status);});
}
function uTick(){if(U.maker&&!U.switching)U_PANELS[U.maker].run('tick();');}
function uClose(){params.setValue('password',0,'');uSet('access_password','');if(U.maker)U_PANELS[U.maker].leave(function(){});}
function uBridgeRead(){
    var p=U.config.pivotcam||{},t=U.config.tally||{};
    var fields={bridge_pivot:p.enabled?1:0,bridge_bind:p.bind||'127.0.0.1',bridge_controller:p.controller||'192.168.96.123',bridge_first:(p.base_port===undefined?19010:p.base_port)+1,bridge_tally:t.enabled?1:0,bridge_tally_bind:t.bind||'127.0.0.1',bridge_tally_source:t.source||'192.168.96.123',bridge_tally_port:t.port||5727,bridge_program:t.program_tally===1?0:1,bridge_offset:(t.address_offset||0)+1};
    for(var key in fields)uSet(key,fields[key]);
}
function uBridgeSave(){
    if(U.role!='admin'||!U.config){uStatus('Sign in as administrator, then load the camera list.');return;}
    var p={},t={},key;for(key in (U.config.pivotcam||{}))p[key]=U.config.pivotcam[key];for(key in (U.config.tally||{}))t[key]=U.config.tally[key];
    p.enabled=Number(uValue('bridge_pivot'))==1;p.bind=String(uValue('bridge_bind'));p.controller=String(uValue('bridge_controller'));p.base_port=Number(uValue('bridge_first'))-1;
    t.enabled=Number(uValue('bridge_tally'))==1;t.bind=String(uValue('bridge_tally_bind'));t.source=String(uValue('bridge_tally_source'));t.port=Number(uValue('bridge_tally_port'));t.program_tally=Number(uValue('bridge_program'))+1;t.address_offset=Number(uValue('bridge_offset'))-1;
    uRequest('setup',{operation:'bridge',revision:U.revision,pivotcam:p,tally:t},function(r){if(r){U.config=r.configuration;U.revision=r.revision;uStatus(r.status);}});
}
