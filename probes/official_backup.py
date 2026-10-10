"""One-shot normal browser probe of the backup documented by Alpha123."""
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from config import BEIJING
from monitor import parse_rows

URL = 'https://zh1.alpha123.net/'
API = 'https://zh1.alpha123.net/api/data'

def main():
    report = {'source': URL, 'detected': datetime.now(BEIJING).isoformat(), 'parsed': False}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(timezone_id='Asia/Shanghai', locale='zh-CN')
            with page.expect_response(lambda r: r.url.split('?')[0] == API, timeout=45000) as event:
                response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
                report['page_status'] = response.status if response else None
                report['page_content_type'] = response.headers.get('content-type') if response else None
                report['cf_mitigated'] = response.headers.get('cf-mitigated') if response else None
                if not response or response.status != 200 or report['cf_mitigated'] == 'challenge':
                    raise ValueError('PAGE_ACCESS_DENIED_OR_FAILED')
            api = event.value
            report['api_status'] = api.status
            report['api_content_type'] = api.headers.get('content-type')
            report['api_cf_mitigated'] = api.headers.get('cf-mitigated')
            if api.status != 200 or report['api_cf_mitigated'] == 'challenge': raise ValueError('API_ACCESS_DENIED_OR_FAILED')
            data = api.json()
            if not isinstance(data, dict) or not isinstance(data.get('airdrops'), list): raise ValueError('INVALID_SCHEMA')
            report['all_airdrops'] = len(data['airdrops'])
            page.wait_for_function('Array.isArray(window.todayAirdrops)', timeout=15000)
            headers = [s.strip() for s in page.locator('#today-airdrops th').all_text_contents()]
            if headers != ['项目', '积分', '数量', '时间']: raise ValueError('INVALID_TODAY_HEADERS')
            count = page.evaluate('window.todayAirdrops.length')
            rows = page.locator('#today-airdrops tbody tr').evaluate_all("rows=>rows.map(r=>Array.from(r.querySelectorAll('td')).map(c=>c.innerText.trim()))")
            items = parse_rows(rows)
            if len(items) != count: raise ValueError('COUNT_MISMATCH')
            report.update(parsed=True, today_count=count, today_items=items, outcome='NORMAL_BROWSER_ACCESS_SUCCEEDED')
        except Exception as exc:
            report.update(outcome='STOP_PROBE_FAILED', error_type=type(exc).__name__)
        finally: browser.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['parsed'] else 1

if __name__ == '__main__': raise SystemExit(main())
