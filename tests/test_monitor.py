import base64
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import httpx
from monitor import process, parse_rows, fetch_with_retry
from notifier import message
from config import BEIJING, RECIPIENTS
from state_store import LocalStore, GithubStore, initial

class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = LocalStore(Path(self.temp.name) / 'state.json')
        self.calls = []
        self.date = datetime(2026, 10, 10, 14, 30, tzinfo=BEIJING)
        self.a = dict(name='ABC', points='230', amount='500', time='18:00')
    def tearDown(self): self.temp.cleanup()
    def send(self, recipient, events, detected): self.calls.append((recipient, events))
    def run_items(self, items, sender=None, date=None): return process(items, self.store, sender or self.send, date or self.date)
    def test_empty(self):
        self.run_items(parse_rows([['暂无数据']]))
        self.assertEqual(self.calls, [])
    def test_first_both(self):
        self.run_items([self.a]); self.assertEqual([c[0] for c in self.calls], list(RECIPIENTS))
    def test_repeat(self):
        self.run_items([self.a]); self.run_items([self.a]); self.assertEqual(len(self.calls), 2)
    def test_second_only(self):
        self.run_items([self.a]); b = dict(self.a, name='DEF'); self.run_items([self.a, b])
        self.assertEqual([e['item']['name'] for e in self.calls[-1][1]], ['DEF'])
    def test_update(self):
        self.run_items([self.a]); self.run_items([dict(self.a, points='240')])
        self.assertEqual(self.calls[-1][1][0]['kind'], '信息更新')
    def test_fetch_failure(self):
        calls = []
        def fail(): calls.append(1); raise OSError('network')
        with self.assertRaises(OSError): fetch_with_retry(fail, lambda _: None)
        self.assertEqual(len(calls), 3); self.assertEqual(self.calls, [])
    def test_restart(self):
        self.run_items([self.a]); self.store = LocalStore(self.store.path); self.run_items([self.a])
        self.assertEqual(len(self.calls), 2)
    def test_partial_failure(self):
        def partial(recipient, events, detected):
            if recipient == RECIPIENTS[1]: raise OSError('smtp')
            self.send(recipient, events, detected)
        self.assertEqual(self.run_items([self.a], partial), 1)
        self.run_items([self.a]); self.assertEqual([c[0] for c in self.calls], list(RECIPIENTS))
        self.assertEqual(self.store.load()['pending'], [])
    def test_midnight_beijing(self):
        self.run_items([self.a], date=datetime(2026, 10, 10, 15, 59, tzinfo=timezone.utc))
        self.run_items([self.a], date=datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc))
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(set(self.store.load()['days']), {'2026-10-10','2026-10-11'})
    def test_pending_survives_empty_and_midnight(self):
        self.run_items([self.a], lambda *args: (_ for _ in ()).throw(OSError()))
        self.run_items([], date=datetime(2026, 10, 11, tzinfo=BEIJING)); self.assertEqual(len(self.calls), 2)
    def test_bad_parse(self):
        for rows in ([], [['loading']], [['ABC','230']]):
            with self.assertRaises(ValueError): parse_rows(rows)
    def test_corrupt_state(self):
        self.store.path.write_text('{}')
        with self.assertRaises(ValueError): self.run_items([self.a])
        self.assertEqual(self.calls, [])
    def test_persist_failure_before_send(self):
        with patch.object(self.store, 'save', side_effect=OSError()):
            with self.assertRaises(OSError): self.run_items([self.a])
        self.assertEqual(self.calls, [])
    def test_utf8_html(self):
        msg = message([{'kind':'发现新空投','item':self.a}], '2026-10-10', RECIPIENTS[0], 'sender@qq.com')
        self.assertEqual(msg.get_content_type(), 'multipart/alternative')
        self.assertIn('项目名称', msg.get_body(preferencelist=('plain',)).get_content())

class GithubTests(unittest.TestCase):
    def test_remote_state_roundtrip_and_sha(self):
        data = initial(); requests = []
        def handler(request):
            requests.append(request)
            if request.method == 'GET': return httpx.Response(200, json={'sha':'old', 'content':base64.b64encode(json.dumps(data).encode()).decode()})
            payload = json.loads(request.content)
            self.assertEqual(payload['sha'], 'old'); self.assertEqual(payload['branch'], 'monitor-state')
            data.update(json.loads(base64.b64decode(payload['content'])))
            return httpx.Response(200, json={'content':{'sha':'new'}})
        with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', GITHUB_TOKEN='test-token'):
            store = GithubStore(); store.client.close(); store.client = httpx.Client(transport=httpx.MockTransport(handler))
            state = store.load(); state['days']['2026-10-10'] = {'key':'fingerprint'}; store.save(state)
            self.assertEqual(store.sha, 'new'); self.assertIn('2026-10-10', store.load()['days'])
    def test_missing_remote_fails_closed(self):
        with patch.dict(os.environ, GITHUB_REPOSITORY='owner/repo', GITHUB_TOKEN='test-token', BOOTSTRAP_STATE='false'):
            store = GithubStore(); store.client.close(); store.client = httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(404)))
            with self.assertRaises(httpx.HTTPStatusError): store.load()

if __name__ == '__main__': unittest.main()
