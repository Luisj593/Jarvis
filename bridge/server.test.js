import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer, authorized } from './server.js';

test('token verification', () => {
  assert.equal(authorized('Bearer secret', 'secret'), true);
  assert.equal(authorized('Bearer wrong', 'secret'), false);
  assert.equal(authorized('', 'secret'), false);
});

test('health, authentication and OpenAI proxy', async () => {
  const server = createServer({
    token: 'test-secret', apiKey: 'test-openai',
    fetcher: async (_url, options) => {
      assert.equal(options.headers.authorization, 'Bearer test-openai');
      const body = JSON.parse(options.body);
      assert.equal(body.store, false);
      return { ok: true, json: async () => ({ id: 'resp_test', output: [{ content: [{ type: 'output_text', text: 'Plan listo' }] }] }) };
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = `http://127.0.0.1:${server.address().port}`;
  try {
    const health = await fetch(url + '/health');
    assert.equal(health.status, 200);
    const denied = await fetch(url + '/v1/command', { method: 'POST' });
    assert.equal(denied.status, 401);
    const ok = await fetch(url + '/v1/command', {
      method: 'POST', headers: { authorization: 'Bearer test-secret', 'content-type': 'application/json' },
      body: JSON.stringify({ project: 'Jarvis', instruction: 'Analiza el módulo' })
    });
    assert.equal(ok.status, 200);
    assert.equal((await ok.json()).answer, 'Plan listo');
  } finally { await new Promise(resolve => server.close(resolve)); }
});
