import asyncio,json
import pytest
from fastapi import HTTPException
import app
from generation import GenerationGate
from test_app import isolated_db,client

def test_history_ownership_followup_and_redaction():
    m,a=client(),client('admin');id=m.post('/api/conversations').json()['id']
    r=m.post('/api/chat',json={'question':'Firewall và WAF khác nhau thế nào?','conversation_id':id}).json()
    assert r['conversation_id']==id and r['sources']
    assert a.get('/api/conversations/'+id).status_code==404
    assert a.delete('/api/conversations/'+id).status_code==404
    follow=m.post('/api/chat',json={'question':'Lập bảng so sánh hai loại ở trên','conversation_id':id}).json()
    assert 'Chủ đề trước' in follow['effective_query']
    a.post('/api/admin/documents/'+r['sources'][0]['id']+'/retire')
    history=m.get('/api/conversations/'+id).json()['messages']
    assert history[0]['sources']==[] and 'thu hồi' in history[0]['answer']
    m.post('/api/logout');m.post('/api/login',json={'username':'member','password':'Test-password-12345'})
    assert len(m.get('/api/conversations/'+id).json()['messages'])==2

def test_delete_cascades_and_blocks_active():
    c=client();r=c.post('/api/chat',json={'question':'Khái niệm DNS là gì?'}).json();id=r['conversation_id']
    assert c.post('/api/feedback',json={'chat_id':r['chat_id'],'rating':1}).status_code==200
    app.ACTIVE_CONVERSATIONS.add(id)
    assert c.delete('/api/conversations/'+id).status_code==409
    app.ACTIVE_CONVERSATIONS.clear();assert c.delete('/api/conversations/'+id).status_code==200
    with app.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM chats').fetchone()[0]==0

def test_history_invalidates_source_revision():
    c=client();r=c.post('/api/chat',json={'question':'Khái niệm DNS là gì?'}).json()
    source_id=r['sources'][0]['id']
    with app.connect() as db:
        d=json.loads(db.execute('SELECT payload FROM docs WHERE id=?',(source_id,)).fetchone()[0])
        d['body']+='\nRevised technical guidance.'
        db.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps(d),source_id))
    message=c.get('/api/conversations/'+r['conversation_id']).json()['messages'][0]
    assert not message['sources'] and 'thay đổi' in message['answer']

def test_gate_parallel_and_cancel():
    async def exercise():
        g=GenerationGate();await g.enter(2);await g.enter(2)
        waiter=asyncio.create_task(g.enter(2));await asyncio.sleep(.06)
        assert g.active==2 and g.waiting==1
        with pytest.raises(HTTPException):await g.acquire()
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):await waiter
        assert g.waiting==0;g.leave();g.leave();await g.acquire()
        with pytest.raises(HTTPException):await g.enter(2)
        g.release()
    asyncio.run(exercise())
