"""Send three independent user questions and verify real overlapping model slots."""
import asyncio,json,time
from pathlib import Path
import httpx
from testing_accounts import credentials
root=Path(__file__).parent
async def run():
    clients=[httpx.AsyncClient(base_url='http://127.0.0.1:8088',trust_env=False,timeout=240) for _ in range(3)]
    report=dict(samples=[],results=[])
    try:
        for c,role in zip(clients,('sale','technical','admin')):
            r=await c.post('/api/login',json=credentials(role));r.raise_for_status()
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            h=(await clients[0].get('/api/health')).json()
            if h['ready']:break
            await asyncio.sleep(1)
        assert h['ready'] and h['parallel']==2 and h['context']==4096,h
        questions=['Cần hỏi khách những gì trước khi triển khai Wi-Fi?','Checklist MOP triển khai firewall gồm những bước nào?','Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì?']
        ids=[(await c.post('/api/conversations')).json()['id'] for c in clients]
        async def ask(c,q,id):
            start=time.monotonic();r=await c.post('/api/chat',json=dict(question=q,conversation_id=id));r.raise_for_status();d=r.json()
            assert d['mode']=='Qwen3.5-9B + RAG' and d['sources'],d
            return dict(question=q,seconds=round(time.monotonic()-start,2),mode=d['mode'],conversation_id=d['conversation_id'],sources=[s['id'] for s in d['sources']])
        start=time.monotonic();tasks=[asyncio.create_task(ask(c,q,id)) for c,q,id in zip(clients,questions,ids)]
        key=(root/'data/model-api-key.txt').read_text().strip();blocked=False
        async with httpx.AsyncClient(base_url='http://127.0.0.1:1234',headers={'Authorization':'Bearer '+key},trust_env=False,timeout=3) as model:
            while not all(t.done() for t in tasks):
                h=(await clients[2].get('/api/health')).json();sample=dict(seconds=round(time.monotonic()-start,2),**h['generation'])
                try:
                    slots=await model.get('/slots')
                    if slots.status_code==200:sample['model_processing']=sum(bool(s.get('is_processing')) for s in slots.json())
                except httpx.HTTPError:pass
                report['samples'].append(sample)
                if sample['active'] and not blocked:
                    blocked=(await clients[2].post('/api/admin/system/model',json={'action':'stop'})).status_code==409
                await asyncio.sleep(.5)
        report['results']=await asyncio.gather(*tasks)
        report['total_seconds']=round(time.monotonic()-start,2)
        report['max_active']=max(s['active'] for s in report['samples']);report['max_waiting']=max(s['waiting'] for s in report['samples'])
        report['max_model_processing']=max(s.get('model_processing',0) for s in report['samples'])
        assert report['max_active']==2 and report['max_waiting']>=1 and blocked,report
        assert report['max_model_processing']==2,'Model /slots did not confirm actual simultaneous processing'
        report['system']=(await clients[2].get('/api/admin/system')).json();report['passed']=True
        (root/'artifacts/concurrent-chat-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({k:report[k] for k in ('passed','total_seconds','max_active','max_waiting','max_model_processing')},ensure_ascii=False))
    finally:
        for c in clients:
            await c.post('/api/logout');await c.aclose()
asyncio.run(run())
