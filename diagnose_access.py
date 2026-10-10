"""Normal access only: no challenge solving, proxy, cookie injection or stealth."""
import json
import platform
import re
import httpx
from playwright.sync_api import sync_playwright
from config import URL

API = 'https://alpha123.uk/api/data?fresh=0'

def metadata(response):
    headers = response.headers
    return {'status': response.status_code, 'server': headers.get('server'), 'cf_mitigated': headers.get('cf-mitigated'), 'content_type': headers.get('content-type'), 'challenge_hint': bool(re.search(r'just a moment|cf-chl-|verify you are human|captcha', response.text, re.I))}

def main():
    report = {'platform': platform.system(), 'http': {}}
    for label, url in [('page', URL), ('api', API)]:
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            report['http'][label] = metadata(response)
            if label == 'api' and response.status_code == 200:
                obj = response.json()
                report['http'][label]['valid_airdrops'] = isinstance(obj, dict) and isinstance(obj.get('airdrops'), list)
        except Exception as exc: report['http'][label] = {'error_type': type(exc).__name__}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(timezone_id='Asia/Shanghai', locale='zh-CN')
            api_responses = []
            page.on('response', lambda r: api_responses.append(r.status) if r.url.split('?')[0] == API.split('?')[0] else None)
            response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            report['browser'] = {'page_status': response.status if response else None, 'server': response.headers.get('server') if response else None, 'cf_mitigated': response.headers.get('cf-mitigated') if response else None}
            if response and response.status == 200:
                try: page.wait_for_function('Array.isArray(window.todayAirdrops)', timeout=15000)
                except Exception: pass
            report['browser']['api_statuses'] = api_responses
            report['browser']['today_loaded'] = page.evaluate('Array.isArray(window.todayAirdrops)')
        except Exception as exc: report['browser'] = {'error_type': type(exc).__name__}
        finally: browser.close()
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__': main()
