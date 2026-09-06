"""Apply four slots through the admin API, exercise four users/conversations, restore config."""
import asyncio,json,time
from pathlib import Path
import httpx
from testing_accounts import credentials
ROOT=Path(__file__).parent
async def run():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8088',trust_env=False,timeout=240) as admin:
        (await admin.post('/api/login',json=credentials('admin'))).raise_for_status()
        original=(await admin.get('/api/admin/system')).json()['configured'];report={};clients=[];ids=[]
        async def apply(c):
            (await admin.put('/api/admin/system/config',json=c)).raise_for_status()
            (await admin.post('/api/admin/system/model',json={'action':'restart'})).raise_for_status()
            for _ in range(120):
                await asyncio.sleep(1);h=(await admin.get('/api/health')).json()
                if h['ready'] and h['parallel']==c['parallel'] and not h['generation']['maintenance']:return h
            raise RuntimeError('Model did not become ready')
        try:
            await apply({**original,'parallel':4,'context':4096})
            for role in ('sale','technical','admin','sale'):
                c=httpx.AsyncClient(base_url='http://127.0.0.1:8088',trust_env=False,timeout=240);clients.append(c)
                (await c.post('/api/login',json=credentials(role))).raise_for_status();ids.append((await c.post('/api/conversations')).json()['id'])
            questions=['Cần hỏi khách những gì trước khi triển khai Wi-Fi?','Checklist MOP triển khai firewall gồm những bước nào?','Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì?','MFA chống phishing là gì và cần chuẩn bị gì để triển khai?']
            tasks=[asyncio.create_task(c.post('/api/chat',json=dict(question=q,conversation_id=id))) for c,q,id in zip(clients,questions,ids)]
            active=0;model_active=0;start=time.monotonic()
            key=(ROOT/'data/model-api-key.txt').read_text().strip()
            async with httpx.AsyncClient(base_url='http://127.0.0.1:1234',headers={'Authorization':'Bearer '+key},trust_env=False,timeout=3) as model:
                while not all(t.done() for t in tasks):
                    h=(await admin.get('/api/health')).json();active=max(active,h['generation']['active'])
                    r=await model.get('/slots');r.raise_for_status();model_active=max(model_active,sum(bool(s.get('is_processing')) for s in r.json()))
                    await asyncio.sleep(.4)
            results=await asyncio.gather(*tasks)
            for r in results:r.raise_for_status();assert r.json()['sources']
            assert active==4 and model_active==4,(active,model_active)
            report=dict(passed=True,max_backend_active=active,max_model_processing=model_active,seconds=round(time.monotonic()-start,2),budgets=(await admin.get('/api/admin/system')).json()['budgets'],modes=[r.json()['mode'] for r in results])
        finally:
            for c,id in zip(clients,ids):await c.delete('/api/conversations/'+id)
            for c in clients:await c.post('/api/logout');await c.aclose()
            await apply(original);report['restored']=original
            await admin.post('/api/logout')
            (ROOT/'artifacts/four-slot-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
        print(json.dumps({k:report[k] for k in ('passed','max_backend_active','max_model_processing','seconds')},ensure_ascii=False))
asyncio.run(run())
