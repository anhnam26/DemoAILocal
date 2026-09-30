import json
import app,quality_feedback,model_provider
from test_app import isolated_db,client


def test_snapshot_duplicates_history_review_and_delete():
    m,a=client(),client('admin');r=m.post('/api/chat',json={'question':'DNS là gì?'}).json()
    data=dict(chat_id=r['chat_id'],rating=-1,reason='off_topic',comment='<script>not executable</script>',answer='forged')
    response=m.post('/api/feedback',json=data);assert response.status_code==200,response.text
    id=response.json()['id'];path='/api/admin/feedback/'+str(id)
    assert m.post('/api/feedback',json=data).json()['duplicate']
    assert m.get('/api/admin/feedback').status_code==403
    assert m.get(path).status_code==403
    assert m.put(path,json={'status':'resolved'}).status_code==403
    assert m.delete(path).status_code==403
    assert a.post('/api/feedback',json=data).status_code==404
    detail=a.get(path).json();assert detail['snapshot']['answer']==r['answer']
    assert detail['snapshot']['diagnostics']['usage_record_id']==r['diagnostics']['usage_record_id']
    assert len(detail['history'])==1
    assert m.post('/api/feedback',json={**data,'rating':1,'reason':''}).status_code==200
    assert a.put(path,json={'status':'resolved','note':'Reviewed source'}).status_code==200
    detail=a.get(path).json();assert len(detail['history'])==3 and detail['status']=='resolved'
    assert len(a.get('/api/admin/feedback?status=resolved&rating=1&q=member&model=test/model').json()['items'])==1
    assert a.get('/api/admin/feedback?status=new').json()['items']==[]
    assert m.delete('/api/conversations/'+r['conversation_id']).status_code==200
    assert a.get(path).status_code==404
    assert m.get('/api/account/usage').json()['used_tokens']>0


def test_revoked_snapshot_and_purge():
    m,a=client(),client('admin');r=m.post('/api/chat',json={'question':'DNS là gì?'}).json()
    id=m.post('/api/feedback',json={'chat_id':r['chat_id'],'rating':-1}).json()['id']
    a.post('/api/admin/documents/'+r['sources'][0]['id']+'/retire')
    path='/api/admin/feedback/'+str(id);s=a.get(path).json()['snapshot']
    assert s['source_redacted'] and not s['sources'] and s['answer']!=r['answer']
    assert a.delete(path).status_code==200
    quality_feedback.init(app.connect)
    assert a.get(path).status_code==404
    with app.connect() as c:assert c.execute('SELECT COUNT(*) FROM chats').fetchone()[0]==1


def test_legacy_migration_idempotent_and_missing_metadata():
    m,a=client(),client('admin');r=m.post('/api/chat',json={'question':'DNS là gì?'}).json()
    with app.connect() as c:
        c.execute('DELETE FROM quality_migrations')
        old={'answer':'Historical answer','sources':[]}
        c.execute('UPDATE chats SET result=? WHERE id=?',(json.dumps(old),r['chat_id']))
        for rating in (-1,1):c.execute('INSERT INTO feedback(chat_id,rating,ts) VALUES(?,?,?)',(r['chat_id'],rating,app.now()))
    quality_feedback.init(app.connect);quality_feedback.init(app.connect)
    rows=a.get('/api/admin/feedback').json()['items'];assert len(rows)==1
    detail=a.get('/api/admin/feedback/'+str(rows[0]['id'])).json()
    assert detail['rating']==1 and len(detail['history'])==2
    assert 'diagnostics' in detail['snapshot']['metadata_missing']
    with app.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]==2
        assert json.loads(c.execute('SELECT result FROM chats').fetchone()[0])==old


def test_invalid_report_and_pagination():
    m,a=client(),client('admin')
    assert m.post('/api/feedback',json={'chat_id':1,'rating':5}).status_code==422
    assert m.post('/api/feedback',json={'chat_id':1,'rating':-1,'reason':'unknown'}).status_code==422
    with app.connect() as c:
        for i in range(51):
            c.execute('INSERT INTO quality_reports(chat_id,rating,reason,comment,created,updated,snapshot,history) VALUES(?,1,\'\',\'\',\'a\',\'a\',?,\'[]\')',(100+i,json.dumps({'question':'q','username':'member'})))
    first=a.get('/api/admin/feedback').json();assert len(first['items'])==50 and first['has_more']
    second=a.get('/api/admin/feedback?offset=50').json();assert len(second['items'])==1 and not second['has_more']


def test_diagnostics_and_no_rejected_reasoning(monkeypatch):
    async def reply(*args):return '<think>private hidden</think>Rejected [UNKNOWN]',{'prompt_tokens':23,'completion_tokens':12},'stop'
    monkeypatch.setattr(model_provider,'complete',reply)
    m=client();r=m.post('/api/chat',json={'question':'DNS là gì?'}).json();d=r['diagnostics']
    assert d['citation_errors']==['unknown_source_ids'] and d['sent_sources']
    assert d['app_version']==app.APP_VERSION and len(d['prompt_hash'])==64
    assert d['usage']['prompt_tokens']==23 and d['usage_record_id']
    with app.connect() as c:
        saved=c.execute('SELECT result FROM chats').fetchone()[0]
        assert 'private hidden' not in saved and 'Rejected' not in saved
        assert c.execute('SELECT status FROM token_usage WHERE id=?',(d['usage_record_id'],)).fetchone()[0]=='completed'
