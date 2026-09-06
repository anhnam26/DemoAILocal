import json,time
from fastapi.testclient import TestClient
import app,accounts,system_runtime
from test_app import isolated_db,client
from testing_accounts import credentials

def test_password_login_replaces_role_selection():
    c=TestClient(app.app)
    assert c.post('/api/login',json={'profile':'admin'}).status_code==422
    assert c.post('/api/login',json={'username':'admin','password':'wrong'}).status_code==401
    a=client('admin');assert a.get('/api/me').json()['role']=='admin'
    with app.connect() as db:
        row=db.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
        assert row[0].startswith('scrypt$') and credentials('admin')['password'] not in row[0]
        token=db.execute('SELECT token FROM sessions').fetchone()[0]
        assert token!=a.cookies.get('cyberant_session') and len(token)==64

def test_admin_create_update_revoke_and_last_admin():
    a=client('admin');s=client('sale')
    payload=dict(username='qa_tester',name='QA User',role='technical',customers=['B'],password='Testing-Strong-Pass-123',active=True)
    assert s.post('/api/admin/users',json=payload).status_code==403
    r=a.post('/api/admin/users',json=payload);assert r.status_code==200
    id=r.json()['id'];qa=TestClient(app.app);assert qa.post('/api/login',json={'username':'qa_tester','password':payload['password']}).status_code==200
    assert qa.get('/api/documents/CASE-B').status_code==200
    assert qa.get('/api/documents/CASE-A').status_code==200
    sessions=a.get('/api/admin/users').json()['sessions'];sid=next(x['sid'] for x in sessions if x['user_id']==id)
    assert a.delete('/api/admin/sessions/'+sid).status_code==200
    assert qa.get('/api/me').status_code==401
    qa.post('/api/login',json={'username':'qa_tester','password':payload['password']})
    assert a.put('/api/admin/users/'+id,json={**payload,'active':False,'password':None}).status_code==200
    assert qa.get('/api/me').status_code==401
    assert qa.post('/api/login',json={'username':'qa_tester','password':payload['password']}).status_code==401
    admin=a.get('/api/me').json()
    r=a.put('/api/admin/users/'+admin['id'],json=dict(username='admin',name='Admin',role='sale',customers=['A'],active=True))
    assert r.status_code==400 and a.get('/api/me').status_code==200

def test_presence_expiry_and_password_reset():
    a=client('admin');s=client('sale');me=s.get('/api/me').json()
    assert s.post('/api/heartbeat').status_code==200
    assert any(u['online'] for u in a.get('/api/admin/users').json()['users'] if u['id']==me['id'])
    with app.connect() as db:db.execute('UPDATE sessions SET last_seen=? WHERE user_id=?',(time.time()-100,me['id']))
    assert not next(u for u in a.get('/api/admin/users').json()['users'] if u['id']==me['id'])['online']
    password=a.post('/api/admin/users/'+me['id']+'/reset-password').json()['temporary_password']
    assert s.get('/api/me').status_code==401
    assert s.post('/api/login',json=credentials('sale')).status_code==401
    assert s.post('/api/login',json={'username':'sales','password':password}).status_code==200

def test_system_permissions_settings_and_model_busy(tmp_path,monkeypatch):
    a=client('admin');s=client('sale');monkeypatch.setattr(system_runtime,'CONFIG',tmp_path/'runtime.json')
    assert s.get('/api/admin/system').status_code==403
    assert s.get('/api/admin/system/logs').status_code==403
    assert s.get('/api/admin/conversations').status_code==403
    r=a.put('/api/admin/system/config',json={**system_runtime.DEFAULT,'context':-1});assert r.status_code==422
    r=a.put('/api/admin/system/config',json={**system_runtime.DEFAULT,'temperature':0.3});assert r.status_code==200
    assert system_runtime.config()['temperature']==0.3
    monkeypatch.setattr(app.LOCK,'active',1)
    assert a.post('/api/admin/system/model',json={'action':'restart'}).status_code==409
    assert a.put('/api/admin/system/config',json=system_runtime.DEFAULT).status_code==409

def test_login_rate_limit():
    c=TestClient(app.app)
    for _ in range(8):assert c.post('/api/login',json={'username':'missing','password':'nope'}).status_code==401
    assert c.post('/api/login',json={'username':' MISSING ','password':'nope'}).status_code==429

