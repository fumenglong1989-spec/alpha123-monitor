import argparse
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from config import URL, RECIPIENTS, BEIJING, STATE_PATH
from state_store import LocalStore, GithubStore
from notifier import send

def now(): return datetime.now(BEIJING)
def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def parse_rows(rows):
    if len(rows) == 1 and len(rows[0]) == 1 and '暂无数据' in rows[0][0]: return []
    if not rows: raise ValueError('表格尚未加载')
    items = []
    for row in rows:
        if len(row) != 4 or any(not str(c).strip() for c in row): raise ValueError('今日空投表格结构变化')
        name = row[0].strip()
        items.append({'name': name, 'points': row[1].strip(), 'amount': row[2].strip(), 'time': row[3].strip()})
    if len({i['name'] for i in items}) != len(items): raise ValueError('项目标识重复；停止发送')
    return items

def fetch_today():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(timezone_id='Asia/Shanghai', locale='zh-CN')
            with page.expect_response(lambda r: r.url.split('?')[0] == 'https://alpha123.uk/api/data', timeout=45000) as result:
                response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
                if not response or response.status != 200: raise ValueError('页面 HTTP 失败')
            api = result.value
            if api.status != 200: raise ValueError('数据接口 HTTP 失败')
            data = api.json()
            if not isinstance(data, dict) or not isinstance(data.get('airdrops'), list): raise ValueError('数据接口结构错误')
            page.wait_for_function("Array.isArray(window.todayAirdrops)", timeout=20000)
            count = page.evaluate('window.todayAirdrops.length')
            headers = page.locator('#today-airdrops th').all_text_contents()
            if [h.strip() for h in headers] != ['项目', '积分', '数量', '时间']: raise ValueError('表头变化')
            rows = page.locator('#today-airdrops tbody tr').evaluate_all("rows => rows.map(r => Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim()))")
            # Use primary fields only, excluding prices, shares and dynamic countdowns.
            if count:
                rows = page.locator('#today-airdrops tbody tr').evaluate_all("rows => rows.map(r => { const c=r.querySelectorAll('td'); return [c[0].querySelector('.token-symbol').innerText.trim() + ' ' + c[0].querySelector('.token-fullname').innerText.trim(), c[1].querySelector('.points-badge').innerText.trim(), c[2].querySelector('.points-badge').innerText.trim(), c[3].innerText.trim()]; })")
                # Time column can contain live countdowns. Take stable API-derived time from the same rendered objects.
                times = page.evaluate("window.todayAirdrops.map(a => (a.beijing_time || a.time || '待公布') + (a.phase === 2 ? ' (二段)' : ''))")
                for row, value in zip(rows, times): row[3] = value
            items = parse_rows(rows)
            if len(items) != count: raise ValueError('渲染项目数量不一致')
            identities = page.evaluate("window.todayAirdrops.map(a => a.id ? String(a.id) : null)")
            if count and (any(not i for i in identities) or len(set(identities)) != count):
                raise ValueError('接口项目标识缺失或重复')
            for item, identity in zip(items, identities): item['id'] = identity
            return items
        finally: browser.close()

def fetch_with_retry(fetch=fetch_today, sleep=time.sleep):
    for attempt in range(3):
        try: return fetch()
        except Exception as exc:
            logging.warning('网站检查失败 attempt=%s error_type=%s', attempt + 1, type(exc).__name__)
            if attempt == 2: raise
            sleep(5 * (attempt + 1))

def process(items, store, sender=send, detected=None):
    detected = (detected or now()).astimezone(BEIJING)
    day = detected.date().isoformat()
    state = store.load()
    known = state['days'].setdefault(day, {})
    events = []
    for item in items:
        key, fingerprint = digest(item.get('id', item['name'])), digest(item)
        if known.get(key) == fingerprint: continue
        events.append({'kind': '信息更新' if key in known else '发现新空投', 'item': item})
        known[key] = fingerprint
    if events:
        state['pending'].append({'events': events, 'detected': detected.strftime('%Y-%m-%d %H:%M:%S'), 'done': []})
    # Persist outbox before sending; remote persistence failure aborts all sends.
    store.save(state)
    logging.info('检测时间=%s 今日项目=%s 新增或更新=%s 待处理批次=%s', detected.isoformat(), len(items), len(events), len(state['pending']))
    failures = 0
    for batch in list(state['pending']):
        for recipient in RECIPIENTS:
            recipient_key = digest(recipient)
            if recipient_key in batch['done']: continue
            try: sender(recipient, batch['events'], batch['detected'])
            except Exception as exc:
                failures += 1
                logging.error('邮件失败 recipient=%s error_type=%s 下轮重试', recipient, type(exc).__name__)
            else:
                batch['done'].append(recipient_key)
                store.save(state)
                logging.info('邮件 SMTP 已接受 recipient=%s', recipient)
        if len(batch['done']) == len(RECIPIENTS):
            state['pending'].remove(batch); store.save(state)
    # Keep 35 days, pending batches independently survive date rollover.
    for old in sorted(state['days'])[:-35]: del state['days'][old]
    store.save(state)
    return failures

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--probe', action='store_true'); args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        started = now(); items = fetch_with_retry()
        if now().date() != started.date(): raise ValueError('检查跨过北京时间午夜，下一轮重新读取')
        if args.probe:
            print(json.dumps({'detected': now().isoformat(), 'items': items}, ensure_ascii=False)); return 0
        store = GithubStore() if os.getenv('GITHUB_ACTIONS') == 'true' else LocalStore(STATE_PATH)
        return 1 if process(items, store) else 0
    except Exception as exc:
        logging.error('本轮失败，未将网站错误当成新空投 error_type=%s', type(exc).__name__); return 1

if __name__ == '__main__': raise SystemExit(main())
