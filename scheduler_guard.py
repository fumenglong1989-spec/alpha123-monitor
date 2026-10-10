"""Persist automatic tick claims under the workflow's single concurrency group."""
import json
import os
from datetime import datetime, timezone
from state_store import GithubStore

def claim(store, scheduled, run_id, now=None):
    now = now or datetime.now(timezone.utc)
    tick = datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
    if tick.tzinfo is None or abs((now - tick).total_seconds()) > 3600:
        raise ValueError('invalid_or_stale_scheduler_timestamp')
    key = str(int(tick.timestamp()) // 300)
    state = store.load()
    ledger = state.setdefault('scheduler_ticks', {})
    if key in ledger:
        print(json.dumps({'scheduler': 'duplicate_skipped', 'tick': key, 'original_run': ledger[key]}))
        return False
    ledger[key] = str(run_id)
    state['scheduler_ticks'] = {k: v for k, v in ledger.items() if int(k) >= int(now.timestamp()) // 300 - 288}
    store.save(state)
    print(json.dumps({'scheduler': 'tick_claim_saved', 'tick': key, 'run_id': str(run_id)}))
    return True

if __name__ == '__main__':
    allowed = True
    if os.getenv('TRIGGER_SOURCE') == 'cloudflare':
        allowed = claim(GithubStore(), os.environ['SCHEDULED_TIME'], os.environ['GITHUB_RUN_ID'])
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
        out.write('should_run=' + str(allowed).lower() + '\n')
