"""Permission, migration and quota regressions; providers and databases are isolated."""
import json,sqlite3
import pytest
from fastapi import HTTPException
import app,model_provider,token_usage
from test_app import isolated_db,client

@pytest.fixture
def multi(monkeypatch):
    monkeypatch.setattr(model_provider,'models',lambda:['test/model','vendor/second'])
    member,admin=client(),client('admin');user=member.get('/api/me').json()
    payload=dict(username='member',name='Member',role='member',allowed_models=['test/model','vendor/second'],monthly_token_limit=100000)
    assert admin.put('/api/admin/users/'+user['id'],json=payload).status_code==200
    return member,admin,user,payload

def test_grants_selection_and_shared_history(multi):
    member,admin,user,payload=multi
    assert member.get('/api/model').json()['allowed_models']==payload['allowed_models']
    first=member.post('/api/chat',json={'question':'DNS là gì?','model':'test/model'}).json()
    assert member.put('/api/model',json={'model':'vendor/second'}).status_code==200
    second=member.post('/api/chat',json={'question':'DNS là gì?','conversation_id':first['conversation_id']}).json()
    assert second['model']=='vendor/second' and second['conversation_id']==first['conversation_id']
    assert member.get('/api/account/usage').json()['used_tokens']==1080
    assert len(member.get('/api/conversations/'+first['conversation_id']).json()['messages'])==2
    assert client().get('/api/model').json()['model']=='vendor/second'
    assert member.put('/api/model',json={'model':'not/granted'}).status_code==403
    assert member.put('/api/admin/users/'+user['id'],json=payload).status_code==403
    assert admin.put('/api/admin/users/'+user['id'],json={**payload,'allowed_models':[]}).status_code==400
    assert admin.put('/api/admin/users/'+user['id'],json={**payload,'allowed_models':['not/configured']}).status_code==400
    assert admin.put('/api/admin/users/'+user['id'],json={**payload,'model':'not/granted'}).status_code==400
    assert admin.put('/api/admin/users/'+user['id'],json={**payload,'allowed_models':payload['allowed_models']*2}).status_code==200
    assert member.get('/api/me').json()['allowed_models']==payload['allowed_models']
    # Admin save must preserve a member's selected default, not reset to first grant.
    assert member.get('/api/model').json()['model']=='vendor/second'

def test_revoked_default_requires_explicit_selection(multi,monkeypatch):
    member,admin,user,payload=multi
    assert admin.put('/api/admin/users/'+user['id'],json={**payload,'allowed_models':['vendor/second']}).status_code==200
    state=member.get('/api/model').json()
    assert state['model']=='' and not state['configured']
    token_usage.init(app.connect)
    assert member.get('/api/model').json()['model']==''
    assert member.post('/api/chat',json={'question':'DNS là gì?'}).status_code==403
    assert member.put('/api/model',json={'model':'vendor/second'}).status_code==200
    monkeypatch.setattr(model_provider,'models',lambda:[])
    assert member.get('/api/model').json()['allowed_models']==[]
    assert member.post('/api/chat',json={'question':'DNS là gì?'}).status_code==409
    assert member.put('/api/model',json={'model':'vendor/second'}).status_code==409

def test_default_change_does_not_cancel_authorized_reservation(multi):
    member,_,user,_=multi
    reservation,_=token_usage.reserve(app.connect,user['id'],'test/model',600,200)
    assert member.put('/api/model',json={'model':'vendor/second'}).status_code==200
    token_usage.mark_sent(app.connect,reservation)
    token_usage.settle(app.connect,reservation,{'prompt_tokens':100,'completion_tokens':20})
    other,_=token_usage.reserve(app.connect,user['id'],'vendor/second',600,200)
    token_usage.mark_sent(app.connect,other)
    token_usage.settle(app.connect,other,{'prompt_tokens':100,'completion_tokens':20})
    assert token_usage.summary(app.connect,user['id'])['used_tokens']==240

@pytest.mark.parametrize('change',['revoke','remove_config','disable','quota'])
def test_dispatch_rechecks_and_cleans_reservations(multi,monkeypatch,change):
    member,_,user,_=multi
    original=token_usage.mark_sent
    def changed(connect,reservation):
        with connect() as db:
            if change=='revoke':db.execute('UPDATE users SET allowed_models=? WHERE id=?',(json.dumps(['vendor/second']),user['id']))
            elif change=='disable':db.execute('UPDATE users SET active=0 WHERE id=?',(user['id'],))
            elif change=='quota':db.execute('UPDATE users SET monthly_token_limit=0 WHERE id=?',(user['id'],))
        if change=='remove_config':monkeypatch.setattr(model_provider,'models',lambda:['vendor/second'])
        original(connect,reservation)
    async def forbidden(*args):pytest.fail('Revoked request reached provider')
    monkeypatch.setattr(token_usage,'mark_sent',changed)
    monkeypatch.setattr(model_provider,'complete',forbidden)
    result=member.post('/api/chat',json={'question':'DNS là gì?','model':'test/model'})
    assert result.status_code in (403,409,429)
    usage=token_usage.summary(app.connect,user['id'])
    assert usage['reserved_tokens']==usage['used_tokens']==usage['uncertain_tokens']==0
    with app.connect() as db:assert db.execute('SELECT status FROM token_usage').fetchone()[0]=='cancelled'

@pytest.mark.parametrize('grants',[[],['vendor/second']])
def test_reservation_cannot_bypass_grants(multi,grants):
    _,_,user,_=multi
    with app.connect() as db:db.execute('UPDATE users SET allowed_models=? WHERE id=?',(json.dumps(grants),user['id']))
    with pytest.raises(HTTPException) as error:token_usage.reserve(app.connect,user['id'],'test/model',600,200)
    assert error.value.status_code==403


def test_legacy_migration_preserves_account_and_usage(tmp_path,monkeypatch):
    path=tmp_path/'legacy.sqlite3'
    def connect():
        db=sqlite3.connect(path);db.row_factory=sqlite3.Row;return db
    monkeypatch.setattr(model_provider,'models',lambda:['new/default'])
    with connect() as db:
        db.executescript('''CREATE TABLE users(id TEXT PRIMARY KEY,model TEXT,monthly_token_limit INTEGER,password_hash TEXT);
            CREATE TABLE sessions(token TEXT,user_id TEXT);
            CREATE TABLE chats(id INTEGER PRIMARY KEY,user_id TEXT,result TEXT,ts TEXT);''')
        db.execute('INSERT INTO users VALUES(?,?,?,?)',('owner','old/removed',1234,'unchanged-hash'))
        db.execute('INSERT INTO sessions VALUES(?,?)',('keep-session','owner'))
        result=json.dumps({'model':'old/removed','usage':{'prompt_tokens':100,'completion_tokens':20}})
        db.execute('INSERT INTO chats VALUES(?,?,?,?)',(1,'owner',result,'2026-09-01T00:00:00+00:00'))
    token_usage.init(connect);token_usage.init(connect)
    with connect() as db:
        row=db.execute('SELECT * FROM users').fetchone()
        assert json.loads(row['allowed_models'])==['old/removed']
        assert row['model']=='old/removed' and row['password_hash']=='unchanged-hash' and row['monthly_token_limit']==1234
        assert db.execute('SELECT token FROM sessions').fetchone()[0]=='keep-session'
        assert db.execute('SELECT result FROM chats').fetchone()[0]==result
        assert db.execute('SELECT COUNT(*),SUM(total_tokens) FROM token_usage').fetchone()[:]==(1,120)
        db.execute("UPDATE users SET allowed_models='[]',model=''")
    token_usage.init(connect)
    with connect() as db:assert tuple(db.execute('SELECT allowed_models,model FROM users').fetchone())==('[]','')
