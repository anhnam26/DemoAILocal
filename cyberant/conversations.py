"""Persistent conversations owned by accounts, independent of login sessions."""
import json,secrets,hashlib,re
from fastapi import APIRouter,HTTPException,Request,Query

def init(connect):
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,title TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL)')
        for table in ('chats','sessions'):
            if 'conversation_id' not in {r[1] for r in c.execute('PRAGMA table_info('+table+')')}:
                c.execute('ALTER TABLE '+table+' ADD COLUMN conversation_id TEXT')
        c.execute('UPDATE chats SET user_id=(SELECT user_id FROM sessions WHERE sessions.token=chats.session) WHERE user_id IS NULL')
        rows=c.execute('SELECT * FROM chats WHERE user_id IS NOT NULL AND conversation_id IS NULL ORDER BY id').fetchall()
        groups={}
        for r in rows:
            key=(r['user_id'],r['session'])
            if key not in groups:
                id=secrets.token_hex(12);groups[key]=id
                c.execute('INSERT INTO conversations VALUES(?,?,?,?,?)',(id,r['user_id'],r['question'][:100],r['ts'],r['ts']))
            id=groups[key]
            c.execute('UPDATE chats SET conversation_id=? WHERE id=?',(id,r['id']))
            c.execute('UPDATE conversations SET updated=? WHERE id=?',(r['ts'],id))
        c.execute('CREATE INDEX IF NOT EXISTS chats_conversation ON chats(conversation_id,id)')
        c.execute('CREATE INDEX IF NOT EXISTS conversations_owner ON conversations(user_id,updated)')

def create(connect,u,now):
    id=secrets.token_hex(12);stamp=now()
    with connect() as c:
        c.execute('INSERT INTO conversations VALUES(?,?,?,?,?)',(id,u['id'],'Cuộc trò chuyện mới',stamp,stamp))
        c.execute('UPDATE sessions SET conversation_id=? WHERE token=?',(id,u['token']))
    return id

def resolve(connect,u,id,now):
    if not id:
        with connect() as c:
            row=c.execute('SELECT conversation_id FROM sessions WHERE token=?',(u['token'],)).fetchone()
        id=row['conversation_id'] if row else None
        if not id:id=create(connect,u,now)
    with connect() as c:r=c.execute('SELECT * FROM conversations WHERE id=? AND user_id=?',(id,u['id'])).fetchone()
    if not r:raise HTTPException(404,'Không tìm thấy cuộc trò chuyện của tài khoản này.')
    return id

def messages(connect,u,id,docs_for,before=None):
    with connect() as c:
        if not c.execute('SELECT 1 FROM conversations WHERE id=? AND user_id=?',(id,u['id'])).fetchone():raise HTTPException(404,'Không tìm thấy cuộc trò chuyện của tài khoản này.')
        rows=c.execute('SELECT * FROM chats WHERE conversation_id=? AND user_id=? AND id<? ORDER BY id DESC LIMIT 101',(id,u['id'],before or 9223372036854775807)).fetchall()
    more=len(rows)>100;rows=rows[:100];allowed={d['id']:hashlib.sha256(d['body'].encode()).hexdigest() for d in docs_for(u,shared=True)};result=[]
    for r in reversed(rows):
        d=json.loads(r['result'])
        if any(s['id'] not in allowed or s.get('source_digest',allowed.get(s['id']))!=allowed.get(s['id']) for s in d['sources']+d.get('context_sources',[])):d.update(answer='Nguồn đã thay đổi, thu hồi hoặc hết hiệu lực. Hãy hỏi lại từ nguồn hiện tại.',sources=[],web_sources=[],needs_review=True,citations_verified=False)
        result.append(dict(**d,question=r['question'],chat_id=r['id'],ts=r['ts'],conversation_id=id))
    return dict(messages=result,has_more=more,next_before=rows[-1]['id'] if rows else None)

def context(connect,u,id,documents,limit=80):
    """Only this owner's conversation; revoked/changed evidence never enters prompts."""
    allowed={d['id']:hashlib.sha256(d['body'].encode()).hexdigest() for d in documents}
    with connect() as c:
        if not c.execute('SELECT 1 FROM conversations WHERE id=? AND user_id=?',(id,u['id'])).fetchone():
            raise HTTPException(404,'Không tìm thấy cuộc trò chuyện của tài khoản này.')
        rows=c.execute('SELECT id,question,result FROM chats WHERE conversation_id=? AND user_id=? ORDER BY id DESC LIMIT ?',
                       (id,u['id'],limit)).fetchall()
    result=[]
    for row in reversed(rows):
        prior=json.loads(row['result'])
        dependencies=prior.get('sources',[])+prior.get('context_sources',[])
        if any(s['id'] not in allowed or s.get('source_digest')!=allowed[s['id']] for s in dependencies):
            continue
        if prior.get('citation_status')=='invalid':continue
        # Old citations are historical mappings, not fresh evidence for this turn.
        from cyberant import web_search
        answer=prior['answer']
        for s in prior.get('web_sources',[]):
            if isinstance(s,dict) and isinstance(s.get('id'),str) and web_search.safe_url(s.get('url')):
                answer=answer.replace('['+s['id']+']','(nguồn web lịch sử: '+s['url']+'; tra cứu '+str(s.get('retrieved_at','không rõ'))+'; chưa tra cứu lại)')
        answer=re.sub(r'\[WEB-[A-Za-z0-9_-]+\]','(nguồn web lịch sử không có ánh xạ; chưa xác minh)',answer)
        result.append(dict(chat_id=row['id'],question=row['question'],answer=answer,
                           effective_query=prior.get('effective_query',row['question']),sources=dependencies))
    return result

def install(app,connect,user,docs_for,now,active_conversations,audit):
    router=APIRouter()
    @router.get('/api/conversations')
    def listing(req:Request,offset:int=Query(0,ge=0),q:str=Query('',max_length=100)):
        u=user(req)
        with connect() as c:
            rows=c.execute('SELECT cv.*,COUNT(ch.id) AS message_count FROM conversations cv LEFT JOIN chats ch ON ch.conversation_id=cv.id WHERE cv.user_id=? AND instr(lower(cv.title),lower(?))>0 GROUP BY cv.id ORDER BY cv.updated DESC,cv.id LIMIT 51 OFFSET ?',(u['id'],q,offset)).fetchall()
        return dict(items=[dict(r) for r in rows[:50]],has_more=len(rows)>50,next_offset=offset+50)
    @router.post('/api/conversations')
    def new(req:Request):return dict(id=create(connect,user(req),now))
    @router.get('/api/conversations/{id}')
    def detail(id:str,req:Request,before:int|None=Query(None,ge=1)):
        u=user(req);resolve(connect,u,id,now)
        return dict(id=id,**messages(connect,u,id,docs_for,before))
    @router.delete('/api/conversations/{id}')
    async def delete(id:str,req:Request):
        u=user(req);resolve(connect,u,id,now)
        if id in active_conversations:raise HTTPException(409,'Cuộc trò chuyện đang xử lý câu hỏi. Hãy chờ hoàn tất rồi xóa.')
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM conversations WHERE id=? AND user_id=?',(id,u['id'])).fetchone():raise HTTPException(404,'Cuộc trò chuyện không còn tồn tại.')
            c.execute('DELETE FROM quality_reports WHERE chat_id IN (SELECT id FROM chats WHERE conversation_id=?)',(id,))
            c.execute('DELETE FROM feedback WHERE chat_id IN (SELECT id FROM chats WHERE conversation_id=?)',(id,))
            c.execute('DELETE FROM chats WHERE conversation_id=?',(id,))
            c.execute('UPDATE sessions SET conversation_id=NULL WHERE conversation_id=?',(id,))
            c.execute('DELETE FROM conversations WHERE id=? AND user_id=?',(id,u['id']))
        audit('conversation_delete',u['role'],id)
        return dict(ok=True,id=id)
    app.include_router(router)
