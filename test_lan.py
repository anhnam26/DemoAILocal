import json
import pytest
from fastapi.testclient import TestClient
import accounts,app,config
from test_app import isolated_db,client

LAN='http://192.168.1.50:8088'

def test_lan_login_cookie_origin_and_full_session(monkeypatch):
    monkeypatch.setenv('APP_ENV','lan');monkeypatch.setenv('APP_ORIGINS',LAN)
    with TestClient(app.app,base_url=LAN) as c:
        r=c.post('/api/login',headers={'Origin':LAN},json={'username':'member','password':'Test-password-12345'})
        assert r.status_code==200 and 'Secure' not in r.headers['set-cookie']
        assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
        assert c.get('/api/me').status_code==200
        assert c.get('/api/documents').status_code==200
        r=c.post('/api/chat',headers={'Origin':LAN},json={'question':'DNS là gì?'});assert r.status_code==200,r.text
        chat=r.json();assert c.get('/api/conversations/'+chat['conversation_id']).status_code==200
        assert c.post('/api/feedback',json={'chat_id':chat['chat_id'],'rating':1}).status_code==200
        assert c.get('/api/admin/feedback').status_code==403
        assert c.post('/api/chat',headers={'Origin':'http://192.168.1.51:8088'},json={'question':'DNS là gì?'}).status_code==403
        assert c.get('/api/me',headers={'Host':'attacker.example'}).status_code==400
        assert c.post('/api/logout').status_code==200
        assert c.get('/api/me').status_code==401

@pytest.mark.parametrize('mode,origin',[
 ('typo',LAN),('production',LAN),('lan','http://8.8.8.8:8088'),
 ('lan','http://0.0.0.0:8088'),('lan','http://example.com'),
 ('lan','http://192.168.1.50:8088/path'),('lan','http://user:password@192.168.1.50'),
 ('lan','http://192.168.1.50?x=1'),('lan','http://192.168.1.50#fragment'),
 ('development','http://*.example.com'),('lan','http://192.168.1.50:99999')])
def test_invalid_security_fails_closed(monkeypatch,mode,origin):
    monkeypatch.setenv('APP_ENV',mode);monkeypatch.setenv('APP_ORIGINS',origin)
    with pytest.raises(ValueError):config.security()

@pytest.mark.parametrize('mode',['lan','production'])
def test_server_bootstrap_ignores_development_password_file(tmp_path,monkeypatch,mode):
    monkeypatch.setattr(app,'DB',tmp_path/'fresh.sqlite3')
    monkeypatch.setenv('APP_ENV',mode)
    monkeypatch.setenv('APP_ORIGINS',LAN if mode=='lan' else 'https://knowledge.example.com')
    monkeypatch.setenv('BOOTSTRAP_ADMIN_USERNAME','server_admin')
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD','')
    original=accounts.BOOTSTRAP.read_bytes()
    with pytest.raises(RuntimeError,match='BOOTSTRAP_ADMIN_PASSWORD'):app.init()
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD','Server-password-12345');app.init()
    with app.connect() as c:
        assert c.execute('SELECT username FROM users').fetchall()[0][0]=='server_admin'
        assert c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==1
    assert accounts.BOOTSTRAP.read_bytes()==original
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD','');app.init()  # Existing DB needs no bootstrap secret.


def test_password_change_revokes_other_sessions():
    a,b=client(),client()
    assert a.post('/api/account/password',json={'old_password':'wrong','new_password':'New-password-12345'}).status_code==400
    assert a.post('/api/account/password',json={'old_password':'Test-password-12345','new_password':'New-password-12345'}).status_code==200
    assert b.get('/api/me').status_code==401
    assert a.post('/api/login',json={'username':'member','password':'New-password-12345'}).status_code==200


def test_expired_session_denied():
    c=client()
    with app.connect() as db:db.execute('UPDATE sessions SET created=0')
    assert c.get('/api/me').status_code==401
