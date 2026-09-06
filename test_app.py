from testing_accounts import credentials,browser_login
import json
import pytest
from fastapi.testclient import TestClient
import app

@pytest.fixture(autouse=True)
def isolated_db(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'DB',tmp_path/'test.sqlite3');app.init()
def client(role):
    c=TestClient(app.app);assert c.post('/api/login',json=credentials(role)).status_code==200;return c
def test_role_and_customer_boundary():
    sale=client('sale');tech=client('technical')
    assert sale.get('/api/documents/CASE-B').status_code==200
    assert sale.get('/api/documents/TECH-MOP').status_code==200
    assert sale.get('/api/documents/CASE-A').status_code==200
    assert tech.get('/api/documents/CASE-A').status_code==200
    assert tech.get('/api/documents/TECH-MOP').status_code==200
    ids={d['id'] for d in app.retrieve('BINHAN-PRIVATE-BETA backup Binh An',dict(role='sale',customer='A'))}
    assert 'CASE-B' in ids
    assert sale.get('/api/admin').status_code==403
def test_service_estimation_removed():
    c=client('sale')
    assert c.post('/api/estimate',json={}).status_code==404
    assert c.get('/api/estimate/templates').status_code==404
    assert c.get('/api/estimates').status_code==404

def test_no_model_call_for_unsupported_commitment(monkeypatch):
    c=client('sale')
    r=c.post('/api/chat',json={'question':'Cam kết hoàn thành trong 2 ngày và miễn phí được không?'}).json()
    assert r['needs_review'] and r['mode']=='Quy tắc nghiệp vụ'
    assert 'DEMO' in r['answer']
def test_upload_approval_and_revocation():
    admin=client('admin');sale=client('sale')
    data='TAI LIEU MAU MOI. Pham vi dich vu khoa dao tao demo va quy trinh ban giao.'
    r=admin.post('/api/admin/upload',files={'file':('sample.md',data.encode(),'text/markdown')},data={'audience':'all'})
    assert r.status_code==200;id=r.json()['id']
    assert sale.get('/api/documents/'+id).status_code==404
    assert admin.post(f'/api/admin/documents/{id}/approve').status_code==200
    assert sale.get('/api/documents/'+id).status_code==200
    assert admin.post(f'/api/admin/documents/{id}/retire').status_code==200
    assert sale.get('/api/documents/'+id).status_code==404
def test_session_isolation_and_origin():
    a=client('sale');b=client('technical')
    r=a.post('/api/chat',json={'question':'Báo giá bao nhiêu tiền?'}).json()
    assert len(a.get('/api/history').json())==1
    assert b.get('/api/history').json()==[]
    assert b.post('/api/feedback',json={'chat_id':r['chat_id'],'rating':1}).status_code==404
    assert a.post('/api/estimate',headers={'Origin':'https://evil.example'},json={}).status_code==403
    a.post('/api/logout');assert a.get('/api/documents').status_code==401

def test_expired_source_excluded_and_history_redacted():
    c=client('sale')
    result=c.post('/api/chat',json={'question':'Cam kết số ngày thi công firewall bao nhiêu?'}).json()
    assert result['sources']
    id=result['sources'][0]['id']
    with app.connect() as db:
        d=json.loads(db.execute('SELECT payload FROM docs WHERE id=?',(id,)).fetchone()['payload'])
        d['valid_to']='2020-01-01'
        db.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps(d),id))
    assert c.get('/api/documents/'+id).status_code==404
    assert id not in {d['id'] for d in app.retrieve('firewall thi cong',dict(role='sale',customer='A'))}
    history=c.get('/api/history').json()
    assert history[-1]['sources']==[] and 'hết hiệu lực' in history[-1]['answer']

def test_general_question_does_not_inject_customer_record():
    found=app.retrieve('Firewall mạng và WAF khác nhau như thế nào?',dict(role='sale',customer='A'))
    assert not any(d.get('customer') for d in found)
    assert any(d['id']=='SV-WAF' for d in found)
