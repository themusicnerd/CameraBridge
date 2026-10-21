// ogScript contract test in V8; actual DashBoard/Rhino requires equipment acceptance.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const xml=fs.readFileSync('dashboard/SW-Sony-Camera-Control.grid','utf8');
const decode=s=>s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
const ids=new Set([...xml.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]));
const access={},values={bridge:'http://127.0.0.1:8088',camera:'sony1'},labels={},requests=[];
const camera={id:'camera_3',number:3,name:'Sony software fixture',manufacturer:'Sony',model:'PXW-Z200',health:'simulated',parameters:{iris:{value:280,confirmation:'confirmed',age_seconds:0,writable:true,dependency:''},zoom:{value:100,confirmation:'confirmed',age_seconds:0,writable:false,dependency:''}},tally:{enabled:true,status:'unsupported'}};
const c=vm.createContext({JSON,Math,Date,String,Number,encodeURIComponent,
 params:{getValue:k=>values[k],setAccess:(k,v)=>access[k]=v,setValue:(k,i,v)=>{assert.equal(access[k],1,'parameter must be unlocked: '+k);values[k]=v}},
 ogscript:{setXML:()=>{},setStyle:id=>assert.ok(ids.has(id),id),rename:(id,value)=>{assert.ok(ids.has(id),id);labels[id]=value},asyncPost:(url,body,callback)=>{requests.push(JSON.parse(decodeURIComponent(body.slice(8))));callback(JSON.stringify({cameras:[camera],events:[]}))}}
});
new vm.Script(decode(xml.match(/<api>([\s\S]*?)<\/api>/)[1])).runInContext(c);
for(const m of xml.matchAll(/<(?:ogscript|task|timertask)\b[^>]*>([\s\S]*?)<\/(?:ogscript|task|timertask)>/g))new vm.Script(decode(m[1]));
vm.runInContext('poll();',c);
assert.equal(values.camera,'camera_3');assert.equal(values.iris,280);assert.equal(access.iris,0);assert.equal(access.zoom,0);
assert.match(labels.tally_state,/unsupported/);assert.match(labels.identity,/Sony software fixture/);
vm.runInContext("cbToken='test';poll();",c);assert.equal(access.iris,1);assert.equal(access.zoom,0);
console.log('PASS: Sony native handlers, initial camera selection, feedback, tally status and read-only controls');
