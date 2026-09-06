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
    assert qa.get('/api/documents/CASE-A').status_code==404
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
    monkeypatch.setattr(app.LOCK,'_value',0)
    assert a.post('/api/admin/system/model',json={'action':'restart'}).status_code==409
    assert a.put('/api/admin/system/config',json=system_runtime.DEFAULT).status_code==409

def test_saved_estimate_workflow_and_acl():
    a=client('admin');s=client('sale');t=client('technical')
    d=s.get('/api/estimate/templates').json();assert len(d['templates'])==20
    template=next(x for x in d['templates'] if x['service_id']=='firewall')
    payload={k:v for k,v in template.items() if k not in ('id','title')}
    r=s.post('/api/estimates',json=payload);assert r.status_code==200,r.text
    e=r.json();assert e['payload']['total']==12000000 and e['payload']['effort']==4
    id=e['id'];assert not any(x['id']==id for x in t.get('/api/estimates').json())
    assert s.post('/api/estimates/'+id+'/transition',json={'action':'approve','note':'Không được phép'}).status_code==403
    assert s.post('/api/estimates/'+id+'/transition',json={'action':'submit'}).json()['status']=='submitted'
    assert a.post('/api/estimates/'+id+'/transition',json={'action':'approve','note':'PM xác nhận lịch và phạm vi demo'}).json()['status']=='approved'
    assert len(s.get('/api/estimates/'+id+'/events').json())==3
    assert a.post('/api/estimates/'+id+'/transition',json={'action':'approve','note':'Không duyệt lại'}).status_code==409
    r=s.post('/api/estimates',json={**payload,'readiness':False});assert r.json()['payload']['total'] is None and r.json()['status']=='needs_survey'
    assert s.post('/api/estimates',json={**payload,'customer_id':'B'}).status_code==403
    assert len(s.get('/api/catalog').json())==20

def test_login_rate_limit():
    c=TestClient(app.app)
    for _ in range(8):assert c.post('/api/login',json={'username':'missing','password':'nope'}).status_code==401
    assert c.post('/api/login',json={'username':' MISSING ','password':'nope'}).status_code==429

def test_estimate_cannot_approve_after_rate_changes():
    a=client('admin');s=client('sale')
    template=next(x for x in s.get('/api/estimate/templates').json()['templates'] if x['service_id']=='firewall')
    payload={k:v for k,v in template.items() if k not in ('id','title')}
    estimate=s.post('/api/estimates',json=payload).json();id=estimate['id']
    assert s.post('/api/estimates/'+id+'/transition',json={'action':'submit'}).status_code==200
    source=estimate['payload']['source_ids'][0]
    with app.connect() as db:
        doc=json.loads(db.execute('SELECT payload FROM docs WHERE id=?',(source,)).fetchone()[0])
        doc['service']['price']+=1000000
        db.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps(doc,ensure_ascii=False),source))
    assert not next(x for x in a.get('/api/estimates').json() if x['id']==id)['sources_current']
    assert a.post('/api/estimates/'+id+'/transition',json={'action':'approve','note':'Giá cũ không còn hiệu lực'}).status_code==409
    assert len(a.get('/api/estimates/'+id+'/events').json())==2
