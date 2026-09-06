import asyncio,json
import pytest
from fastapi import HTTPException
import app,conversations
from generation import GenerationGate
from test_app import isolated_db,client
from testing_accounts import credentials

def test_shared_knowledge_but_admin_operations_protected():
    sale=client('sale');tech=client('technical');admin=client('admin')
    ids=lambda c:{d['id'] for d in c.get('/api/documents').json()}
    assert ids(sale)==ids(tech)==ids(admin)
    for c in (sale,tech):
        assert c.get('/api/documents/COST-A-01').status_code==200
        assert c.get('/api/admin/system').status_code==403
        assert c.post('/api/admin/documents/COST-A-01/retire').status_code==403

def test_history_survives_login_and_is_owned_by_account():
    s=client('sale');t=client('technical');a=client('admin')
    id=s.post('/api/conversations').json()['id']
    first=s.post('/api/chat',json={'question':'Firewall mạng và WAF khác nhau như thế nào?','conversation_id':id}).json()
    assert first['conversation_id']==id
    s.post('/api/logout');s.post('/api/login',json=credentials('sale'))
    assert id in {x['id'] for x in s.get('/api/conversations').json()['items']}
    assert len(s.get('/api/conversations/'+id).json()['messages'])==1
    for other in (t,a):
        assert other.get('/api/conversations/'+id).status_code==404
        assert other.post('/api/chat',json={'question':'Hỏi tiếp nội dung cũ','conversation_id':id}).status_code==404
    follow=s.post('/api/chat',json={'question':'Tạo bảng so sánh hai cái đó','conversation_id':id}).json()
    assert 'Chủ đề trước:' in follow['effective_query']
    assert len(s.get('/api/conversations/'+id).json()['messages'])==2
    assert s.post('/api/feedback',json={'chat_id':first['chat_id'],'rating':1}).status_code==200
    fresh=s.post('/api/chat/reset').json()['conversation_id']
    assert fresh!=id and s.get('/api/history').json()==[]
    assert len(s.get('/api/conversations/'+id).json()['messages'])==2

def test_history_redaction_and_legacy_migration():
    s=client('sale');a=client('admin');answer=s.post('/api/chat',json={'question':'Cam kết triển khai firewall 2 ngày được không?'}).json();id=answer['conversation_id']
    a.post('/api/admin/documents/'+answer['sources'][0]['id']+'/retire')
    m=s.get('/api/conversations/'+id).json()['messages'][0]
    assert m['sources']==[] and 'thu hồi' in m['answer']
    with app.connect() as db:db.execute('UPDATE chats SET conversation_id=NULL WHERE id=?',(answer['chat_id'],))
    conversations.init(app.connect);conversations.init(app.connect)
    with app.connect() as db:
        migrated=db.execute('SELECT conversation_id FROM chats WHERE id=?',(answer['chat_id'],)).fetchone()[0]
        assert db.execute('SELECT COUNT(*) FROM chats WHERE conversation_id=?',(migrated,)).fetchone()[0]==1
    assert s.get('/api/conversations/'+migrated).status_code==200

def test_gate_parallel_queue_and_exclusive_maintenance():
    async def exercise():
        g=GenerationGate();await g.enter(2);await g.enter(2)
        waiter=asyncio.create_task(g.enter(2));await asyncio.sleep(.08)
        assert g.active==2 and g.waiting==1 and not waiter.done()
        with pytest.raises(HTTPException):await g.acquire()
        g.leave();await waiter;assert g.active==2 and g.waiting==0
        g.leave();g.leave();await g.acquire()
        with pytest.raises(HTTPException):await g.enter(2)
        g.release();await g.enter(2);g.leave()
        await g.enter(1);task=asyncio.create_task(g.enter(1));await asyncio.sleep(.06);task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert g.waiting==0 and g.active==1;g.leave()
    asyncio.run(exercise())

def test_history_pagination_has_no_duplicates():
    s=client('sale');id=s.post('/api/conversations').json()['id'];u=s.get('/api/me').json()
    payload=json.dumps(dict(answer='Nội dung mẫu',sources=[],needs_review=False,mode='DEMO',elapsed=0,citations_verified=False))
    with app.connect() as db:
        for i in range(105):db.execute('INSERT INTO chats(session,question,result,ts,user_id,conversation_id) VALUES(?,?,?,?,?,?)',('test','Q'+str(i),payload,app.now(),u['id'],id))
    page=s.get('/api/conversations/'+id).json();assert len(page['messages'])==100 and page['has_more']
    older=s.get('/api/conversations/'+id+'?before='+str(page['next_before'])).json();assert len(older['messages'])==5 and not older['has_more']
    ids=[m['chat_id'] for m in older['messages']+page['messages']];assert len(set(ids))==105 and ids==sorted(ids)

def test_explicit_financial_topic_does_not_reuse_old_topic():
    from business import context_query
    q='Xem công nợ Bình An Factory'
    assert context_query(q,'Lợi nhuận An Minh là bao nhiêu?')==q
    assert 'Chủ đề trước:' in context_query('Tạo bảng so sánh hai cái đó','Firewall và WAF khác nhau như thế nào?')
