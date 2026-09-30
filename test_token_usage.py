import asyncio,json
from concurrent.futures import ThreadPoolExecutor
import httpx,pytest
from fastapi import HTTPException
import app,token_usage,model_provider
from test_app import isolated_db,client

def setup_user(limit=10000):
    c=client();u=c.get('/api/me').json()
    with app.connect() as db:db.execute('UPDATE users SET monthly_token_limit=? WHERE id=?',(limit,u['id']))
    return c,u

def test_atomic_parallel_reservation():
    _,u=setup_user(1000)
    def reserve():
        try:return token_usage.reserve(app.connect,u['id'],u['model'],600,200)[0]
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:reserve(),range(2)))
    assert sum(isinstance(x,str) for x in results)==1 and 429 in results
    assert token_usage.summary(app.connect,u['id'])['reserved_tokens']==800

def test_settle_actual_idempotent_and_month_rollover(monkeypatch):
    _,u=setup_user(1000);monkeypatch.setattr(token_usage,'month',lambda:'2026-09')
    id,out=token_usage.reserve(app.connect,u['id'],u['model'],600,200)
    token_usage.mark_sent(app.connect,id)
    token_usage.settle(app.connect,id,{'prompt_tokens':200,'completion_tokens':40,'total_tokens':240})
    token_usage.settle(app.connect,id,{'prompt_tokens':999,'completion_tokens':999})
    s=token_usage.summary(app.connect,u['id']);assert s['used_tokens']==240 and s['remaining_tokens']==760 and s['reserved_tokens']==0
    monkeypatch.setattr(token_usage,'month',lambda:'2026-10')
    assert token_usage.summary(app.connect,u['id'])['used_tokens']==0
    assert token_usage.summary(app.connect,u['id'],'2026-09')['used_tokens']==240

def test_timeout_retains_budget_and_admin_reconciles(monkeypatch):
    c,u=setup_user()
    async def fail(*args):raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(model_provider,'complete',fail)
    assert c.post('/api/chat',json={'question':'DNS là gì?'}).status_code==503
    s=token_usage.summary(app.connect,u['id']);assert s['uncertain_tokens']>0 and s['used_tokens']==0
    a=client('admin');records=a.get('/api/admin/usage').json()['records'];id=records[0]['id']
    payload=dict(prompt_tokens=120,completion_tokens=20,note='Đã kiểm usage trên OpenRouter')
    assert c.post('/api/admin/usage/'+id+'/reconcile',json=payload).status_code==403
    assert a.post('/api/admin/usage/'+id+'/reconcile',json=payload).status_code==200
    assert a.post('/api/admin/usage/'+id+'/reconcile',json=payload).status_code==409
    s=token_usage.summary(app.connect,u['id']);assert s['used_tokens']==140 and s['uncertain_tokens']==0

def test_oversized_or_missing_usage_never_silently_releases():
    _,u=setup_user(1000)
    id,_=token_usage.reserve(app.connect,u['id'],u['model'],600,200);token_usage.mark_sent(app.connect,id)
    token_usage.settle(app.connect,id,{'prompt_tokens':-1,'completion_tokens':10})
    assert token_usage.summary(app.connect,u['id'])['uncertain_tokens']==800

def test_restart_pending_recovery():
    _,u=setup_user(3000)
    id,_=token_usage.reserve(app.connect,u['id'],u['model'],600,200);token_usage.mark_sent(app.connect,id)
    token_usage.reserve(app.connect,u['id'],u['model'],600,200)
    token_usage.recover(app.connect)
    s=token_usage.summary(app.connect,u['id']);assert s['uncertain_tokens']==800 and s['reserved_tokens']==0

def test_limit_blocks_before_api_and_cannot_override_model(monkeypatch):
    c,u=setup_user(0)
    async def fail(*args):pytest.fail('Provider must not be called')
    monkeypatch.setattr(model_provider,'complete',fail)
    assert c.post('/api/chat',json={'question':'DNS là gì?','model':'unauthorized/model'}).status_code==403
    assert c.post('/api/chat',json={'question':'DNS là gì?'}).status_code==429
    assert token_usage.summary(app.connect,u['id'])['requests']==0

def test_model_assignment_and_password_change(monkeypatch):
    monkeypatch.setenv('MODEL1','vendor/second');a=client('admin');c,u=setup_user()
    payload=dict(username='member',name='Member',role='member',model='vendor/second',monthly_token_limit=5000)
    assert c.put('/api/admin/users/'+u['id'],json=payload).status_code==403
    assert a.put('/api/admin/users/'+u['id'],json={**payload,'model':'unknown'}).status_code==400
    assert a.put('/api/admin/users/'+u['id'],json=payload).status_code==200
    async def complete(messages,cfg,max_tokens):
        assert cfg['model']=='vendor/second'
        import re
        id=re.findall(r'\[([A-Z0-9-]+)\]',messages[-1]['content'])[0]
        return 'Nguồn ['+id+']',{'prompt_tokens':100,'completion_tokens':30},'stop'
    monkeypatch.setattr(model_provider,'complete',complete)
    assert c.post('/api/chat',json={'question':'DNS là gì?','model':'test/model'}).status_code==403
    r=c.post('/api/chat',json={'question':'DNS là gì?','model':'vendor/second'});assert r.status_code==200,r.text
    assert r.json()['model']=='vendor/second'
    id=r.json()['conversation_id'];c.delete('/api/conversations/'+id)
    assert c.get('/api/account/usage').json()['used_tokens']==130
    assert a.put('/api/admin/users/'+u['id'],json={**payload,'password':'Changed-password-234'}).status_code==200
    assert c.get('/api/me').status_code==401
    assert c.post('/api/login',json={'username':'member','password':'Changed-password-234'}).status_code==200

def test_model_changed_while_waiting_cancels_reservation():
    _,u=setup_user();id,_=token_usage.reserve(app.connect,u['id'],u['model'],600,200)
    with app.connect() as c:c.execute('UPDATE users SET allowed_models=? WHERE id=?',(json.dumps(['new/model']),u['id']))
    with pytest.raises(HTTPException):token_usage.mark_sent(app.connect,id)
    token_usage.settle(app.connect,id)
    assert token_usage.summary(app.connect,u['id'])['reserved_tokens']==0

def test_usage_counted_even_when_completion_invalid(monkeypatch):
    c,u=setup_user()
    async def empty(*args):raise model_provider.InvalidCompletion({'prompt_tokens':400,'completion_tokens':200})
    monkeypatch.setattr(model_provider,'complete',empty)
    assert c.post('/api/chat',json={'question':'DNS là gì?'}).status_code==503
    assert token_usage.summary(app.connect,u['id'])['used_tokens']==600

def test_unauthorized_usage_and_month_validation():
    a,c=client('admin'),client()
    assert c.get('/api/admin/usage').status_code==403
    assert a.get('/api/admin/usage?month=2026-99').status_code==422

def test_production_host_origin_cookie(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('APP_ORIGINS','https://knowledge.example.com')
    c=TestClient(app.app,base_url='https://knowledge.example.com')
    r=c.post('/api/login',json={'username':'member','password':'Test-password-12345'})
    assert r.status_code==200 and 'Secure' in r.headers['set-cookie']
    assert c.get('/api/me').status_code==200
    assert c.get('/api/health',headers={'Host':'attacker.example'}).status_code==400
    assert c.post('/api/chat',headers={'Origin':'https://attacker.example'},json={'question':'test'}).status_code==403
