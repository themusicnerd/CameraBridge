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
    const labels={},inflight=[],access={},opened=[];
    const context=vm.createContext({
      console,JSON,Date,Math,String,Number,encodeURIComponent,
      params:{getValue:(k)=>values[k],setValue:(k,i,v)=>{assert.equal(access[k],1,`feedback must unlock local parameter ${k} before setValue`);values[k]=v;},setAccess:(k,v)=>{access[k]=v;}},
      ogscript:{
        setXML:(id,xml)=>{assert.equal(id,'bridge_launcher');const link=xml.match(/href="([^"]+)"/);if(link)opened.push(link[1]);},
        setStyle:(id,style)=>{assert.ok(elements.has(id),`missing style target ${id}`);},
        rename:(id,text)=>{assert.ok(elements.has(id),`missing UI id ${id}`);labels[id]=text;},
        asyncPost:(url,body,callback)=>{
          const task=fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body}).then(r=>r.text()).then(callback);
          inflight.push(task);
        }
      }
    });
    new vm.Script(api,{filename:manufacturer+'.api'}).runInContext(context);
    vm.runInContext('refreshBridgeLink();',context);
    assert.deepEqual(opened,['http://127.0.0.1:8088/']);
    values.bridge='javascript:alert(1)';vm.runInContext('refreshBridgeLink();',context);
    assert.equal(opened.length,1,'non-HTTP links must not launch');values.bridge='http://127.0.0.1:8088';
    vm.runInContext('cbNoticeUntil=0;',context);
    vm.runInContext("highlightPage(CB_MANUFACTURER==='Panasonic'?'PTZ':'Paint');",context);
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
    assert.equal(values.red_gain,manufacturer==='Panasonic'?150:128);
    assert.equal(access.red_gain,0,'unauthenticated controls return to read-only');
    console.log(`${manufacturer}: ${count} handlers parse; live lab feedback updates native parameter/label contract`);
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
