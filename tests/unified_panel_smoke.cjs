/* Executes generated ogScript with strict native-API fixtures; not a Rhino/UI test. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const xml=fs.readFileSync(require('node:path').join(__dirname,'../dashboard/CameraBridge.grid'),'utf8');
const decode=s=>s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&amp;/g,'&');
const ids=new Set([...xml.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]));
const values={},access={},labels={},commands=[],pages=[],requests=[];
for(const m of xml.matchAll(/<param\b([^>]+)>?/g)){
 const attrs=Object.fromEntries([...m[1].matchAll(/(\w+)="([^"]*)"/g)].map(x=>[x[1],decode(x[2])]));
 if(attrs.value!==undefined){values[attrs.oid]=attrs.type==='INT32'?Number(attrs.value):attrs.value;access[attrs.oid]=Number(attrs.access);}
}
const config={cameras:[{id:'pana1',number:1,name:'Panasonic',manufacturer:'Panasonic',model:'AW-HE130',driver:'panasonic',host:'192.168.96.20',carbonite_input:1},
 {id:'sony2',number:2,name:'Sony',manufacturer:'Sony',model:'PXW-Z200',driver:'sony-sdk',host:'192.168.96.21',carbonite_input:2}]};
let revision='r1',failStop=false;
const state={cameras:config.cameras.map(c=>({...c,health:'online',locked:false,tally:{enabled:true,status:'off'},parameters:{wb_mode:{label:'White balance'},iris:{value:1300,confirmation:'confirmed',age_seconds:0,low:0,high:65535,supported:true,writable:true}}}))};
state.cameras[0].capabilities={gain_display_divisor:5};
state.cameras[0].parameters.detail={value:2,confirmation:'confirmed',age_seconds:0,low:0,high:2,writable:true};
state.cameras[0].parameters.red_gain={value:150,confirmation:'confirmed',age_seconds:0,low:0,high:300,writable:true,display_divisor:5};
const ctx=vm.createContext({JSON,Date,Math,String,Number,encodeURIComponent,
 params:{replaceConstraint:(oid,id)=>{assert.ok(xml.includes('id="'+id+'"'));},getValue:k=>values[k],setValue:(k,i,v)=>{assert.equal(access[k],1,'locked parameter '+k);values[k]=v;},setAccess:(k,v)=>{access[k]=v;},getParam:k=>({replaceConstraint:r=>assert.ok(values[k]!==undefined)})},
 ogscript:{rename:(id,text)=>{assert.ok(ids.has(id),'unknown label '+id);labels[id]=text;},setStyle:id=>assert.ok(ids.has(id),'unknown style '+id),
 reveal:id=>{assert.ok(ids.has(id),'unknown page '+id);pages.push(id);},hide:id=>{assert.ok(ids.has(id),'unknown popup '+id);},setXML:id=>assert.ok(ids.has(id)),
 asyncPost:(url,body,callback)=>{const d=JSON.parse(decodeURIComponent(body.slice(8)));requests.push({url,data:d});const path=url.split('/api/')[1];let result;
  if(path==='login')result={token:'admin-token',role:'admin'};
  else if(path==='state')result=state;
  else if(path==='setup'){
   if(d.operation==='save'){const at=config.cameras.findIndex(c=>c.id===d.previous);if(at<0)config.cameras.push(d.camera);else config.cameras[at]=d.camera;revision+='x';}
   result={configuration:config,revision,status:'Saved'};
  }else if(path==='command'){commands.push(d);result=failStop&&d.action==='stop'?{error:'Stop failed'}:{generation:1,status:'OK'};}
  else if(path==='logout')result={status:'signed out'};
  else throw Error('unexpected endpoint '+path);
  callback(JSON.stringify(result));
 }}});
new vm.Script(decode(xml.match(/<api>([\s\S]*?)<\/api>/)[1])).runInContext(ctx);
for(const m of xml.matchAll(/<(?:task|ogscript|timertask)\b[^>]*>([\s\S]*?)<\/(?:task|ogscript|timertask)>/g))new vm.Script(decode(m[1]));
const run=s=>vm.runInContext(s,ctx);
run("uNew();params.setValue('username',0,'admin');params.setValue('password',0,'password');uLogin();");
assert.equal(values.password,'');assert.match(labels.unified_status,/Loaded/);
run('uPick(0);uControl();');assert.equal(pages.at(-1),'unified_Panasonic');assert.equal(values.panasonic_iris,1300);
run("CB_Panasonic.run('touchEnable();jog(1,0,0,0);');");assert.ok(commands.some(c=>c.camera==='pana1'&&c.action==='move'));
failStop=true;run('uSetup();');assert.equal(pages.at(-1),'unified_Panasonic');assert.match(labels.unified_status,/stop failed/);
failStop=false;run('uSetup();');assert.equal(pages.at(-1),'unified_setup');
const count=commands.length;run("CB_Panasonic.run('jog(1,0,0,0);');");assert.equal(commands.length,count,'inactive panel cannot move');
run('uPick(1);uControl();');assert.equal(pages.at(-1),'unified_Sony');assert.equal(values.sony_camera,'sony2');
run('uSetup();uNew();uSet("number",3);uSet("host","192.168.96.30");uSave();');
assert.equal(config.cameras.length,3);assert.equal(config.cameras.at(-1).tally_enabled,true);
assert.equal(config.cameras.at(-1).number,3);assert.equal(config.cameras.at(-1).id,'camera_3');
assert.equal(config.cameras[1].host,'192.168.96.21','other camera setup must remain intact');
run("U.index=0;U.config.cameras[0]=Object.assign({},U.config.cameras[0],{host:'192.168.96.99'});uControl();");
assert.match(labels.unified_status,/differs from the running camera/,'pending host changes cannot control the old camera');
run('uNew();uSet("profile",U_PROFILES.indexOf("panasonic-serial"));uProfile();uSet("host","192.0.2.44");uSet("port",2304);uSet("number",4);uSave();');
assert.equal(config.cameras.at(-1).driver,'panasonic-serial');
assert.equal(config.cameras.at(-1).model,'AK-HC1800G + AW-PH360N');
assert.equal(config.cameras.at(-1).port,2304);
assert.match(labels.setup_profile_help,/USR gateway/);
console.log('Unified generated panel: scripts parse, scoped feedback, login, camera handover, stop failure, inactive controls, camera setup passed.');
