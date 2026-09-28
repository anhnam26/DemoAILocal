"""Read-only inventory of project sources and data (never prints secrets)."""
import ast, collections, hashlib, importlib.util, json, os, sqlite3, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent
skip = {'.git', '.venv', '.venv-runtime', '__pycache__', '.pytest_cache', 'runtime', 'models'}
report=[]
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in skip]
    for name in sorted(files):
        p=Path(base)/name; rel=p.relative_to(ROOT).as_posix()
        if name.startswith('.env') or name in {'initial-accounts.json','model-api-key.txt'}:
            if name=='.env': print('ENV KEYS', [s.split('=',1)[0].strip() for s in p.read_text().splitlines() if '=' in s])
            report.append({'path':rel,'kind':'secret - values omitted'}); continue
        raw=p.read_bytes(); item={'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        try:
            if p.suffix in {'.json','.jsonl'}:
                text=raw.decode('utf-8-sig'); data=json.loads(text) if p.suffix=='.json' else [json.loads(s) for s in text.splitlines() if s.strip()]
                item['kind']='json';item['count']=len(data);item['keys']=list(data)[:20] if isinstance(data,dict) else list(data[0]) if data and isinstance(data[0],dict) else []
                if isinstance(data,list) and data and isinstance(data[0],dict):
                    item['types']={k:dict(collections.Counter(str(d.get(k,'')) for d in data)) for k in ('category','type','record_type','knowledge_type') if any(k in d for d in data)}
            elif p.suffix=='.py':
                text=raw.decode('utf-8-sig');tree=ast.parse(text); item['definitions']=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
            elif p.suffix in {'.md','.txt','.ps1','.js','.html','.css','.csv'}:
                text=raw.decode('utf-8-sig');item['lines']=len(text.splitlines())
            elif p.suffix in {'.xlsx','.docx','.zip'}:
                with zipfile.ZipFile(p) as z:
                    item['entries']=[x.filename for x in z.infolist()];item['expanded_bytes']=sum(len(z.read(n)) for n in z.namelist())
            elif p.suffix in {'.sqlite','.sqlite3'}:
                with sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True) as c:
                    item['tables']=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                    for table in item['tables']:
                        c.execute('SELECT * FROM "'+table.replace('"','""')+'"').fetchall()
            else:item['kind']='binary read'
        except Exception as e:item['error']=type(e).__name__
        report.append(item)
out=ROOT/'artifacts'/'workspace_inventory.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('READ',len(report),'files;',sum(x.get('bytes',0) for x in report),'bytes')
print('MODULES', {m:bool(importlib.util.find_spec(m)) for m in ['openpyxl','pypdf','dotenv','pytest','playwright','tiktoken']})
for x in report:
    if x['path'].startswith('NewData/') and ('count' in x or 'error' in x):print(json.dumps(x,ensure_ascii=False))
for path in ['data/demo_documents.json','data/company_operations.json','data/finance_documents.json','.local-internal/knowledge.json','NewData/data/processed/company_knowledge.jsonl','NewData/data/processed/it_configuration.json','NewData/data/processed/service_requirements.json','NewData/data/processed/customer_fields.json','NewData/data/processed/service_sow_templates.json','NewData/data/processed/glossary.json']:
    p=ROOT/path
    if not p.exists():continue
    raw=p.read_text(encoding='utf8');data=json.loads(raw) if p.suffix=='.json' else [json.loads(s) for s in raw.splitlines() if s.strip()]
    print('SAMPLE',path,json.dumps(data[:2] if isinstance(data,list) else {k:(v[:1] if isinstance(v,list) else str(v)[:150]) for k,v in data.items()},ensure_ascii=False)[:6000])
