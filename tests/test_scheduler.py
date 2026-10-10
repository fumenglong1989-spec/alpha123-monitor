import copy
import unittest
from datetime import datetime, timezone, date
from scheduler_guard import claim
from token_reminder import remind
from state_store import initial

class Store:
    def __init__(self): self.state = initial()
    def load(self): return copy.deepcopy(self.state)
    def save(self, data): self.state = copy.deepcopy(data)

class SchedulerTests(unittest.TestCase):
    def test_tick_persists_across_instances(self):
        s = Store(); now = datetime(2026, 10, 10, 10, tzinfo=timezone.utc)
        self.assertTrue(claim(s, '2026-10-10T10:00:00Z', '1', now))
        restart = Store(); restart.state = copy.deepcopy(s.state)
        self.assertFalse(claim(restart, '2026-10-10T10:00:00Z', '2', now))
        self.assertTrue(claim(restart, '2026-10-10T10:05:00Z', '3', now))
    def test_reject_stale_or_naive(self):
        for stamp in ('2020-01-01T00:00:00Z', '2026-10-10T10:00:00'):
            with self.assertRaises(ValueError): claim(Store(), stamp, '1')
    def test_no_early_expiry_notice(self):
        sent=[]; remind(Store(), '2027-01-08', date(2026,10,10), lambda *a: sent.append(a))
        self.assertEqual(sent, [])
    def test_expiry_recipient_retry_and_dedup(self):
        s=Store(); sent=[]
        def sender(recipient, expiry):
            if recipient.startswith('249'): raise OSError()
            sent.append(recipient)
        remind(s, '2027-01-08', date(2026,12,26), sender)
        remind(s, '2027-01-08', date(2026,12,26), lambda r,e: sent.append(r))
        remind(s, '2027-01-08', date(2026,12,26), lambda r,e: sent.append(r))
        self.assertEqual(len(sent), 2)
