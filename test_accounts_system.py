from fastapi.testclient import TestClient
import app
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

def test_admin_system_permissions_and_removed_local():
    a,m=client('admin'),client()
    assert m.get('/api/admin/system').status_code==403
    assert m.get('/api/admin/usage').status_code==403
    assert a.get('/api/admin/system').status_code==200
    assert a.post('/api/admin/system/model',json={'action':'start'}).status_code==404
    assert a.put('/api/admin/system/provider',json={'mode':'local'}).status_code==404

def test_production_bootstrap_and_backup(tmp_path,monkeypatch):
    import sqlite3,accounts,config
    from fastapi.testclient import TestClient
    state=tmp_path/'production';state.mkdir()
    monkeypatch.setattr(app,'DB',state/'app.sqlite3')
    monkeypatch.setattr(accounts,'BOOTSTRAP',state/'initial-accounts.json')
    monkeypatch.setenv('APP_DATA_DIR',str(state))
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('APP_ORIGINS','https://knowledge.example.com')
    monkeypatch.setenv('BOOTSTRAP_ADMIN_USERNAME','production_admin')
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD','Production-test-password-567')
    app.init()
    assert not accounts.BOOTSTRAP.exists()
    with app.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==1
    c=TestClient(app.app,base_url='https://knowledge.example.com')
    assert c.post('/api/login',json={'username':'production_admin','password':'Production-test-password-567'}).status_code==200
    r=c.post('/api/admin/system/backup');assert r.status_code==200
    snapshot=state/'backups'/r.json()['path'].split('/')[-1]
    with sqlite3.connect(snapshot) as restored:
        assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert restored.execute('SELECT COUNT(*) FROM docs').fetchone()[0]>1000
        assert restored.execute('SELECT username FROM users').fetchone()[0]=='production_admin'
