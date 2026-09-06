"""Exercise real stop/start on this demo model only and leave it running."""
from pathlib import Path
import httpx,time,json
from testing_accounts import credentials
root=Path(__file__).parent
report=[]
with httpx.Client(base_url='http://127.0.0.1:8088',trust_env=False,timeout=20) as c:
    c.post('/api/login',json=credentials('admin')).raise_for_status()
    before=c.get('/api/admin/system').json();original=before['configured']
    c.put('/api/admin/system/config',json={**original,'temperature':0.3}).raise_for_status()
    assert c.get('/api/admin/system').json()['configured']['temperature']==0.3
    c.put('/api/admin/system/config',json=original).raise_for_status()
    try:
        for action in ('stop','start'):
            r=c.post('/api/admin/system/model',json={'action':action});r.raise_for_status();deadline=time.time()+130
            while time.time()<deadline:
                time.sleep(2);s=c.get('/api/admin/system').json()
                if not s['generation_busy'] and s['action']['state'] in ('done','error'):break
            assert s['action']['state']=='done',s['action']
            health=c.get('/api/health').json()
            assert health['ready']==(action=='start'),health
            report.append(dict(action=action,state=s['action']['state'],ready=health['ready'],observed=s['observed']))
    finally:
        if not c.get('/api/health').json()['ready']:
            c.post('/api/admin/system/model',json={'action':'start'})
(root/'artifacts'/'model-control-report.json').write_text(json.dumps(dict(passed=True,actions=report),indent=2),encoding='utf8')
print('Model stop/start and config save passed; model ready on GPU.')
