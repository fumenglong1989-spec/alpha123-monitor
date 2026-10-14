import copy
import unittest
from datetime import datetime
from config import BEIJING, RECIPIENTS
from monitor import project_identities, process
from state_store import initial

class Store:
    def __init__(self): self.data = initial()
    def load(self): return copy.deepcopy(self.data)
    def save(self, data): self.data = copy.deepcopy(data)

class RealApiIdentityTests(unittest.TestCase):
    def test_actual_unannounced_record_has_creation_identity(self):
        record={'token':'','name':'','amount':'','points':'245','time':'18:00',
                'created_timestamp':1791964881,'updated_timestamp':1791965951}
        self.assertEqual(project_identities([record]), ['created:1791964881'])
        record.update(token='ABC', name='Example', amount='500', updated_timestamp=1791967000)
        self.assertEqual(project_identities([record]), ['created:1791964881'])

    def test_explicit_id_and_zero_preserved(self):
        self.assertEqual(project_identities([{'id':'abc'},{'id':0}]), ['abc','0'])

    def test_ambiguous_or_missing_creation_rejected(self):
        for records in ([{}],[{'created_timestamp':True}],
                        [{'created_timestamp':123},{'created_timestamp':123}],
                        [{'created_timestamp':'not-a-timestamp'}]):
            with self.assertRaises(ValueError): project_identities(records)

    def test_unpublished_project_then_restart_and_details_update(self):
        store=Store(); sent=[]; sender=lambda recipient, events, detected: sent.append((recipient,copy.deepcopy(events)))
        detected=datetime(2026,10,14,16,30,tzinfo=BEIJING)
        item={'id':'created:1791964881','name':'UNKNOWN 未知项目','points':'245','amount':'-','time':'18:00'}
        self.assertEqual(process([item],store,sender,detected),0)
        self.assertEqual(len(sent),len(RECIPIENTS))
        restart=Store(); restart.data=copy.deepcopy(store.data)
        process([item],restart,sender,detected)
        self.assertEqual(len(sent),len(RECIPIENTS))
        changed=dict(item,name='ABC Example',amount='500')
        process([changed],restart,sender,detected)
        self.assertEqual(len(sent),2*len(RECIPIENTS))
        self.assertTrue(all(events[0]['kind']=='信息更新' for _,events in sent[len(RECIPIENTS):]))
