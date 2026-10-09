from pathlib import Path
from datetime import date,datetime,timezone
import asyncio, hashlib, json, re, secrets, time
import httpx
from fastapi import FastAPI,HTTPException,Request,Response,UploadFile,File,Form
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from pypdf import PdfReader
import io
from contextlib import asynccontextmanager
from typing import Literal
from cyberant import accounts,config,token_usage,runtime_lock
from cyberant import conversations,quality_feedback
APP_VERSION='2026.10.09-chat-tools-2'
PROMPT_VERSION='service-files-web-5'
from cyberant.generation import GenerationGate
from cyberant.http_limits import BodyLimitMiddleware
from cyberant import admin_system,rag,model_provider,storage,web_search,provider_errors,service_evidence,attachments,document_extractors,url_reader


ROOT=Path(__file__).resolve().parents[1]
def connect():
    return storage.connect(config.data_dir())
def now(): return datetime.now(timezone.utc).isoformat()
def audit(action,role,detail):
    with connect() as c: c.execute('INSERT INTO audit(ts,action,role,detail) VALUES(?,?,?,?)',(now(),action,role,detail))


def create_app():
    """Build an isolated application; persistent writes occur only in lifespan/requests."""
    INSTANCE_LOCK=None
    LOCK=GenerationGate()
    ACTIVE_CONVERSATIONS=set()
    @asynccontextmanager
    async def lifespan(application):
        nonlocal INSTANCE_LOCK
        config.security()
        INSTANCE_LOCK=runtime_lock.acquire(config.data_dir())
        try:
            storage.validate(config.data_dir(),integrity=True)
            token_usage.recover(connect)
            application.state.ready=True
            yield
        finally:
            application.state.ready=False
            INSTANCE_LOCK.close()
            INSTANCE_LOCK=None

    app=FastAPI(title='CyberAnt Knowledge',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
    app.add_middleware(BodyLimitMiddleware)

    @app.middleware('http')
    async def request_guard(request,call_next):
        from urllib.parse import urlsplit
        security=config.security()
        host=urlsplit('//'+request.headers.get('host','')).hostname
        if host not in security['hosts']:return Response('Host denied',400)
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/') not in security['origins']:return Response('Origin denied',403)
        if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('sec-fetch-site')=='cross-site':return Response('Cross-site denied',403)
        length=request.headers.get('content-length')
        body_limit=10_100_000 if re.fullmatch(r'/api/conversations/[a-f0-9]{24}/attachments',request.url.path) else 2_100_000
        if length and (not length.isdigit() or int(length)>body_limit):return Response('Request too large',413)
        res=await call_next(request)
        res.headers['X-Content-Type-Options']='nosniff'
        res.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        res.headers['Cache-Control']='no-store'
        res.headers['Referrer-Policy']='same-origin'
        if security['production']:res.headers['Strict-Transport-Security']='max-age=31536000'
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

    def source(d):return {**{k:d[k] for k in ('id','title','category','version','owner','valid_to')},'references':d.get('references',[]),'knowledge_type':d.get('knowledge_type','theory'),'group':d.get('group','F'),'review_status':d.get('review_status','reference'),'provenance':d.get('provenance',{}),'source_digest':d.get('source_digest') or hashlib.sha256(d['body'].encode()).hexdigest()}
    class Chat(BaseModel):
        question:str=Field(min_length=2,max_length=20000)
        conversation_id:str|None=Field(default=None,max_length=64)
        model:str|None=Field(default=None,min_length=1,max_length=200)
        audience:Literal['auto','sales','engineering']='auto'
        web_query:str|None=Field(default=None,min_length=2,max_length=300)
        urls:list[str]=Field(default_factory=list,max_length=3)
    class ModelInput(BaseModel):
        model:str=Field(min_length=1,max_length=200)
    Feedback=quality_feedback.Feedback
    @app.get('/')
    def index():return FileResponse(ROOT/'static'/'index.html')
    @app.get('/api/me')
    def me(req:Request):u=user(req);return {k:v for k,v in u.items() if k not in ('token','context_after','sid')}
    @app.get('/api/health')
    def health():
        return {'status':'ok','provider':'openrouter','app_version':APP_VERSION,'prompt_version':PROMPT_VERSION}

    @app.get('/api/ready')
    def ready():
        if not getattr(app.state,'ready',False):raise HTTPException(503,'Ứng dụng chưa sẵn sàng')
        with connect() as c:
            for table in ('users','chats','docs','audit'):c.execute('SELECT 1 FROM '+table+' LIMIT 1').fetchall()
        return {'status':'ready','layout_version':storage.VERSION}

    @app.get('/api/account/usage')
    def my_usage(req:Request):return token_usage.summary(connect,user(req)['id'])

    @app.get('/api/model')
    def my_model(req:Request):
        u=user(req)
        available=[m for m in u['allowed_models'] if m in model_provider.models()]
        return dict(model=u['model'],allowed_models=available,mode='openrouter',configured=u['model'] in available and bool(model_provider.settings()['api_key']),generation=LOCK.status(),catalog=[item for item in model_provider.catalog()['items'] if item['id'] in available])

    @app.put('/api/model')
    def select_model(data:ModelInput,req:Request):
        u=user(req)
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT active,allowed_models FROM users WHERE id=?',(u['id'],)).fetchone()
            if not row or not row['active']:raise HTTPException(403,'Tài khoản đã bị khóa.')
            model_provider.require_allowed(data.model,row['allowed_models'])
            c.execute('UPDATE users SET model=?,updated=? WHERE id=?',(data.model,time.time(),u['id']))
        return my_model(req)

    @app.get('/api/documents')
    def documents(req:Request):return [source(d) for d in docs_for(user(req),shared=True)]
    @app.get('/api/documents/{id}')
    def document(id:str,req:Request):
        for d in docs_for(user(req),shared=True):
            if d['id']==id:return d
        if id.startswith('FILE-'):
            u=user(req)
            with connect() as c:
                if attachments.available(c):row=c.execute('SELECT conversation_id FROM attachments WHERE id=? AND user_id=?',(id.rsplit('-',1)[0],u['id'])).fetchone()
                else:row=None
            if row:
                for d in attachments.documents(connect,u,row['conversation_id']):
                    if d['id']==id:return d
        raise HTTPException(404,'Không tìm thấy tài liệu trong phạm vi được phép.')
    @app.post('/api/chat/reset')
    def reset_chat(req:Request):
        return dict(ok=True,conversation_id=conversations.create(connect,user(req),now))

    @app.get('/api/conversations/{id}/attachments')
    def list_files(id:str,req:Request):return dict(items=attachments.listing(connect,user(req),id))

    @app.post('/api/conversations/{id}/attachments')
    async def upload_file(id:str,req:Request,file:UploadFile=File(...)):
        u=user(req);conversations.resolve(connect,u,id,now)
        if id in ACTIVE_CONVERSATIONS:raise HTTPException(409,'Hội thoại đang trả lời; chờ trước khi đổi file.')
        with connect() as c:attachments.require(c)
        raw=await file.read(document_extractors.MAX_BYTES+1)
        name=Path((file.filename or 'file').replace('\\','/')).name[:200]
        try:parsed=await document_extractors.extract_async(raw,name)
        except Exception:raise HTTPException(400,'Không đọc được file hoặc vượt giới hạn. Nhận UTF-8 TXT/MD/CSV, PDF text, DOCX/XLSX/PPTX; scan cần OCR, file cũ/mã hóa cần chuyển đổi.') from None
        if id in ACTIVE_CONVERSATIONS:raise HTTPException(409,'Hội thoại vừa bắt đầu trả lời; tải lại sau.')
        fresh=user(req);file_id=attachments.save(connect,fresh,id,name,raw,parsed,now)
        audit('chat_file_upload',fresh['role'],file_id)
        return dict(id=file_id,name=name,warnings=parsed['warnings'],units=len(parsed['units']))

    @app.delete('/api/conversations/{id}/attachments/{file_id}')
    def delete_file(id:str,file_id:str,req:Request):
        u=user(req)
        if id in ACTIVE_CONVERSATIONS:raise HTTPException(409,'Hội thoại đang trả lời; chờ trước khi đổi file.')
        attachments.delete(connect,u,id,file_id);audit('chat_file_delete',u['role'],file_id)
        return dict(ok=True)

    @app.post('/api/chat')
    async def chat(data:Chat,req:Request):
        u=user(req)
        data.model=model_provider.require_allowed(data.model if data.model is not None else u['model'],u['allowed_models'])
        id=conversations.resolve(connect,u,data.conversation_id,now)
        if id in ACTIVE_CONVERSATIONS:raise HTTPException(409,'Cuộc trò chuyện này đang trả lời. Hãy chờ hoặc mở cuộc trò chuyện mới.')
        ACTIVE_CONVERSATIONS.add(id)
        try:return await answer_chat(data,req,u,id)
        finally:ACTIVE_CONVERSATIONS.discard(id)

    @app.post('/api/chat/stream')
    async def stream_chat(data:Chat,req:Request):
        # Authenticate before opening a stream; keep normal /chat compatibility.
        user(req)
        events=asyncio.Queue()
        async def progress(stage):await events.put(dict(type='progress',stage=stage))
        req.state.chat_progress=progress
        async def work():
            try:await events.put(dict(type='result',data=await chat(data,req)))
            except HTTPException as e:await events.put(dict(type='error',status=e.status_code,detail=e.detail))
            except Exception:await events.put(dict(type='error',status=500,detail='Không hoàn tất yêu cầu; kiểm tra lịch sử và usage trước khi gửi lại.'))
        async def stream():
            task=asyncio.create_task(work())
            try:
                while True:
                    try:event=await asyncio.wait_for(events.get(),10)
                    except TimeoutError:
                        yield ': keepalive\n\n';continue
                    yield 'data: '+json.dumps(event,ensure_ascii=False)+'\n\n'
                    if event['type'] in ('result','error'):break
            finally:
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no','Cache-Control':'no-store'})

    async def answer_chat(data,req,u,conversation_id):
        async def progress(stage):
            callback=getattr(req.state,'chat_progress',None)
            if callback:await callback(stage)
        await progress('Đang đọc file và kiểm tra nguồn nội bộ')
        start=time.monotonic();q=data.question.strip();allowed=docs_for(u)+attachments.documents(connect,u,conversation_id);effective=q
        history=conversations.context(connect,u,conversation_id,allowed)
        if history:effective=rag.followup(q,history[-1]['effective_query'])
        try:cfg=model_provider.settings(data.model)
        except ValueError as e:raise HTTPException(400,str(e))
        usage={};estimated=0;calls=0;found=[];used=[];review=True
        provider_deadline=None
        finish=None;output=0;budget=0;reservation=None;retrieved_count=0;citation_status='not_checked'
        retrieved_sources=[];citation_errors=[];packing={};web=[];web_state='not_needed';usages=[];usage_records=[]
        artifacts=service_evidence.artifacts(effective,rag.intent(effective),allowed)
        requested_urls=list(dict.fromkeys(data.urls+re.findall(r'https://[^\s<>]+',q)))
        requested_urls=[url.rstrip('.,;)') for url in requested_urls]
        if len(requested_urls)>3:raise HTTPException(400,'Tối đa 3 URL mỗi lượt.')
        for url in requested_urls:
            try:url_reader.validate_url(url)
            except ValueError as e:raise HTTPException(400,str(e)) from None
        url_reports=[]
        async def invoke(messages,settings,limit,input_size):
            nonlocal calls,reservation
            remaining=provider_deadline-time.monotonic()
            if remaining<=0:raise HTTPException(504,'Đã hết thời gian xử lý tổng. Không tự gọi lại; kiểm tra usage trước khi gửi lại.')
            fresh=user(req)
            reservation,limit=token_usage.reserve(connect,fresh['id'],cfg['model'],input_size,limit,min_output_tokens=limit)
            usage_records.append(reservation)
            call_start=time.monotonic()
            def provider_failure(error):
                failure,detail=provider_errors.failure(error,cfg['model'],'web_lookup' if settings.get('web_lookup') else 'completion',reservation,time.monotonic()-call_start)
                audit('model_error',u['role'],detail)
                return failure
            try:
                token_usage.mark_sent(connect,reservation);calls+=1
                async with asyncio.timeout(remaining):
                    text,measured,reason=await model_provider.complete(messages,settings,limit)
                token_usage.settle(connect,reservation,measured);usages.append(measured)
                return text,measured,reason
            except model_provider.InvalidCompletion as e:
                token_usage.settle(connect,reservation,e.usage);usages.append(e.usage)
                raise provider_failure(e) from None
            except TimeoutError as e:
                raise provider_failure(e) from None
            except httpx.HTTPStatusError as e:
                status=e.response.status_code
                token_usage.settle(connect,reservation,rejected=status in (400,401,402,403,404,422,429))
                raise provider_failure(e) from None
            except (httpx.HTTPError,ValueError,KeyError,TypeError,IndexError) as e:
                raise provider_failure(e) from None
            finally:token_usage.settle(connect,reservation)
        # No record lookup or invented customer identity; this costs zero API calls.
        if not any(d.get('attachment_id') for d in allowed) and re.search(r'\b(crm-|contract-|quote-|ticket-|cong no|ho so khach|ten khach hang|khach hang thuc|dien thoai khach)',rag.norm(effective)):
            answer='Kho này chỉ giữ tài liệu lý thuyết và biểu mẫu trống; không lưu hồ sơ, liên hệ, hợp đồng hay công nợ khách hàng.'
            routing={'groups':[],'routing':'local','candidates':0};mode='Không có dữ liệu khách hàng'
        else:
            retrieval_cap=rag.retrieval_limit(effective,cfg['top_k'])
            found,routing=await asyncio.to_thread(rag.retrieve,effective,allowed,retrieval_cap)
            file_docs=[d for d in allowed if d.get('attachment_id')]
            if file_docs:
                if sum(rag.estimate_tokens(d['body']) for d in file_docs)<=cfg['input_budget']//2:
                    file_chunks=[chunk for d in file_docs for chunk in rag.chunks(d)]
                else:
                    # Service/configuration routing applies to company knowledge,
                    # not arbitrary uploads whose titles may contain no topic.
                    file_chunks,_=await asyncio.to_thread(rag.retrieve,effective,file_docs,retrieval_cap,False)
                found=file_chunks+[d for d in found if not d.get('attachment_id')]
            if artifacts:
                artifact_chunks=[chunk for d in artifacts for chunk in rag.chunks(d)]
                artifact_ids={d['id'] for d in artifacts}
                found=artifact_chunks+[d for d in found if d['id'] not in artifact_ids]
            if history and rag.is_followup(q):
                prior_ids={s['id'] for h in history[-6:] for s in h['sources']}
                present={d['id'] for d in found}
                prior_chunks=[chunk for d in allowed if d['id'] in prior_ids-present for chunk in rag.chunks(d)]
                found=found+prior_chunks[:retrieval_cap]
            retrieved_count=len(found)
            retrieved_sources=[dict(id=d['id'],chunk=d['chunk'],digest=d['source_digest']) for d in found]
            budget,output=rag.budgets(effective,cfg['input_budget'],cfg['output_budget'])
            if file_docs or requested_urls:budget,output=cfg['input_budget'],cfg['output_budget']
            try:
                web_cfg=web_search.settings();model_provider.headers(cfg)
                messages,packed,estimated=rag.pack(effective,found,budget,data.audience,packing,history=history)
            except ValueError as e:raise HTTPException(400,str(e))
            query=web_search.public_query(q,data.web_query)
            lookup=web_search.should_search(q,found,data.web_query)
            if file_docs and not data.web_query:lookup=False
            if requested_urls and not data.web_query:lookup=False
            if lookup and not web_cfg['enabled']:web_state='disabled'
            elif lookup and not query:web_state='public_query_required'
            await LOCK.enter(cfg['parallel'])
            provider_deadline=time.monotonic()+240
            try:
                if requested_urls:
                    await progress('Đang đọc URL công khai được chỉ định')
                    url_deadline=time.monotonic()+90
                    for url in requested_urls:
                        try:
                            remaining=url_deadline-time.monotonic()
                            if remaining<=0:raise TimeoutError()
                            async with asyncio.timeout(remaining):report=await url_reader.read(url)
                            web.extend({**d,'direct_url':True} for d in report['sources'])
                            url_reports.append(dict(url=report['url'],status='read',units=report['units'],warnings=report['warnings']))
                        except (ValueError,httpx.HTTPError,OSError,TimeoutError,LookupError):
                            url_reports.append(dict(url=url,status='unreadable',units=0,warnings=['Không đọc được URL: có thể bị chặn, yêu cầu đăng nhập, vượt giới hạn hoặc không an toàn.']))
                    web_state='sources_returned' if web else 'no_valid_sources'
                if lookup and query and web_cfg['enabled']:
                    await progress('Đang tìm kiếm Internet bằng truy vấn công khai')
                    lookup_messages=web_search.messages(query)
                    lookup_size=sum(rag.estimate_tokens(m['content'])+16 for m in lookup_messages)+64
                    _,web_usage,_=await invoke(lookup_messages,{**cfg,'web_lookup':True,'web_max_results':web_cfg['max_results']},web_cfg['output_tokens'],lookup_size)
                    web+=web_search.evidence(web_usage,web_cfg['max_results'])
                    web_state='sources_returned' if web else 'no_valid_sources'
                messages,found,estimated=rag.pack(effective,found,budget,data.audience,packing,history=history,web=web)
                sent_web=set(packing['web_sent'])
                for report in url_reports:
                    report['sent_units']=sum(d['url']==report['url'] and d['id'] in sent_web for d in web)
                web=[d for d in web if d['id'] in packing['web_sent']]
                if web_state=='sources_returned' and not web:web_state='budget_omitted'
                await progress('Đang phân tích nguồn và tổng hợp câu trả lời')
                answer,_,finish=await invoke(messages,cfg,output,estimated)
                need_web='[NEED_WEB]' in answer or answer.strip()=='Kho tri thức chưa có đủ căn cứ để trả lời câu hỏi này.'
                if need_web and web_state=='not_needed' and not file_docs and not requested_urls:
                    if not web_cfg['enabled']:web_state='disabled'
                    elif not query:web_state='public_query_required'
                    else:
                        lookup_messages=web_search.messages(query)
                        lookup_size=sum(rag.estimate_tokens(m['content'])+16 for m in lookup_messages)+64
                        _,web_usage,_=await invoke(lookup_messages,{**cfg,'web_lookup':True,'web_max_results':web_cfg['max_results']},web_cfg['output_tokens'],lookup_size)
                        web=web_search.evidence(web_usage,web_cfg['max_results'])
                        web_state='sources_returned' if web else 'no_valid_sources'
                        if web:
                            messages,found,estimated=rag.pack(effective,found,budget,data.audience,packing,history=history,web=web)
                            web=[d for d in web if d['id'] in packing['web_sent']]
                            if not web:web_state='budget_omitted'
                            if web:answer,_,finish=await invoke(messages,cfg,output,estimated)
                answer=answer.replace('[NEED_WEB]','').strip()
                usage=web_search.aggregate(usages)
                answer=re.sub(r'<think\b[^>]*>.*?(?:</think>|$)','',answer,flags=re.S|re.I).strip()
                # Normalize typography, not IDs; unknown IDs still fail closed.
                answer=rag.normalize_citations(answer)
                ids={d['id'] for d in found+web};cited=set(re.findall(r'\[([A-Za-z0-9_-]+)\]',answer))
                used=list(dict.fromkeys(d['id'] for d in found if d['id'] in cited))
                web=[d for d in web if d['id'] in cited]
                # Never allow a generated hyperlink to masquerade as a returned web source.
                urls=set(re.findall(r'https?://[^\s<>\]\)]+',answer))
                allowed_urls={d['url'] for d in web}
                allowed_urls.update(url for d in found if d['id'] in used
                                    for url in re.findall(r'https?://[^\s<>\]\)]+',d['body']) if web_search.safe_url(url))
                unknown_urls=urls-allowed_urls
                mode='OpenRouter + RAG' if used else 'Kiến thức chung / ngữ cảnh'
                if web:mode='OpenRouter + Internet'+(' + RAG' if used else '')
                review=not used or bool(web) or finish=='length' or any(d.get('review_status')=='draft_engineer_review' for d in found)
                review=review or any(t in rag.norm(q) for t in ('cau hinh','sla','gia','rollback','lenh'))
                if cited-ids or unknown_urls:
                    citation_errors=['unknown_source_ids'] if cited-ids else ['unknown_urls']
                    answer='Chưa xác thực được nguồn trích dẫn. Hệ thống không hiển thị nội dung có nguồn không hợp lệ và không tự gọi lại. Hãy bổ sung tài liệu hoặc nêu truy vấn công khai rõ hơn.'
                    used=[];web=[];review=True;mode='Chưa xác thực trích dẫn';citation_status='invalid'
                elif cited:citation_status='ids_valid_not_entailment_checked'
                else:
                    citation_status='general_knowledge_unverified';review=True
                    if web_search.requires_evidence(q):
                        answer='Chưa có trích dẫn hợp lệ để xác minh thông tin cập nhật trong câu hỏi này. Hãy cung cấp nguồn chính thức hoặc truy vấn công khai cụ thể để tra cứu.'
                        mode='Thiếu nguồn cập nhật';citation_status='abstained'
                    else:answer+='\n\nLưu ý: phản hồi dựa trên kiến thức chung hoặc ngữ cảnh hội thoại, chưa được đối chiếu nguồn trích dẫn.'
                if web_state in ('public_query_required','disabled','no_valid_sources','budget_omitted'):
                    answer+='\n\nTra cứu Internet: '+{'public_query_required':'chưa có truy vấn công khai an toàn; bạn có thể nhập truy vấn riêng trong mục tra cứu web.',
                        'disabled':'đang bị tắt trong cấu hình.','no_valid_sources':'không nhận được đoạn nguồn và URL hợp lệ; không coi phản hồi là đã được web xác minh.',
                        'budget_omitted':'đã tìm được nguồn nhưng ngân sách đầu vào không đủ chứa đoạn nguồn; không coi phản hồi là đã được web xác minh.'}[web_state]
                if finish=='length' and citation_status!='invalid':
                    answer+='\n\n**Câu trả lời bị cắt do giới hạn output.** Gửi “Tiếp tục hướng dẫn ở trên” để yêu cầu phần tiếp theo trong cuộc trò chuyện này; lượt tiếp theo dùng quota riêng. Hệ thống không tự gọi lại.'
                if history and rag.is_followup(q) and history[-1]['chat_id'] not in packing.get('history_sent',[]):
                    answer+='\n\nNgữ cảnh trả lời trước không vừa ngân sách đầu vào; hãy nêu mục cần tiếp tục hoặc trích đoạn liên quan. Không thể coi lượt này là phần nối tiếp đầy đủ.'
            finally:LOCK.leave()
        fresh=user(req);fresh_docs={d['id']:d for d in docs_for(fresh)+attachments.documents(connect,fresh,conversation_id)}
        await progress('Đang kiểm tra trích dẫn và lưu kết quả')
        sent_history=set(packing.get('history_sent',[]))
        if any(s['id'] not in fresh_docs or s.get('source_digest')!=source(fresh_docs[s['id']])['source_digest']
               for h in history if h['chat_id'] in sent_history for s in h['sources']):
            raise HTTPException(409,'Nguồn trong ngữ cảnh đã thay đổi trong lúc xử lý; hãy hỏi lại.')
        if any(d['id'] not in fresh_docs or source(d)['source_digest']!=source(fresh_docs[d['id']])['source_digest'] for d in found if d['id'] in used):
            raise HTTPException(409,'Nguồn đã thay đổi trong lúc xử lý; hãy hỏi lại.')
        if any(d['id'] not in fresh_docs or source(d)['source_digest']!=source(fresh_docs[d['id']])['source_digest'] for d in artifacts):
            raise HTTPException(409,'Danh mục nguồn đã thay đổi; hãy hỏi lại.')
        sent_file_docs=[d for d in found if d.get('attachment_id')]
        if any(d['id'] not in fresh_docs or source(d)['source_digest']!=source(fresh_docs[d['id']])['source_digest'] for d in sent_file_docs):
            raise HTTPException(409,'File đã thay đổi trong lúc xử lý; hãy hỏi lại.')
        source_docs={d['id']:d for d in found if d['id'] in used}
        source_docs.update({d['id']:d for d in artifacts})
        dependencies={s['id']:dict(id=s['id'],source_digest=s['source_digest']) for h in history if h['chat_id'] in sent_history for s in h['sources']}
        # A model can use an upload without emitting a citation. Retention and
        # future context must still honor file deletion/revocation in that case.
        dependencies.update({d['id']:dict(id=d['id'],source_digest=d['source_digest']) for d in sent_file_docs})
        sent_files={d['id'] for d in found if d.get('attachment_id')};file_units=[d for d in allowed if d.get('attachment_id')]
        if file_units and len(sent_files)<len(file_units):answer+=f'\n\n**Phạm vi file:** gửi model {len(sent_files)}/{len(file_units)} phần trích xuất; chưa thể coi là đọc toàn bộ file trong lượt này.'
        file_list=attachments.listing(connect,fresh,conversation_id)
        sent_artifact_ids={d['id'] for d in found}&{d['id'] for d in artifacts}
        if artifacts and len(sent_artifact_ids)<len(artifacts):
            answer+=f'\n\n**Phạm vi SOW/BOM:** gửi model {len(sent_artifact_ids)}/{len(artifacts)} bản ghi. Phụ lục nguồn hiển thị đủ bản ghi, nhưng phần AI tổng hợp chưa thể coi là đầy đủ hoặc đã xác minh nội dung.'
        for f in file_list:
            if f['warnings']:answer+='\n\n**Lưu ý trích xuất '+f['name']+':** '+' '.join(f['warnings'])
        for report in url_reports:
            answer+='\n\n**Đọc URL:** '+report['status']+f" · {report.get('sent_units',0)}/{report['units']} phần gửi model. "+' '.join(report['warnings'])
        out=dict(answer=answer,url_reads=url_reports,file_coverage=dict(available_units=len(file_units),sent_units=len(sent_files)),evidence_items=[dict(id=d['id'],title=d['title'],body=d['body'],service_id=d['service_id'],version=d['version'],review_status=d.get('review_status'),source_location=d['source_location']) for d in artifacts],
                 artifact_coverage=dict(available=len(artifacts),displayed=len(artifacts),available_ids=[dict(id=d['id'],version=d['version'],digest=source(d)['source_digest']) for d in artifacts],sent_ids=list(dict.fromkeys(d['id'] for d in found if d['id'] in {a['id'] for a in artifacts})),sent_to_model=sum(d['id'] in {p['id'] for p in found} for d in artifacts),verification='record_completeness_not_factual_verification'),
                 sources=[source(d) for d in source_docs.values()],context_sources=list(dependencies.values()),web_sources=[{k:d[k] for k in ('id','title','url','retrieved_at')} for d in web],web_status=web_state,needs_review=review,mode=mode,
                 elapsed=round(time.monotonic()-start,2),citations_verified=bool(used or web),effective_query=effective,
                 usage=usage,model=cfg['model'],api_calls=calls,finish_reason=finish,output_token_limit=output,
                 citation_status=citation_status,grounding_verified=False,
                  truncated=finish=='length',
                 diagnostics=dict(app_version=APP_VERSION,prompt_version=PROMPT_VERSION,
                     prompt_hash=hashlib.sha256(rag.system_prompt(effective,data.audience).encode()).hexdigest(),effective_query=effective,
                     retrieved_sources=retrieved_sources,sent_sources=[dict(id=d['id'],chunk=d['chunk'],digest=d['source_digest']) for d in found],
                      input_budget=budget,estimated_input=estimated,output_budget=output,usage_record_id=reservation,usage_record_ids=usage_records,
                      usage=usage,finish_reason=finish,citation_errors=citation_errors,packing=packing,
                      requested_audience=data.audience,
                       model_limits=cfg.get('model_limits'),model_limits_configured=cfg.get('model_limits_configured',False),
                     scope=rag.scope(effective),device_details_required=rag.intent(effective)=='procedure' and rag.scope(effective)=='generic'),
                 retrieval={**routing,'intent':rag.intent(effective),'retrieved_chunks':retrieved_count,'selected_chunks':len(found),
                             'packed_coverage':packing.get('coverage'),'omissions':packing.get('omitted',[]),
                             'omitted_chunks':retrieved_count-len(found),'estimated_input_tokens':estimated,
                             'estimated_input_bytes':estimated,'token_estimator':'UTF-8 byte proxy; not a tokenizer'})
        with connect() as c:
            cur=c.execute('INSERT INTO chats(session,question,result,ts,user_id,conversation_id) VALUES(?,?,?,?,?,?)',(u['token'],q,json.dumps(out,ensure_ascii=False),now(),u['id'],conversation_id));out['chat_id']=cur.lastrowid
            c.execute("UPDATE conversations SET title=CASE WHEN title='Cuộc trò chuyện mới' THEN ? ELSE title END,updated=? WHERE id=?",(q[:100],now(),conversation_id))
        out['conversation_id']=conversation_id
        out['account_usage']=token_usage.summary(connect,u['id'])
        audit('chat',u['role'],f"{mode}; sources={','.join(used)}; calls={out['api_calls']}")
        return out

    @app.get('/api/history')
    def history(req:Request):
        u=user(req);id=conversations.resolve(connect,u,None,now)
        return conversations.messages(connect,u,id,docs_for)['messages']
    @app.post('/api/feedback')
    def feedback(data:Feedback,req:Request):
        return quality_feedback.submit(connect,user(req),data,now,docs_for)
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
        if len(raw)>2_000_000:raise HTTPException(400,'Giới hạn tải lên 2MB')
        name=Path(file.filename or 'document').name
        if Path(name).suffix.lower() not in ('.txt','.md','.pdf'):raise HTTPException(400,'Chỉ nhận TXT, Markdown hoặc PDF có text')
        def extract():
            return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages[:30]) if name.lower().endswith('.pdf') else raw.decode('utf8')
        try:
            body=await asyncio.to_thread(extract)
        except Exception:raise HTTPException(400,'Không trích xuất được; cần file UTF-8 hoặc PDF có text')
        if len(body.strip())<30:raise HTTPException(400,'Không đủ nội dung. PDF scan cần được OCR trước khi tải lên.')
        if len(body)>12000:raise HTTPException(400,'Chia tài liệu thành các mục dưới 12.000 ký tự')
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
    quality_feedback.install(app,connect,user,docs_for,now,audit)

    return app


app=create_app()
