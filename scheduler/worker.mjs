// Credentials belong only in the Cloudflare encrypted Secret binding.
const endpoint = 'https://api.github.com/repos/fumenglong1989-spec/alpha123-monitor/actions/workflows/monitor.yml/dispatches';

export async function dispatchTick(controller, env, request = fetch) {
  controller.noRetry(); // Ambiguous network acceptance: wait for next tick.
  const scheduled = new Date(controller.scheduledTime).toISOString();
  if (env.SCHEDULER_ENABLED !== 'true') return { outcome: 'disabled', scheduled };
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error('missing_dispatch_secret');
  let response;
  try {
    response = await request(endpoint, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(20000),
      headers: {
        Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN.trim()}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'alpha123-scheduler',
        'X-GitHub-Api-Version': '2026-03-10',
      },
      body: JSON.stringify({ ref: 'main', inputs: {
        mode: 'monitor', bootstrap: 'false',
        trigger_source: 'cloudflare', scheduled_time: scheduled,
      } }),
    });
  } catch (error) {
    const name = ['TypeError', 'TimeoutError', 'AbortError'].includes(error?.name) ? error.name : 'OtherError';
    throw new Error(`dispatch_fetch_${name}`); // Never log message, request, or credentials.
  }
  if (response.status !== 200 && response.status !== 204)
    throw new Error(`dispatch_http_${response.status}`); // Never log response body.
  let details = {};
  if (response.status === 200) {
    try { details = await response.json(); }
    catch { throw new Error('dispatch_invalid_response'); }
  }
  return { outcome: 'github_accepted', scheduled, status: response.status,
    run_id: Number.isSafeInteger(details.workflow_run_id) ? details.workflow_run_id : null };
}

export default {
  async scheduled(controller, env) {
    try { console.log(JSON.stringify(await dispatchTick(controller, env))); }
    catch (error) { console.error(error.message); throw error; }
  },
  async fetch() { return new Response('Not found', { status: 404 }); },
};
