"""Development migration of the previous app to the unified knowledge backend."""
from pathlib import Path
p=Path('app.py');s=p.read_text(encoding='utf8')
s=s.replace('from business import respond as business_answer, context_query, has, service_matches','import rag, model_provider, sync_knowledge')
s=s.replace('from finance_logic import respond as finance_answer, dashboard as finance_dashboard, calculate as finance_calculate','')
start=s.index('MODEL_URL=');end=s.index('LOCK=GenerationGate()')
s=s[:start]+s[end:]
start=s.index("    if not (DATA/'demo_documents.json').exists():");end=s.index('    with connect() as c:',start)
s=s[:start]+"    if not (DATA/'knowledge_documents.json').exists():sync_knowledge.build()\n"+s[end:]
start=s.index("        for d in json.loads((DATA/'demo_documents.json')");end=s.index('init()\napp=',start)
s=s[:start]+'''    accounts.init(connect)
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
''' + s[end:]
s=s.replace("title='CyberAnt Local Demo'","title='CyberAnt Knowledge'")
start=s.index('def docs_for(');end=s.index('def source(',start)
s=s[:start]+'''def docs_for(u=None,pending=False,shared=False):
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

''' + s[end:]
s=s.replace("'knowledge_type':d.get('knowledge_type','company_demo')","'knowledge_type':d.get('knowledge_type','theory'),'group':d.get('group','F'),'review_status':d.get('review_status','reference'),'provenance':d.get('provenance',{})")
start=s.index('class FinanceEstimate');end=s.index("@app.get('/')",start);s=s[:start]+s[end:]
start=s.index("@app.get('/api/health')");end=s.index("@app.get('/api/documents')",start)
s=s[:start]+'''@app.get('/api/health')
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

''' + s[end:]
start=s.index("@app.get('/api/catalog')");end=s.index("@app.post('/api/chat/reset')",start)
s=s[:start]+s[end:]
start=s.index("@app.get('/api/finance')");end=s.index("@app.post('/api/chat')",start)
s=s[:start]+s[end:]
start=s.index('async def answer_chat');end=s.index("@app.get('/api/history')",start)
s=s[:start]+'''async def answer_chat(data,req,u,conversation_id):
    start=time.monotonic();q=data.question.strip();allowed=docs_for(u);effective=q
    with connect() as c:
        previous=c.execute('SELECT question,result FROM chats WHERE conversation_id=? AND user_id=? ORDER BY id DESC LIMIT 1',(conversation_id,u['id'])).fetchone()
    if previous:
        prior=json.loads(previous['result']);ids={d['id'] for d in allowed}
        if all(d['id'] in ids for d in prior.get('sources',[])):
            effective=rag.followup(q,prior.get('effective_query',previous['question']))
    cfg=model_provider.settings();usage={};estimated=0;calls=0;found=[];used=[];review=True
    # No record lookup or invented customer identity; this costs zero API calls.
    if re.search(r'\\b(crm-|contract-|quote-|ticket-|cong no|ho so khach|ten khach hang|khach hang thuc|dien thoai khach)',rag.norm(effective)):
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
                    ids={d['id'] for d in found};cited=set(re.findall(r'\\[([A-Za-z0-9_-]+)\\]',answer))
                    used=[d['id'] for d in found if d['id'] in cited];used=list(dict.fromkeys(used))
                    review=finish=='length' or any(d.get('review_status')=='draft_engineer_review' for d in found)
                    review=review or any(t in rag.norm(q) for t in ('cau hinh','sla','gia','rollback','lenh'))
                    if not cited or not cited.issubset(ids):
                        answer='Bản tổng hợp chưa đạt kiểm tra mã nguồn. Các trích đoạn để đối chiếu:\\n\\n'+'\\n\\n'.join(d['body']+' ['+d['id']+']' for d in found[:2])
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

''' + s[end:]
s=s.replace("audience:str=Form('technical')","audience:str=Form('all')").replace("audience not in ('technical','all')","audience != 'all'").replace("roles=['sale','technical','admin']","roles=['member','admin']")
s=s.replace("owner='Quản trị demo')","owner='Quản trị',group='F',knowledge_type='theory',review_status='manual_review')")
s=s[:s.index('# Optional machine-local extension.')]
p.write_text(s,encoding='utf8')
# Convert roles without resetting account passwords.
p=Path('accounts.py');s=p.read_text(encoding='utf8').replace("ROLES={'sale':'Sales','technical':'Kỹ thuật','admin':'Quản trị'}","ROLES={'member':'Thành viên','admin':'Quản trị'}")
s=s.replace("[('sales','sale','Minh Anh',list('ACEGI')),('kythuat','technical','Hoàng Nam',list('BDFHJ')),('admin','admin','Quản trị hệ thống',['*'])]","[('member','member','Thành viên',[]),('admin','admin','Quản trị hệ thống',[])]")
s=s.replace("        for s in seeds:\n", "        for s in seeds:\n            s['role']='admin' if s['role']=='admin' else 'member';s['customers']=[]\n")
s=s.replace("title=ROLES[row['role']]+' • '+('Toàn hệ thống' if row['role']=='admin' else str(len(customers))+' khách hàng')","title=ROLES[row['role']]+' • Kho tri thức chung'")
s=s.replace("Vai trò phải là sales, kỹ thuật hoặc quản trị.","Vai trò phải là thành viên hoặc quản trị.")
s=s.replace("        if any(x not in list('ABCDEFGHIJ') for x in data.customers):raise HTTPException(400,'Mã khách hàng hợp lệ: A–J.')\n        return ['*'] if data.role=='admin' else sorted(set(data.customers))","        return []")
p.write_text(s,encoding='utf8')
