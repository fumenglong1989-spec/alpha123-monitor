import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { dispatchTick } from './worker.mjs';
const controller = () => ({ scheduledTime: Date.UTC(2026,9,10,9), noRetry() {} });
const env = { SCHEDULER_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: 'synthetic-secret' };
test('disabled scheduler makes no request', async () => {
  assert.equal((await dispatchTick(controller(), {}, () => assert.fail())).outcome, 'disabled');
});
test('missing token fails closed', async () => {
  await assert.rejects(dispatchTick(controller(), { SCHEDULER_ENABLED:'true' }, () => assert.fail()), /missing_dispatch_secret/);
});
test('dispatches only production monitor, records scheduled time and run id', async () => {
  const result = await dispatchTick(controller(),env,async (url, options) => {
    assert.match(url,/github\.com\/repos\/fumenglong1989-spec\/alpha123-monitor/);
    assert.equal(options.redirect,'error');
    const body=JSON.parse(options.body);
    assert.equal(body.inputs.mode,'monitor');assert.equal(body.inputs.bootstrap,'false');
    assert.equal(body.inputs.trigger_source,'cloudflare');
    assert.equal(body.inputs.scheduled_time,'2026-10-10T09:00:00.000Z');
    return new Response(JSON.stringify({workflow_run_id:123}),{status:200});
  });
  assert.equal(result.run_id,123);
  assert.ok(!JSON.stringify(result).includes('synthetic-secret'));
});
test('legacy 204 acceptance', async () => {
  assert.equal((await dispatchTick(controller(),env,async()=>new Response(null,{status:204}))).status,204);
});
test('authentication rejection is redacted and never retried', async () => {
  let calls=0;
  await assert.rejects(dispatchTick(controller(),env,async()=>{calls++;return new Response('synthetic-secret',{status:401});}),/dispatch_http_401/);
  assert.equal(calls,1);
});
test('network exception is redacted and never retried', async () => {
  let calls=0;
  await assert.rejects(dispatchTick(controller(),env,async()=>{calls++;throw Error('synthetic-secret');}),e=>e.message==='dispatch_network_or_timeout');
  assert.equal(calls,1);
});
test('no public HTTP trigger endpoint', async () => {
  assert.equal((await worker.fetch()).status,404);
});
