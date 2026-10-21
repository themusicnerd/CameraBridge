/* Exercise actual generated ogScript against the local read-only lab adapter.
 * This tests the script contract in V8, NOT DashBoard's Rhino/OGLML runtime.
 * Start python -m backend.server --lab before running this optional test.
 */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const decode = s => s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
(async () => {
  for (const manufacturer of ['Panasonic','Marshall']) {
    const xml=fs.readFileSync(path.join(__dirname,'../dashboard',`SW-${manufacturer}-Camera-Control.grid`),'utf8');
    const api=decode(xml.match(/<api>([\s\S]*?)<\/api>/)[1]);
    const elements=new Set([...xml.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]));
    const values={bridge:'http://127.0.0.1:8088',camera:manufacturer==='Panasonic'?'pana1':'marshall1'};
    const labels={},inflight=[];
    const context=vm.createContext({
      console,JSON,Date,Math,String,Number,encodeURIComponent,
      params:{getValue:(k)=>values[k],setValue:(k,i,v)=>{values[k]=v;},setAccess:()=>{}},
      ogscript:{
        rename:(id,text)=>{assert.ok(elements.has(id),`missing UI id ${id}`);labels[id]=text;},
        asyncPost:(url,body,callback)=>{
          const task=fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body}).then(r=>r.text()).then(callback);
          inflight.push(task);
        }
      }
    });
    new vm.Script(api,{filename:manufacturer+'.api'}).runInContext(context);
    let count=0;
    for(const match of xml.matchAll(/<(?:ogscript|task|timertask)\b[^>]*>([\s\S]*?)<\/(?:ogscript|task|timertask)>/g)){
      new vm.Script(decode(match[1]),{filename:manufacturer+'.handler'+count});count++;
    }
    vm.runInContext('poll();',context);
    await Promise.all(inflight);
    assert.match(labels.identity,/emulator|LAB/);
    assert.match(labels.connection,/SIMULATOR/);
    assert.match(labels.status,/read-only/);
    assert.ok(labels.actual_red_gain.includes('confirmed'));
    console.log(`${manufacturer}: ${count} handlers parse; live lab feedback updates native parameter/label contract`);
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
