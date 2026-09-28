from pathlib import Path
import json,re
root=Path(__file__).resolve().parent
# Preserve every normalized theory source; the running server no longer needs raw workbooks.
docs=json.loads((root/'data/knowledge_documents.json').read_text(encoding='utf8'))
(root/'knowledge').mkdir(exist_ok=True)
(root/'knowledge/documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')
p=root/'app.py';s=p.read_text(encoding='utf8')
s=s.replace('import system_runtime\nimport runtime_limits\n','import config,token_usage\n')
s=s.replace("DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)","DATA=config.data_dir(); DATA.mkdir(parents=True,exist_ok=True)")
s=s.replace("DB=DATA/'demo.sqlite3'","DB=DATA/'app.sqlite3'")
s=s.replace("c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c","c=sqlite3.connect(DB,timeout=30); c.row_factory=sqlite3.Row; c.execute('PRAGMA busy_timeout=30000'); return c")
s=s.replace("    if not (DATA/'knowledge_documents.json').exists():sync_knowledge.build()", "    config.security()\n    with connect() as c:c.execute('PRAGMA journal_mode=WAL')")
s=s.replace('    accounts.init(connect)\n','    accounts.init(connect)\n    token_usage.init(connect)\n')
start=s.index('    # A one-time privacy migration');end=s.index('init()\napp=',start)
s=s[:start]+"    sync_knowledge.synchronize(connect,sync_knowledge.load())\n"+s[end:]
s=s.replace("init()\napp=", "init()\ntoken_usage.recover(connect)\napp=")
s=s.replace("docs_url=None,redoc_url=None)","docs_url=None,redoc_url=None,openapi_url=None)")
start=s.index("    host=request.headers.get('host'");end=s.index('    res=await call_next(request)',start)
s=s[:start]+'''    from urllib.parse import urlsplit
    security=config.security()
    host=urlsplit('//'+request.headers.get('host','')).hostname
    if host not in security['hosts']:return Response('Host denied',400)
    origin=request.headers.get('origin')
    if origin and origin.rstrip('/') not in security['origins']:return Response('Origin denied',403)
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('sec-fetch-site')=='cross-site':return Response('Cross-site denied',403)
    length=request.headers.get('content-length')
    if length and (not length.isdigit() or int(length)>2100000):return Response('Request too large',413)
''' + s[end:]
s=s.replace("    res.headers['Cache-Control']='no-store'", "    res.headers['Cache-Control']='no-store'\n    res.headers['Referrer-Policy']='same-origin'\n    if security['production']:res.headers['Strict-Transport-Security']='max-age=31536000'")
start=s.index("@app.get('/api/health')");end=s.index("@app.get('/api/documents')",start)
s=s[:start]+'''@app.get('/api/health')
def health():
    return {'status':'ok','provider':'openrouter'}

@app.get('/api/account/usage')
def my_usage(req:Request):return token_usage.summary(connect,user(req)['id'])

@app.get('/api/model')
def my_model(req:Request):
    u=user(req)
    return dict(model=u['model'],mode='openrouter',configured=u['model'] in model_provider.models() and bool(model_provider.settings()['api_key']),generation=LOCK.status())

''' + s[end:]
s=s.replace("    cfg=model_provider.settings();usage={};estimated=0;calls=0;found=[];used=[];review=True", "    try:cfg=model_provider.settings(u['model'])\n    except ValueError as e:raise HTTPException(400,str(e))\n    usage={};estimated=0;calls=0;found=[];used=[];review=True")
start=s.index("            if cfg['mode']=='local':");end=s.index('            try:messages,found,estimated=',start)
s=s[:start]+s[end:]
s=s.replace("                await LOCK.enter(parallel)\n                try:\n                    calls=1\n                    answer,usage,finish=await model_provider.complete(messages,cfg,output)","""                # Validate config before reserving; all accounting uses the database owner/model.
                try:model_provider.headers(cfg)
                except ValueError as e:raise HTTPException(503,str(e))
                await LOCK.enter(parallel)
                reservation=None
                try:
                    fresh=user(req)
                    reservation,output=token_usage.reserve(connect,fresh['id'],cfg['model'],estimated,output)
                    token_usage.mark_sent(connect,reservation)
                    calls=1
                    answer,usage,finish=await model_provider.complete(messages,cfg,output)
                    token_usage.settle(connect,reservation,usage)
""")
s=s.replace("                except httpx.HTTPStatusError as e:\n                    status=e.response.status_code", "                except model_provider.InvalidCompletion as e:\n                    token_usage.settle(connect,reservation,e.usage)\n                    raise HTTPException(503,'Model không trả nội dung; usage đã được ghi nhận nếu nhà cung cấp trả về.')\n                except httpx.HTTPStatusError as e:\n                    status=e.response.status_code\n                    token_usage.settle(connect,reservation,rejected=status in (400,401,402,403,404,422,429))")
s=s.replace("                finally:LOCK.leave()","                finally:\n                    if reservation:token_usage.settle(connect,reservation)\n                    LOCK.leave()")
s=s.replace('Kiểm tra .env/kết nối hoặc model local.','Kiểm tra cấu hình model hoặc kết nối OpenRouter.')
s=s.replace("usage=usage,api_calls=", "usage=usage,model=cfg['model'],api_calls=")
s=s.replace("    out['conversation_id']=conversation_id", "    out['conversation_id']=conversation_id\n    out['account_usage']=token_usage.summary(connect,u['id'])")
p.write_text(s,encoding='utf8')
