const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const xml=fs.readFileSync(require('node:path').join(__dirname,'../dashboard/SW-Panasonic-Camera-Control.grid'),'utf8');
const decode=s=>s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&amp;/g,'&');
const ids=new Set([...xml.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]));
const values={camera:'p1',bridge:'http://bridge',zoom:2000,speed:12,shot_number:1,number_value:''},popups=[],hidden=[],labels={};
const context=vm.createContext({JSON,Date,Math,String,Number,encodeURIComponent,
 params:{getValue:k=>values[k],setAccess:()=>{},setValue:(k,i,v)=>{values[k]=v;if(k==='zoom')vm.runInContext("changed('zoom')",context);}},
 ogscript:{rename:(k,t)=>{assert.ok(ids.has(k),'missing label '+k);labels[k]=t;},reveal:k=>{assert.ok(ids.has(k));popups.push(k);},hide:k=>hidden.push(k),asyncPost:()=>{throw Error('Number entry must stage before sending');}}});
new vm.Script(decode(xml.match(/<api>([\s\S]*?)<\/api>/)[1])).runInContext(context);
const run=code=>vm.runInContext(code,context);
run("cbToken='token';cbRanges.zoom=[1365,4095];cbWritable.zoom=true;numberOpen('zoom');numberDigit('3');numberDigit('9');numberDigit('9');numberDigit('9');");
assert.equal(values.zoom,2000);assert.equal(Object.keys(context.cbPending).length,0);assert.equal(popups.at(-1),'number_popup');
run('numberCancel();');assert.equal(values.zoom,2000);
run("numberOpen('zoom');params.setValue('number_value',0,'4096');numberApply();");assert.equal(values.zoom,2000);assert.match(values.number_error,/1365.*4095/);
run("params.setValue('number_value',0,'3999');numberApply();");assert.equal(values.zoom,3999);assert.equal(context.cbPending.zoom,3999);
run("numberOpen('zoom');params.setValue('number_value',0,'1400');cbEpoch++;numberApply();");assert.equal(values.zoom,3999);
run("cbWritable.zoom=false;numberOpen('zoom');");assert.match(labels.status,/Read Only/);
run("cbCapabilities.preset_max=50;numberOpen('shot_number');params.setValue('number_value',0,'51');numberApply();");assert.equal(values.shot_number,1);
run("params.setValue('number_value',0,'50');numberApply();");assert.equal(values.shot_number,50);
assert.ok(!xml.includes('page_td1c'));assert.ok(!xml.includes('nav_td1c'));assert.ok(xml.includes('txt-align:center;w.keyboard:disabled;'));
console.log('PASS: numeric popup stages values, validates model ranges, cancels safely, rejects stale/read-only edits, and applies once.');
