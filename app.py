from pathlib import Path
from contextlib import asynccontextmanager
from datetime import date,datetime,timezone
import asyncio, hashlib, json, re, secrets, sqlite3, time, unicodedata, subprocess
import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from fastapi import FastAPI,HTTPException,Request,Response,UploadFile,File,Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from pypdf import PdfReader
import io
import accounts
import system_runtime
import runtime_limits
import conversations
from generation import GenerationGate
import admin_system
from functools import lru_cache
from collections import Counter
import rag, model_provider, sync_knowledge


ROOT=Path(__file__).parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
DB=DATA/'demo.sqlite3'
LOCK=GenerationGate()
ACTIVE_CONVERSATIONS=set()
def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def now(): return datetime.now(timezone.utc).isoformat()
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD',s.lower().replace('đ','d')) if unicodedata.category(c)!='Mn')
def audit(action,role,detail):
    with connect() as c: c.execute('INSERT INTO audit(ts,action,role,detail) VALUES(?,?,?,?)',(now(),action,role,detail))
def init():
    if not (DATA/'knowledge_documents.json').exists():sync_knowledge.build()
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,profile TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,ts TEXT,action TEXT,role TEXT,detail TEXT);
        CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY,session TEXT,question TEXT,result TEXT,ts TEXT);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,chat_id INTEGER,session TEXT,rating INTEGER,ts TEXT);''')
        if 'context_after' not in {r[1] for r in c.execute('PRAGMA table_info(sessions)')}:
            c.execute('ALTER TABLE sessions ADD COLUMN context_after INTEGER DEFAULT 0')
        if 'user_id' not in {r[1] for r in c.execute('PRAGMA table_info(chats)')}:
            c.execute('ALTER TABLE chats ADD COLUMN user_id TEXT')
    accounts.init(connect)
    conversations.init(connect)
    # A one-time privacy migration clears old knowledge and conversation payloads.
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS migrations(name TEXT PRIMARY KEY)')
        if not c.execute("SELECT 1 FROM migrations WHERE name='theory_only_v1'").fetchone():
            c.execute('PRAGMA secure_delete=ON')
            for table in ('docs','chats','feedback','audit','conversations','sessions'):
                c.execute('DELETE FROM '+table)
            c.execute("UPDATE users SET role='member',customers='[]' WHERE role IN ('sale','technical')")
            c.execute("UPDATE users SET customers='[]'")
            c.execute("INSERT INTO migrations VALUES('theory_only_v1')")
    with connect() as c:c.execute('VACUUM')
    sync_knowledge.synchronize(connect,json.loads((DATA/'knowledge_documents.json').read_text(encoding='utf8')))
init()
app=FastAPI(title='CyberAnt Knowledge',docs_url=None,redoc_url=None)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

@app.middleware('http')
async def local_guard(request,call_next):
    host=request.headers.get('host','').split(':')[0]
    if host not in ('127.0.0.1','localhost','testserver'): return Response('Local access only',403)
    origin=request.headers.get('origin')
    if origin and origin not in ('http://127.0.0.1:8088','http://localhost:8088','http://testserver'):
        return Response('Origin denied',403)
    res=await call_next(request)
    res.headers['X-Content-Type-Options']='nosniff'
    res.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    res.headers['Cache-Control']='no-store'
    return res

def user(req):
    return accounts.current(req,connect)

def docs_for(u=None,pending=False,shared=False):
    with connect() as c:rows=c.execute('SELECT payload FROM docs ORDER BY id').fetchall()
    result=[]
    for row in rows:
        d=json.loads(row['payload'])
        if d.get('customer') or d.get('is_example'):continue
        if not pending and (d['status']!='approved' or not d['valid_from']<=date.today().isoformat()<=d['valid_to']):continue
        result.append(d)
    return result

def retrieve(q,u):
    return rag.retrieve(q,docs_for(u),model_provider.settings()['top_k'])[0]

def source(d):return {**{k:d[k] for k in ('id','title','category','version','owner','valid_to')},'references':d.get('references',[]),'knowledge_type':d.get('knowledge_type','theory'),'group':d.get('group','F'),'review_status':d.get('review_status','reference'),'provenance':d.get('provenance',{})}
class Chat(BaseModel):
    question:str=Field(min_length=2,max_length=1500)
    conversation_id:str|None=Field(default=None,max_length=64)
class Feedback(BaseModel): chat_id:int; rating:int=Field(ge=-1,le=1)
@app.get('/')
def index():return FileResponse(ROOT/'static'/'index.html')
@app.get('/api/me')
def me(req:Request):u=user(req);return {k:v for k,v in u.items() if k not in ('token','context_after','sid')}
@app.get('/api/health')
async def health():
    settings=model_provider.public_settings();ready=settings['configured']
    observed=None
    if settings['mode']=='local':
        observed=system_runtime.observed_config()
        try:
            cfg=model_provider.settings()
            async with httpx.AsyncClient(timeout=2,trust_env=False) as c:
                r=await c.get(cfg['url']+'/models',headers=model_provider.headers(cfg))
                ready=r.status_code==200 and any(m.get('id')==cfg['model'] for m in r.json().get('data',[]))
        except (httpx.HTTPError,ValueError):ready=False
    return dict(**settings,ready=ready,readiness='configured' if settings['mode']=='openrouter' else 'probed',
                backend='OpenRouter API' if settings['mode']=='openrouter' else 'llama.cpp · local',
                context=observed.get('context') if observed else settings['input_budget'],
                generation=LOCK.status(),retrieval='Phân nhóm cục bộ + TF-IDF từ/ký tự + chọn đoạn đa dạng',demo=False)

@app.get('/api/documents')
def documents(req:Request):return [source(d) for d in docs_for(user(req),shared=True)]
@app.get('/api/documents/{id}')
def document(id:str,req:Request):
    for d in docs_for(user(req),shared=True):
        if d['id']==id:return d
    raise HTTPException(404,'Không tìm thấy tài liệu trong phạm vi được phép.')
@app.post('/api/chat/reset')
def reset_chat(req:Request):
    return dict(ok=True,conversation_id=conversations.create(connect,user(req),now))

@app.post('/api/chat')
async def chat(data:Chat,req:Request):
    u=user(req);id=conversations.resolve(connect,u,data.conversation_id,now)
    if id in ACTIVE_CONVERSATIONS:raise HTTPException(409,'Cuộc trò chuyện này đang trả lời. Hãy chờ hoặc mở cuộc trò chuyện mới.')
    ACTIVE_CONVERSATIONS.add(id)
    try:return await answer_chat(data,req,u,id)
    finally:ACTIVE_CONVERSATIONS.discard(id)

async def answer_chat(data,req,u,conversation_id):
    start=time.monotonic();q=data.question.strip();allowed=docs_for(u);effective=q
    with connect() as c:
        previous=c.execute('SELECT question,result FROM chats WHERE conversation_id=? AND user_id=? ORDER BY id DESC LIMIT 1',(conversation_id,u['id'])).fetchone()
    if previous:
        prior=json.loads(previous['result']);ids={d['id'] for d in allowed}
        if all(d['id'] in ids for d in prior.get('sources',[])):
            effective=rag.followup(q,prior.get('effective_query',previous['question']))
    cfg=model_provider.settings();usage={};estimated=0;calls=0;found=[];used=[];review=True
    # No record lookup or invented customer identity; this costs zero API calls.
    if re.search(r'\b(crm-|contract-|quote-|ticket-|cong no|ho so khach|ten khach hang|khach hang thuc|dien thoai khach)',rag.norm(effective)):
        answer='Kho này chỉ giữ tài liệu lý thuyết và biểu mẫu trống; không lưu hồ sơ, liên hệ, hợp đồng hay công nợ khách hàng.'
        routing={'groups':[],'routing':'local','candidates':0};mode='Không có dữ liệu khách hàng'
    else:
        found,routing=await asyncio.to_thread(rag.retrieve,effective,allowed,cfg['top_k'])
        mode=('OpenRouter' if cfg['mode']=='openrouter' else 'Local')+' + RAG'
        if not found:
            answer='Kho tri thức chưa có đủ căn cứ. Hãy nêu rõ dịch vụ, thiết bị hoặc nội dung cần tìm.';mode='Thiếu căn cứ'
        else:
            budget=cfg['input_budget'];output=cfg['output_budget'];parallel=cfg['parallel']
            if cfg['mode']=='local':
                runtime=system_runtime.config();observed=system_runtime.observed_config() or {}
                context=observed.get('context') or runtime['context']
                output=min(output,runtime_limits.output_limit(context,runtime['max_tokens']))
                budget=min(budget,context-output-128);parallel=observed.get('parallel') or 1
            try:messages,found,estimated=rag.pack(effective,found,budget)
            except ValueError as e:raise HTTPException(400,str(e))
            if not found:
                answer='Ngân sách đầu vào chưa đủ để chứa đoạn nguồn. Hãy rút gọn câu hỏi hoặc tăng RAG_INPUT_TOKENS.';mode='Thiếu ngân sách'
            else:
                await LOCK.enter(parallel)
                try:
                    calls=1
                    answer,usage,finish=await model_provider.complete(messages,cfg,output)
                    answer=re.sub(r'<think>.*?</think>','',answer,flags=re.S).strip()
                    ids={d['id'] for d in found};cited=set(re.findall(r'\[([A-Za-z0-9_-]+)\]',answer))
                    used=[d['id'] for d in found if d['id'] in cited];used=list(dict.fromkeys(used))
                    review=finish=='length' or any(d.get('review_status')=='draft_engineer_review' for d in found)
                    review=review or any(t in rag.norm(q) for t in ('cau hinh','sla','gia','rollback','lenh'))
                    if not cited or not cited.issubset(ids):
                        answer='Bản tổng hợp chưa đạt kiểm tra mã nguồn. Các trích đoạn để đối chiếu:\n\n'+'\n\n'.join(d['body']+' ['+d['id']+']' for d in found[:2])
                        used=[d['id'] for d in found[:2]];review=True;mode='Trích đoạn tài liệu'
                except httpx.HTTPStatusError as e:
                    status=e.response.status_code
                    audit('model_error',u['role'],str(status))
                    detail={401:'API key không hợp lệ.',402:'Tài khoản OpenRouter không đủ số dư.',429:'Nhà cung cấp đang giới hạn lượt gọi.'}.get(status,'Model từ chối yêu cầu; kiểm tra model và cấu hình ngân sách.')
                    raise HTTPException(503,detail)
                except (httpx.HTTPError,ValueError,KeyError,TypeError,IndexError):
                    audit('model_error',u['role'],'provider_failure')
                    raise HTTPException(503,'Không nhận được phản hồi hợp lệ. Kiểm tra .env/kết nối hoặc model local. Hệ thống không tự gọi lại.')
                finally:LOCK.leave()
    fresh=user(req);fresh_ids={d['id'] for d in docs_for(fresh)}
    if any(id not in fresh_ids for id in used):raise HTTPException(409,'Nguồn đã thay đổi trong lúc xử lý; hãy hỏi lại.')
    source_docs={d['id']:d for d in found if d['id'] in used}
    out=dict(answer=answer,sources=[source(d) for d in source_docs.values()],needs_review=review,mode=mode,
             elapsed=round(time.monotonic()-start,2),demo=False,citations_verified=bool(used),effective_query=effective,
             usage=usage,api_calls=calls if cfg['mode']=='openrouter' else 0,
             retrieval={**routing,'selected_chunks':len(found),'estimated_input_tokens':estimated,'token_estimator':'UTF-8 byte upper estimate'})
    with connect() as c:
        cur=c.execute('INSERT INTO chats(session,question,result,ts,user_id,conversation_id) VALUES(?,?,?,?,?,?)',(u['token'],q,json.dumps(out,ensure_ascii=False),now(),u['id'],conversation_id));out['chat_id']=cur.lastrowid
        c.execute("UPDATE conversations SET title=CASE WHEN title='Cuộc trò chuyện mới' THEN ? ELSE title END,updated=? WHERE id=?",(q[:100],now(),conversation_id))
    out['conversation_id']=conversation_id
    audit('chat',u['role'],f"{mode}; sources={','.join(used)}; calls={out['api_calls']}")
    return out

@app.get('/api/history')
def history(req:Request):
    u=user(req);id=conversations.resolve(connect,u,None,now)
    return conversations.messages(connect,u,id,docs_for)['messages']
@app.post('/api/feedback')
def feedback(data:Feedback,req:Request):
    u=user(req)
    with connect() as c:
        if not c.execute('SELECT id FROM chats WHERE id=? AND user_id=?',(data.chat_id,u['id'])).fetchone():raise HTTPException(404,'Không tìm thấy lượt hỏi')
        c.execute('INSERT INTO feedback(chat_id,session,rating,ts) VALUES(?,?,?,?)',(data.chat_id,u['token'],data.rating,now()))
    return {'ok':True}
@app.get('/api/admin')
def admin(req:Request):
    u=user(req)
    if u['role']!='admin':raise HTTPException(403,'Cần vai trò quản trị')
    with connect() as c:logs=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 30')]
    return {'documents':docs_for(u,True),'audit':logs}
@app.post('/api/admin/upload')
async def upload(req:Request,file:UploadFile=File(...),audience:str=Form('all')):
    u=user(req)
    if u['role']!='admin':raise HTTPException(403,'Cần vai trò quản trị')
    if audience != 'all':raise HTTPException(400,'Phạm vi không hợp lệ')
    raw=await file.read(2_000_001)
    if len(raw)>2_000_000:raise HTTPException(400,'Giới hạn 2MB cho demo')
    name=Path(file.filename or 'document').name
    if Path(name).suffix.lower() not in ('.txt','.md','.pdf'):raise HTTPException(400,'Demo nhận TXT, Markdown hoặc PDF có text')
    try:
        body='\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages[:30]) if name.lower().endswith('.pdf') else raw.decode('utf8')
    except Exception:raise HTTPException(400,'Không trích xuất được; cần file UTF-8 hoặc PDF có text')
    if len(body.strip())<30:raise HTTPException(400,'Không đủ nội dung. PDF scan cần OCR ngoài demo.')
    if len(body)>12000:raise HTTPException(400,'Chia tài liệu thành các mục dưới 12.000 ký tự cho demo')
    d=dict(id='UP-'+secrets.token_hex(4).upper(),title=name,category='Tải lên',body=body,roles=['member','admin'],customer=None,version='upload-1',status='pending',valid_from=date.today().isoformat(),valid_to='2027-12-31',owner='Quản trị',group='F',knowledge_type='theory',review_status='manual_review')
    with connect() as c:c.execute('INSERT INTO docs VALUES(?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
    audit('upload',u['role'],d['id']+' đang chờ duyệt');return {'id':d['id'],'status':'pending'}
@app.post('/api/admin/documents/{id}/{action}')
def approve(id:str,action:str,req:Request):
    u=user(req)
    if u['role']!='admin':raise HTTPException(403,'Cần vai trò quản trị')
    if action not in ('approve','retire'):raise HTTPException(400,'Thao tác không hợp lệ')
    with connect() as c:
        row=c.execute('SELECT payload FROM docs WHERE id=?',(id,)).fetchone()
        if not row:raise HTTPException(404,'Không tìm thấy')
        d=json.loads(row['payload']);d['status']='approved' if action=='approve' else 'retired'
        c.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps(d,ensure_ascii=False),id))
    audit(action,u['role'],id);return {'ok':True}

accounts.install(app,connect,user,audit)
conversations.install(app,connect,user,docs_for,now,ACTIVE_CONVERSATIONS,audit)
admin_system.install(app,connect,user,audit,LOCK,docs_for)

