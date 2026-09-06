from testing_accounts import credentials,browser_login
from pathlib import Path
import httpx,json,time
root=Path(__file__).parent
out=root/'artifacts';out.mkdir(exist_ok=True)
report=[]
for role,question in [('sale','Cần hỏi khách những gì trước khi triển khai Wi-Fi?'),('technical','Checklist MOP triển khai firewall gồm những bước nào?')]:
    with httpx.Client(base_url='http://127.0.0.1:8088',timeout=200,trust_env=False) as c:
        c.post('/api/login',json=credentials(role)).raise_for_status()
        start=time.monotonic();r=c.post('/api/chat',json={'question':question})
        data=r.json();report.append({'role':role,'question':question,'status':r.status_code,'seconds':round(time.monotonic()-start,2),'result':data})
        print(json.dumps(report[-1],ensure_ascii=True),flush=True)
        assert r.status_code==200,r.text
        assert data['mode']=='Qwen3.5-9B + RAG'
        assert data['citations_verified'],data
(out/'smoke-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
