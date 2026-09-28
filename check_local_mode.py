"""Explicit local GPU smoke; restore provider mode and stop only a newly started model."""
import json,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent
admin=next(a for a in json.loads((ROOT/'data/initial-accounts.json').read_text(encoding='utf8'))['accounts'] if a['role']=='admin')
report={};started=False;cv=None
with httpx.Client(base_url='http://127.0.0.1:8088',timeout=180,trust_env=False) as c:
    c.post('/api/login',json={k:admin[k] for k in ('username','password')}).raise_for_status()
    old=c.get('/api/health').json()['mode']
    try:
        c.put('/api/admin/system/provider',json={'mode':'local'}).raise_for_status()
        if not c.get('/api/health').json()['ready']:
            c.post('/api/admin/system/model',json={'action':'start'}).raise_for_status();started=True
        for _ in range(50):
            if c.get('/api/health').json()['ready']:break
            time.sleep(2)
        else:raise RuntimeError('Local model did not become ready')
        cv=c.post('/api/conversations').json()['id']
        r=c.post('/api/chat',json={'question':'DNS là gì? Trả lời ngắn và dẫn nguồn.','conversation_id':cv})
        report={'status':r.status_code,'result':r.json()}
    finally:
        if cv:c.delete('/api/conversations/'+cv)
        if started:
            c.post('/api/admin/system/model',json={'action':'stop'})
            for _ in range(15):
                state=c.get('/api/health').json()
                if not state['generation']['maintenance']:break
                time.sleep(1)
        c.put('/api/admin/system/provider',json={'mode':old}).raise_for_status()
        c.post('/api/logout')
(ROOT/'artifacts/local_smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
