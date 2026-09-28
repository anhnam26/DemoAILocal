import asyncio,hashlib,json,sqlite3,time,secrets
from pathlib import Path
from fastapi import APIRouter,HTTPException,Request,Query
from pydantic import BaseModel,Field
import config,model_provider,sync_knowledge,rag,token_usage
START=time.monotonic()

class Reconcile(BaseModel):
    prompt_tokens:int=Field(ge=0,le=1000000000)
    completion_tokens:int=Field(ge=0,le=1000000000)
    note:str=Field(min_length=10,max_length=1000)

def install(app,connect,user,audit,generation_lock,docs_for):
    router=APIRouter()
    def admin(req):
        u=user(req)
        if u['role']!='admin':raise HTTPException(403,'Cần quyền quản trị.')
        return u
    @router.get('/api/admin/system')
    def system(req:Request):
        admin(req)
        with connect() as c:counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('users','docs','chats','conversations','token_usage')}
        return dict(provider=model_provider.public_settings(),database=counts,generation=generation_lock.status(),uptime=int(time.monotonic()-START),month=token_usage.month(),timezone='UTC')

    @router.get('/api/admin/usage')
    def usage(req:Request,month:str|None=Query(None,pattern=r'^\d{4}-(0[1-9]|1[0-2])$'),user_id:str|None=None,offset:int=Query(0,ge=0)):
        admin(req);period=month or token_usage.month()
        with connect() as c:
            users=c.execute('SELECT id,username,name FROM users WHERE (? IS NULL OR id=?) ORDER BY username',(user_id,user_id)).fetchall()
            records=[dict(r) for r in c.execute('''SELECT t.*,u.username FROM token_usage t JOIN users u ON t.user_id=u.id
                  WHERE t.month=? AND (? IS NULL OR t.user_id=?) ORDER BY t.created DESC,t.id LIMIT 51 OFFSET ?''',(period,user_id,user_id,offset))]
        return dict(month=period,timezone='UTC',users=[dict(**dict(u),**token_usage.summary(connect,u['id'],period)) for u in users],records=records[:50],has_more=len(records)>50,next_offset=offset+50)

    @router.post('/api/admin/usage/{id}/reconcile')
    def reconcile(id:str,data:Reconcile,req:Request):
        u=admin(req);token_usage.reconcile(connect,id,data.prompt_tokens,data.completion_tokens,data.note)
        audit('usage_reconcile',u['role'],json.dumps(dict(id=id,**data.model_dump()),ensure_ascii=False));return {'ok':True}

    @router.post('/api/admin/knowledge/sync')
    async def sync(req:Request):
        u=admin(req);await generation_lock.acquire()
        try:
            docs=await asyncio.to_thread(sync_knowledge.load)
            await asyncio.to_thread(sync_knowledge.synchronize,connect,docs)
            rag.index.cache_clear();audit('knowledge_sync',u['role'],str(len(docs)))
            return {'documents':len(docs)}
        except (ValueError,OSError):raise HTTPException(400,'Nguồn knowledge/documents.json chưa hợp lệ; dữ liệu hiện tại được giữ.')
        finally:generation_lock.release()

    @router.post('/api/admin/system/backup')
    def backup(req:Request):
        u=admin(req);root=config.data_dir()/'backups';root.mkdir(parents=True,exist_ok=True)
        name=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.sqlite3'
        with connect() as src,sqlite3.connect(root/name) as dest:src.backup(dest)
        audit('backup',u['role'],name);return dict(ok=True,path='data/backups/'+name)

    @router.get('/api/admin/conversations')
    def conversations(req:Request):
        u=admin(req);allowed={d['id']:hashlib.sha256(d['body'].encode()).hexdigest() for d in docs_for(u)}
        with connect() as c:rows=c.execute('SELECT ch.question,ch.result,ch.ts,u.username FROM chats ch LEFT JOIN users u ON ch.user_id=u.id ORDER BY ch.id DESC LIMIT 100').fetchall()
        result=[]
        for r in rows:
            a=json.loads(r['result']);valid=all(s['id'] in allowed and s.get('source_digest',allowed.get(s['id']))==allowed.get(s['id']) for s in a.get('sources',[]))
            result.append(dict(question=r['question'],answer=a['answer'] if valid else 'Nguồn đã thay đổi/thu hồi.',ts=r['ts'],username=r['username'],mode=a.get('mode')))
        return result
    app.include_router(router)
