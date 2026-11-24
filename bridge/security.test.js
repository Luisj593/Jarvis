import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from './server.js';
async function runCase(payload, auth='Bearer test-secret', apiKey='test-openai', mockStatus=200){
 const server=createServer({token:'test-secret',apiKey,fetcher:async()=>({ok:mockStatus===200,status:mockStatus,json:async()=>({id:'r',output:[]})})});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const res=await fetch(`http://127.0.0.1:${server.address().port}/v1/command`,{method:'POST',headers:{authorization:auth,'content-type':'application/json'},body:payload});
  return {status:res.status,body:await res.json()};
 } finally {await new Promise(resolve=>server.close(resolve))}
}
test('reject malformed JSON',async()=>assert.equal((await runCase('{oops')).status,400));
test('reject blank instructions',async()=>assert.equal((await runCase(JSON.stringify({instruction:'   '}))).status,400));
test('reject overlong instruction',async()=>assert.equal((await runCase(JSON.stringify({instruction:'x'.repeat(8001)}))).status,400));
test('reject wrong bearer token',async()=>assert.equal((await runCase('{}','Bearer wrong')).status,401));
test('reject absent OpenAI API key',async()=>assert.equal((await runCase('{}','Bearer test-secret','')).status,503));
test('handle OpenAI 429',async()=>{
 const r=await runCase(JSON.stringify({instruction:'Hola'}),'Bearer test-secret','test-openai',429);
 assert.equal(r.status,502);assert.equal(r.body.upstream_status,429);
});
test('reject oversized request',async()=>assert.equal((await runCase(JSON.stringify({instruction:'x'.repeat(17000)}))).status,413));
