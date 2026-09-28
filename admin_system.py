import asyncio,json,time,sqlite3,shutil,secrets
from pathlib import Path
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
import system_runtime as runtime
import runtime_limits as limits
import model_provider, sync_knowledge, rag
class Settings(BaseModel):
    parallel:int=Field(default=2,ge=1,le=limits.MAX_PARALLEL)
    context:int=Field(ge=limits.MIN_CONTEXT,le=limits.MAX_CONTEXT)
    gpu_layers:int=Field(ge=0,le=99)
    cache_ram:int=Field(ge=0,le=512)
    temperature:float=Field(ge=0,le=1)
    max_tokens:int=Field(ge=256,le=limits.MAX_OUTPUT)
class Action(BaseModel):action:str
class ProviderMode(BaseModel):mode:str
TASKS=set()

def install(app,connect,user,audit,generation_lock,docs_for):
    router=APIRouter()
    def admin(req):
        u=user(req)
        if u['role']!='admin':raise HTTPException(403,'Chỉ quản trị được đọc và thay đổi thông số hệ thống.')
        return u
    @router.get('/api/admin/system')
    def system(req:Request):
        admin(req);data=runtime.metrics()
        configured=data['configured'];observed=data['observed']
        data={**data,'budgets':{'saved':limits.budget(configured['context'],configured['parallel'],configured['max_tokens']),'running':limits.budget(observed['context'],observed['parallel'],configured['max_tokens']) if observed and observed.get('context') and observed.get('parallel') else None},'limits':dict(max_parallel=limits.MAX_PARALLEL,max_context=limits.MAX_CONTEXT,max_total_context=limits.MAX_TOTAL_CONTEXT,max_output=limits.MAX_OUTPUT)}
        with connect() as c:
            counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('users','docs','chats','audit','feedback','conversations')}
            online=c.execute('SELECT COUNT(DISTINCT user_id) FROM sessions WHERE last_seen>? AND created>?',(time.time()-75,time.time()-43200)).fetchone()[0]
        provider=model_provider.public_settings()
        return {**data,'provider':provider,'database':counts,'online':online,'generation_busy':generation_lock.locked(),'generation':generation_lock.status(),'retrieval':'Phân nhóm + TF-IDF + ngân sách đầu vào','connections_fixed':dict(web='http://127.0.0.1:8088',model='OpenRouter API' if provider['mode']=='openrouter' else 'http://127.0.0.1:1234',cloud_fallback=False)}
    @router.put('/api/admin/system/provider')
    def provider(data:ProviderMode,req:Request):
        u=admin(req)
        if data.mode not in ('local','openrouter'):raise HTTPException(400,'Chọn local hoặc openrouter.')
        if generation_lock.locked():raise HTTPException(409,'Chờ các lượt trả lời hoàn tất trước khi đổi mode.')
        import os,re
        if 'LLM_MODE' in os.environ:raise HTTPException(409,'LLM_MODE đang do môi trường tiến trình quản lý; đổi biến đó rồi khởi động lại ứng dụng.')
        path=runtime.ROOT/'.env';text=path.read_text(encoding='utf-8-sig') if path.exists() else ''
        text=re.sub(r'^\s*LLM_MODE\s*=.*(?:\n|$)','',text,flags=re.M).rstrip()+'\nLLM_MODE='+data.mode+'\n'
        temp=path.with_suffix('.tmp');temp.write_text(text,encoding='utf8');temp.replace(path)
        audit('provider',u['role'],data.mode)
        return model_provider.public_settings()
    @router.post('/api/admin/knowledge/sync')
    async def sync(req:Request):
        u=admin(req)
        if generation_lock.locked():raise HTTPException(409,'Chờ các lượt trả lời hoàn tất trước khi đồng bộ.')
        await generation_lock.acquire()
        try:
            report=await asyncio.to_thread(sync_knowledge.build)
            docs=json.loads((runtime.ROOT/'data'/'knowledge_documents.json').read_text(encoding='utf8'))
            sync_knowledge.synchronize(connect,docs);rag.index.cache_clear()
            audit('knowledge_sync',u['role'],str(report['documents']))
            return report
        finally:generation_lock.release()
    @router.put('/api/admin/system/config')
    def configure(data:Settings,req:Request):
        u=admin(req)
        if data.context%256:raise HTTPException(400,'Context phải là bội số của 256.')
        if data.context*data.parallel>limits.MAX_TOTAL_CONTEXT:raise HTTPException(400,'Tổng context của tất cả lượt không được vượt '+str(limits.MAX_TOTAL_CONTEXT)+' token trong bản demo.')
        if generation_lock.locked():raise HTTPException(409,'Có lượt sinh hoặc thao tác model đang chạy. Chờ hoàn tất trước đổi cấu hình.')
        runtime.save_config(data.model_dump());runtime.METRICS_TIME=0;audit('runtime_config',u['role'],json.dumps(data.model_dump()))
        return dict(ok=True,configured=data.model_dump(),message='Đã lưu. Temperature/token đầu ra áp dụng lượt hỏi mới. Context/số lượt đồng thời/lớp GPU/cache áp dụng sau Khởi động lại model.')
    @router.post('/api/admin/system/model')
    async def control(data:Action,req:Request):
        u=admin(req)
        if model_provider.settings()['mode']!='local':raise HTTPException(400,'Điều khiển GPU chỉ dùng trong mode local.')
        if data.action not in ('start','stop','restart'):raise HTTPException(400,'Thao tác không hợp lệ.')
        if generation_lock.locked():raise HTTPException(409,'Model đang trả lời hoặc đổi trạng thái; chưa thể thực hiện.')
        await generation_lock.acquire()
        runtime.ACTION=dict(state='running',action=data.action,started=time.time())
        async def execute():
            try:
                await asyncio.to_thread(runtime.control,data.action)
                audit('model_'+data.action,u['role'],runtime.ACTION['state'])
            finally:generation_lock.release()
        task=asyncio.create_task(execute());TASKS.add(task);task.add_done_callback(TASKS.discard)
        return dict(accepted=True,message='Đang '+data.action+' model; trang hệ thống sẽ cập nhật trạng thái.')
    @router.get('/api/admin/system/logs')
    def logs(req:Request,stream:str='app',lines:int=80):
        admin(req)
        if stream not in ('app','model'):raise HTTPException(400,'Loại log không hợp lệ.')
        path=runtime.ROOT/'logs'/(stream+'.stderr.log')
        if not path.exists():return dict(text='Chưa có log.')
        with path.open('rb') as f:
            f.seek(max(0,path.stat().st_size-60000));data=f.read().decode('utf8',errors='replace')
        import re
        data=re.sub(r'Bearer\s+\S+','Bearer [REDACTED]',data,flags=re.I)
        return dict(text='\n'.join(data.splitlines()[-max(1,min(lines,200)):]))
    @router.post('/api/admin/system/backup')
    def backup(req:Request):
        u=admin(req);path=runtime.ROOT/'backups'/(time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(2));path.mkdir(parents=True)
        with connect() as src,sqlite3.connect(path/'demo.sqlite3') as dest:src.backup(dest)
        for file in (runtime.ROOT/'data').glob('*.json'):
            if file.name!='initial-accounts.json':shutil.copy2(file,path/file.name)
        audit('backup',u['role'],path.name);return dict(ok=True,path=str(path))
    @router.get('/api/admin/conversations')
    def conversations(req:Request):
        import hashlib
        u=admin(req);allowed={d['id']:hashlib.sha256(d['body'].encode()).hexdigest() for d in docs_for(u)}
        with connect() as c:rows=c.execute('SELECT ch.id,ch.question,ch.result,ch.ts,u.username FROM chats ch LEFT JOIN sessions s ON s.token=ch.session LEFT JOIN users u ON u.id=COALESCE(ch.user_id,s.user_id) ORDER BY ch.id DESC LIMIT 100').fetchall()
        result=[]
        for r in rows:
            a=json.loads(r['result']);valid=all(s['id'] in allowed and s.get('source_digest',allowed.get(s['id']))==allowed.get(s['id']) for s in a.get('sources',[]))
            result.append(dict(id=r['id'],question=r['question'],answer=a['answer'] if valid else 'Nguồn hết hiệu lực/thu hồi; nội dung cũ không hiển thị.',ts=r['ts'],username=r['username'] or 'Phiên cũ/đã thu hồi',mode=a.get('mode')))
        return result
    app.include_router(router)
