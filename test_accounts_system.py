from fastapi.testclient import TestClient
import app,system_runtime
from test_app import isolated_db,client

def test_user_lifecycle_and_admin_boundary():
    a,m=client('admin'),client()
    payload=dict(username='qa_member',name='QA Member',role='member',password='ValidPassword-123',customers=[])
    assert m.post('/api/admin/users',json=payload).status_code==403
    r=a.post('/api/admin/users',json=payload);assert r.status_code==200;id=r.json()['id']
    c=TestClient(app.app);assert c.post('/api/login',json={'username':'qa_member','password':payload['password']}).status_code==200
    assert a.put('/api/admin/users/'+id,json={**payload,'active':False}).status_code==200
    assert c.get('/api/me').status_code==401
    assert a.post('/api/admin/users',json={**payload,'username':'legacy','role':'sale'}).status_code==400
    me=a.get('/api/me').json()
    assert a.put('/api/admin/users/'+me['id'],json={**payload,'username':'admin','role':'member'}).status_code==400

def test_login_rate_limit():
    c=TestClient(app.app)
    for _ in range(8):assert c.post('/api/login',json={'username':'missing','password':'nope'}).status_code==401
    assert c.post('/api/login',json={'username':' MISSING ','password':'nope'}).status_code==429

def test_admin_config_and_provider_boundary(tmp_path,monkeypatch):
    a,m=client('admin'),client();monkeypatch.setattr(system_runtime,'CONFIG',tmp_path/'config.json')
    assert m.get('/api/admin/system').status_code==403
    assert m.put('/api/admin/system/provider',json={'mode':'local'}).status_code==403
    assert a.post('/api/admin/system/model',json={'action':'start'}).status_code==400
    assert a.put('/api/admin/system/config',json={**system_runtime.DEFAULT,'context':-1}).status_code==422
    assert a.put('/api/admin/system/provider',json={'mode':'invalid'}).status_code==400
    monkeypatch.setenv('LLM_MODE','local');monkeypatch.setattr(app.LOCK,'active',1)
    assert a.post('/api/admin/system/model',json={'action':'restart'}).status_code==409
