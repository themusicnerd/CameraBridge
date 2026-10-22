const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const xml=fs.readFileSync(require('node:path').join(__dirname,'../dashboard/SW-Panasonic-Camera-Control.grid'),'utf8');
const decode=s=>s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&amp;/g,'&');
let pending=[],requests=[],values={camera:'pana1',speed:12,bridge:'http://example'},labels={};
const ctx=vm.createContext({JSON,Date,Math,String,Number,encodeURIComponent,
 params:{getValue:k=>values[k],setValue:(k,i,v)=>values[k]=v,setAccess:()=>{}},
 ogscript:{rename:(k,t)=>labels[k]=t,asyncPost:(u,b,cb)=>{let d=JSON.parse(decodeURIComponent(b.slice(8)));requests.push(d);pending.push({d,cb});}}});
new vm.Script(decode(xml.match(/<api>([\s\S]*?)<\/api>/)[1])).runInContext(ctx);
function run(s){vm.runInContext(s,ctx)}
function reply(action,result={generation:1}){let p=pending.shift();assert.equal(p.d.action,action);p.cb(JSON.stringify(result));return p.d;}
run("cbToken='token';cbTouchEnabled=true;jog(-1,0,0,0);release();jog(1,0,0,0);");
reply('claim');assert.equal(reply('stop').data.active_only,true);reply('claim');
assert.equal(pending[0].d.data.pan,12);assert.equal(pending[0].d.action,'move');
run('release();jog(0,1,0,0);');reply('move');reply('stop');reply('claim');
assert.equal(reply('move').data.tilt,12);assert.equal(pending.length,0);
assert.deepEqual(requests.filter(x=>x.action==='move').map(x=>[x.data.pan,x.data.tilt]),[[12,0],[0,12]]);
run('stop();');assert.equal(pending[0].d.data.active_only,false);
reply('stop',{error:'no camera'});assert.equal(ctx.cbTouchEnabled,false);assert.equal(ctx.cbMotionHeld,null);
console.log('PASS: rapid direction changes wait for stop, discard superseded claims, retain latest direction, and disable on failed stop.');
