import json
import httpx,model_provider
s=model_provider.settings()
r=httpx.post(s['url']+'/chat/completions',headers=model_provider.headers(s),json={'model':s['model'],'messages':[{'role':'user','content':'Chỉ trả lời: OK'}],'max_tokens':128,'reasoning':{'enabled':False}},timeout=90,trust_env=False)
data=r.json()
print('HTTP',r.status_code)
print('ERROR',str(data.get('error',''))[:500])
for c in data.get('choices',[]):
    print('CHOICE',c.get('finish_reason'),{k:len(str(v)) if v else 0 for k,v in c.get('message',{}).items()})
print('USAGE',data.get('usage'))
