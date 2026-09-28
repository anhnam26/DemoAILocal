import json,re
import pytest
from fastapi.testclient import TestClient
import accounts,app,model_provider

@pytest.fixture(autouse=True)
def isolated_db(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setattr(accounts,'BOOTSTRAP',tmp_path/'initial.json')
    accounts.BOOTSTRAP.write_text(json.dumps({'accounts':[dict(username=role,name=role,role=role,customers=[],password='Test-password-12345') for role in ('member','admin')]}),encoding='utf8')
    monkeypatch.setenv('LLM_MODE','openrouter');monkeypatch.setenv('OPENROUTER_MODEL','test/model');monkeypatch.setenv('OPENROUTER_API_KEY','test-key')
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('APP_ORIGINS','http://testserver,http://localhost:8088,http://127.0.0.1:8088')
    app.init();app.ACTIVE_CONVERSATIONS.clear()
    async def complete(messages,cfg,max_tokens):
        ids=re.findall(r'\[([A-Z0-9-]+)\]',messages[-1]['content'])
        return 'Cần kiểm tra và đối chiếu tài liệu ['+ids[0]+'].',{'prompt_tokens':500,'completion_tokens':40,'total_tokens':540},'stop'
    monkeypatch.setattr(model_provider,'complete',complete)

def client(role='member'):
    c=TestClient(app.app)
    assert c.post('/api/login',json={'username':role,'password':'Test-password-12345'}).status_code==200
    return c

def test_shared_theory_no_customer_and_no_old_routes():
    member,admin=client(),client('admin')
    assert member.get('/api/documents').json()==admin.get('/api/documents').json()
    assert len(member.get('/api/documents').json())>1000
    assert all(not d.get('customer') and d['knowledge_type']=='theory' for d in app.docs_for())
    for path in ('/internal/','/demo','/api/finance','/api/operations','/api/documents/CRM-A'):
        assert member.get(path).status_code==404
    assert member.get('/api/admin').status_code==403

def test_chat_one_call_bounded_and_grounded(monkeypatch):
    calls=[]
    async def complete(messages,cfg,max_tokens):
        calls.append(messages)
        assert sum(app.rag.estimate_tokens(m['content'])+16 for m in messages)+64<=cfg['input_budget']
        id=re.findall(r'\[([A-Z0-9-]+)\]',messages[-1]['content'])[0]
        return 'Kiểm tra DNS ['+id+'].',{'prompt_tokens':700,'completion_tokens':30},'stop'
    monkeypatch.setattr(model_provider,'complete',complete)
    r=client().post('/api/chat',json={'question':'Cấu hình DNS Server cần chuẩn bị gì?'})
    assert r.status_code==200,r.text
    result=r.json();assert len(calls)==1 and result['api_calls']==1
    assert result['sources'] and result['citations_verified']
    assert result['usage']['prompt_tokens']==700 and result['retrieval']['groups']

def test_customer_query_does_not_call_provider(monkeypatch):
    async def fail(*args):pytest.fail('Customer query must not call API')
    monkeypatch.setattr(model_provider,'complete',fail)
    r=client().post('/api/chat',json={'question':'Cho xem hồ sơ khách hàng và công nợ'}).json()
    assert r['api_calls']==0 and r['sources']==[] and 'không lưu' in r['answer']

def test_bad_citation_uses_only_retrieved_excerpts(monkeypatch):
    async def bad(*args):return 'Nội dung không đúng [UNKNOWN-99]',{},'stop'
    monkeypatch.setattr(model_provider,'complete',bad)
    r=client().post('/api/chat',json={'question':'Cấu hình DHCP cần gì?'}).json()
    assert r['mode']=='Trích đoạn tài liệu' and 'UNKNOWN' not in r['answer'] and r['sources']

def test_upload_approval_and_revocation():
    admin,member=client('admin'),client()
    r=admin.post('/api/admin/upload',files={'file':('theory.md',b'A theoretical guide for network backup and recovery planning.','text/markdown')},data={'audience':'all'})
    assert r.status_code==200;id=r.json()['id']
    assert member.get('/api/documents/'+id).status_code==404
    assert admin.post(f'/api/admin/documents/{id}/approve').status_code==200
    assert member.get('/api/documents/'+id).status_code==200
    assert admin.post(f'/api/admin/documents/{id}/retire').status_code==200
    assert member.get('/api/documents/'+id).status_code==404

def test_session_and_origin():
    c=client()
    assert c.post('/api/chat',headers={'Origin':'https://evil.example'},json={'question':'test'}).status_code==403
    c.post('/api/logout');assert c.get('/api/documents').status_code==401

def test_no_secrets_in_health():
    health=client().get('/api/model').json()
    assert 'api_key' not in health and 'test-key' not in str(health)
    assert health['mode']=='openrouter' and health['configured']

def test_provider_failure_no_retry(monkeypatch):
    import httpx
    calls=[]
    async def fail(*args):calls.append(1);raise httpx.ReadTimeout('do not reveal credentials')
    monkeypatch.setattr(model_provider,'complete',fail)
    r=client().post('/api/chat',json={'question':'Cấu hình DHCP cần gì?'})
    assert r.status_code==503 and len(calls)==1 and app.LOCK.active==0
