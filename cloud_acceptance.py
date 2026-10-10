"""No SMTP: isolated persistence acceptance across distinct cloud runs."""
import argparse,json,os
from datetime import datetime
from config import BEIJING,RECIPIENTS
from monitor import process,digest
from notifier import message
from state_store import GithubStore
class CachedStore(GithubStore):
    def load(self):
        if not hasattr(self,'data'): self.data=super().load()
        return self.data
def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',type=int,required=True);phase=p.parse_args().phase
    assert phase in (1,2,3,4)
    os.environ['BOOTSTRAP_STATE']='true' if phase==1 else 'false'
    store=CachedStore('monitor-acceptance');state=store.load()
    runs=state.setdefault('acceptance_runs',[]);receipts=state.setdefault('simulated_deliveries',[])
    run_id=os.environ['GITHUB_RUN_ID'];assert len(runs)==phase-1 and run_id not in runs
    a=dict(id='synthetic-A',name='SIMULATED A',points='230',amount='500',time='18:00')
    b=dict(id='synthetic-B',name='SIMULATED B',points='240',amount='600',time='19:00')
    items=[a] if phase<3 else [a,b]
    if phase==4:b['points']='250'
    def fake_sender(recipient,events,detected):
        assert len(events)==1
        assert events[0]['kind']==('信息更新' if phase==4 else '发现新空投')
        assert events[0]['item']['id']==('synthetic-A' if phase==1 else 'synthetic-B')
        msg=message(events,detected,recipient,'synthetic@163.com')
        assert msg.get_body(preferencelist=('plain',)) and msg.get_body(preferencelist=('html',))
        receipts.append(dict(recipient=digest(recipient),subject=str(msg['Subject']),run_id=run_id))
    assert process(items,store,sender=fake_sender,detected=datetime(2026,10,10,16,0,tzinfo=BEIJING))==0
    assert len(receipts)=={1:2,2:2,3:4,4:6}[phase] and not state['pending']
    for i in range(0,len(receipts),2):assert {x['recipient'] for x in receipts[i:i+2]}=={digest(x) for x in RECIPIENTS}
    runs.append(run_id);store.save(state)
    print(json.dumps(dict(phase=phase,run_id=run_id,distinct_instances=len(set(runs)),simulated_messages=len(receipts),real_emails_sent=0,result='PASS'),ensure_ascii=False))
if __name__=='__main__':main()
