"""Server-derived quality reports; no rejected model output or internal reasoning."""
import hashlib,json
from typing import Literal
from fastapi import APIRouter,HTTPException,Request,Query
from pydantic import BaseModel,Field

class Feedback(BaseModel):
    chat_id:int=Field(gt=0)
    rating:Literal[-1,0,1]
    reason:Literal['','incorrect','off_topic','missing_evidence','incomplete','other']=''
    comment:str=Field(default='',max_length=1000)

class Review(BaseModel):
    status:Literal['new','reviewing','resolved','dismissed']
    note:str=Field(default='',max_length=2000)

def snapshot(c,chat):
    result=json.loads(chat['result'])
    owner=c.execute('SELECT username,name FROM users WHERE id=?',(chat['user_id'],)).fetchone()
    return dict(question=chat['question'],answer=result.get('answer'),user_id=chat['user_id'],
        username=owner['username'] if owner else None,name=owner['name'] if owner else None,
        chat_id=chat['id'],conversation_id=chat['conversation_id'],chat_ts=chat['ts'],
        **{key:result.get(key) for key in ('model','usage','sources','diagnostics','citation_status','finish_reason','mode')},
        metadata_missing=[key for key in ('model','usage','diagnostics','citation_status','finish_reason') if key not in result])

def init(connect):
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS quality_reports(
            id INTEGER PRIMARY KEY,chat_id INTEGER NOT NULL UNIQUE,user_id TEXT,
            rating INTEGER NOT NULL,reason TEXT NOT NULL,comment TEXT NOT NULL,
            created TEXT NOT NULL,updated TEXT NOT NULL,snapshot TEXT NOT NULL,
            history TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'new',note TEXT NOT NULL DEFAULT '')''')
        c.execute('CREATE INDEX IF NOT EXISTS quality_reports_status ON quality_reports(status,updated)')
        c.execute('CREATE TABLE IF NOT EXISTS quality_migrations(name TEXT PRIMARY KEY)')
        if c.execute("SELECT 1 FROM quality_migrations WHERE name='legacy_feedback'").fetchone():return
        for old in c.execute('SELECT * FROM feedback ORDER BY id').fetchall():
            chat=c.execute('SELECT * FROM chats WHERE id=?',(old['chat_id'],)).fetchone()
            if not chat:continue  # Orphan originals remain intact; do not invent an owner/answer.
            previous=c.execute('SELECT history FROM quality_reports WHERE chat_id=?',(chat['id'],)).fetchone()
            history=json.loads(previous[0]) if previous else []
            history.append(dict(rating=old['rating'],ts=old['ts'],legacy=True,legacy_id=old['id']))
            c.execute('''INSERT INTO quality_reports(chat_id,user_id,rating,reason,comment,created,updated,snapshot,history)
                VALUES(?,?,?,'','',?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET
                rating=excluded.rating,updated=excluded.updated,history=excluded.history''',
                (chat['id'],chat['user_id'],old['rating'],old['ts'],old['ts'],json.dumps(snapshot(c,chat),ensure_ascii=False),json.dumps(history)))
        c.execute("INSERT INTO quality_migrations VALUES('legacy_feedback')")

def safe_snapshot(data,allowed):
    sources=data.get('sources') or []
    if any(s['id'] not in allowed or s.get('source_digest',allowed.get(s['id']))!=allowed.get(s['id']) for s in sources):
        data={**data,'answer':'Nguồn đã thay đổi, thu hồi hoặc hết hiệu lực.','sources':[],'source_redacted':True}
    return data

def submit(connect,u,data,now,docs_for):
    allowed={d['id']:hashlib.sha256(d['body'].encode()).hexdigest() for d in docs_for(u)}
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        chat=c.execute('SELECT * FROM chats WHERE id=? AND user_id=?',(data.chat_id,u['id'])).fetchone()
        if not chat:raise HTTPException(404,'Không tìm thấy lượt hỏi')
        row=c.execute('SELECT * FROM quality_reports WHERE chat_id=?',(data.chat_id,)).fetchone()
        if row and (row['rating'],row['reason'],row['comment'])==(data.rating,data.reason,data.comment):return dict(ok=True,id=row['id'],duplicate=True)
        stamp=now();history=json.loads(row['history']) if row else []
        history.append(dict(rating=data.rating,reason=data.reason,comment=data.comment,ts=stamp,user_id=u['id']))
        snap=safe_snapshot(snapshot(c,chat),allowed)
        c.execute('''INSERT INTO quality_reports(chat_id,user_id,rating,reason,comment,created,updated,snapshot,history)
            VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET rating=excluded.rating,
            reason=excluded.reason,comment=excluded.comment,updated=excluded.updated,history=excluded.history,status='new' ''',
            (data.chat_id,u['id'],data.rating,data.reason,data.comment,stamp,stamp,json.dumps(snap,ensure_ascii=False),json.dumps(history,ensure_ascii=False)))
        id=c.execute('SELECT id FROM quality_reports WHERE chat_id=?',(data.chat_id,)).fetchone()[0]
    return dict(ok=True,id=id,duplicate=False)


def install(app,connect,user,docs_for,now,audit):
    router=APIRouter()
    def admin(req):
        u=user(req)
        if u['role']!='admin':raise HTTPException(403,'Cần quyền quản trị.')
        return u
    @router.get('/api/admin/feedback')
    def listing(req:Request,offset:int=Query(0,ge=0),status:str=Query('',max_length=20),
                rating:int|None=Query(None,ge=-1,le=1),q:str=Query('',max_length=100),
                model:str=Query('',max_length=200),reason:str=Query('',max_length=30)):
        admin(req)
        with connect() as c:
            rows=c.execute('''SELECT id,chat_id,user_id,rating,reason,comment,created,updated,status,note,
                json_extract(snapshot,'$.question') AS question,json_extract(snapshot,'$.username') AS username,
                json_extract(snapshot,'$.model') AS model FROM quality_reports
                WHERE (?='' OR status=?) AND (? IS NULL OR rating=?) AND (?='' OR reason=?)
                AND (?='' OR json_extract(snapshot,'$.model')=?)
                AND instr(lower(coalesce(json_extract(snapshot,'$.question'),'')||' '||coalesce(json_extract(snapshot,'$.username'),'')),lower(?))>0
                ORDER BY updated DESC,id DESC LIMIT 51 OFFSET ?''',
                (status,status,rating,rating,reason,reason,model,model,q,offset)).fetchall()
        return dict(items=[dict(r) for r in rows[:50]],has_more=len(rows)>50,next_offset=offset+50,
                    retention='delete_with_conversation; explicit admin purge; backups managed separately')
    @router.get('/api/admin/feedback/{id}')
    def detail(id:int,req:Request):
        u=admin(req)
        with connect() as c:row=c.execute('SELECT * FROM quality_reports WHERE id=?',(id,)).fetchone()
        if not row:raise HTTPException(404,'Không có phản hồi.')
        allowed={d['id']:hashlib.sha256(d['body'].encode()).hexdigest() for d in docs_for(u)}
        return {**dict(row),'snapshot':safe_snapshot(json.loads(row['snapshot']),allowed),'history':json.loads(row['history'])}
    @router.put('/api/admin/feedback/{id}')
    def review(id:int,data:Review,req:Request):
        u=admin(req)
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT history FROM quality_reports WHERE id=?',(id,)).fetchone()
            if not row:raise HTTPException(404,'Không có phản hồi.')
            history=json.loads(row[0]);stamp=now()
            history.append(dict(status=data.status,note=data.note,admin_id=u['id'],ts=stamp))
            c.execute('UPDATE quality_reports SET status=?,note=?,updated=?,history=? WHERE id=?',
                (data.status,data.note,stamp,json.dumps(history,ensure_ascii=False),id))
        audit('feedback_review',u['role'],str(id));return dict(ok=True)
    @router.delete('/api/admin/feedback/{id}')
    def purge(id:int,req:Request):
        u=admin(req)
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT chat_id FROM quality_reports WHERE id=?',(id,)).fetchone()
            if not row:raise HTTPException(404,'Không có phản hồi.')
            c.execute('DELETE FROM feedback WHERE chat_id=?',(row[0],))
            c.execute('DELETE FROM quality_reports WHERE id=?',(id,))
        audit('feedback_purge',u['role'],str(id));return dict(ok=True)
    app.include_router(router)
