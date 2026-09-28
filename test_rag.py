import asyncio,json
from pathlib import Path
import httpx,pytest
import rag,model_provider,sync_knowledge

def test_budget_and_diverse_chunks():
    docs=json.loads(Path('data/knowledge_documents.json').read_text(encoding='utf8'))
    found,route=rag.retrieve('RMA là gì và các bước thực hiện ra sao?',docs)
    messages,selected,count=rag.pack('RMA là gì?',found,6000)
    assert selected and count<=6000 and len(selected)<=6
    assert route['routing']=='local' and any('RMA' in d['title'] for d in selected)
    assert all(d['id'] in {d['id'] for d in found} for d in selected)
    with pytest.raises(ValueError):rag.pack('x'*8000,found,6000)

def test_sync_updates_deletes_and_preserves_retirement(tmp_path):
    import sqlite3
    def connect():return sqlite3.connect(tmp_path/'test.db')
    with connect() as c:c.execute('CREATE TABLE docs(id TEXT PRIMARY KEY,payload TEXT)')
    a=sync_knowledge.document('A','First','Body','A');b=sync_knowledge.document('B','Second','Other','B')
    sync_knowledge.synchronize(connect,[a,b])
    with connect() as c:c.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps({**a,'status':'retired'}),'A'))
    sync_knowledge.synchronize(connect,[{**a,'body':'Updated'}])
    with connect() as c:
        rows=c.execute('SELECT payload FROM docs').fetchall()
    assert len(rows)==1 and json.loads(rows[0][0])['status']=='retired' and json.loads(rows[0][0])['body']=='Updated'

def test_env_aliases_and_no_secret_projection(tmp_path,monkeypatch):
    for key in ('LLM_MODE','OPENROUTER_API_KEY','API_KEY','OPENROUTER_MODEL','MODEL'):monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(model_provider,'ROOT',tmp_path)
    (tmp_path/'.env').write_text('API_KEY="example-secret"\nMODEL=vendor/model\n',encoding='utf8')
    assert model_provider.settings()['mode']=='openrouter'
    assert model_provider.settings()['model']=='vendor/model'
    assert 'example-secret' not in str(model_provider.public_settings())
    monkeypatch.setenv('LLM_MODE','local');assert model_provider.settings()['url'].startswith('http://127.0.0.1')

@pytest.mark.parametrize('mode',['local','openrouter'])
def test_provider_wire_payload_and_usage(monkeypatch,mode):
    seen=[]
    def handler(request):
        seen.append(json.loads(request.content))
        assert request.headers['Authorization']=='Bearer secret'
        return httpx.Response(200,json={'choices':[{'message':{'content':'Answer [A]'},'finish_reason':'stop'}],'usage':{'prompt_tokens':123,'completion_tokens':12,'cost':0.001}})
    real_client=httpx.AsyncClient
    monkeypatch.setattr(model_provider.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(model_provider,'headers',lambda s:{'Authorization':'Bearer secret'})
    cfg=dict(mode=mode,model='vendor/model',url='https://openrouter.ai/api/v1')
    answer,usage,finish=asyncio.run(model_provider.complete([{'role':'user','content':'Question'}],cfg,256))
    assert usage['prompt_tokens']==123 and usage['cost']==.001 and len(seen)==1
    assert seen[0]['max_tokens']==256 and ('chat_template_kwargs' in seen[0])==(mode=='local')
    if mode=='openrouter':assert seen[0]['reasoning']=={'enabled':False}
