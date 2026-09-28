"""Build the single theory corpus from explicit, customer-free source adapters."""
import hashlib,json,re,sqlite3
from collections import Counter
from pathlib import Path
from rag import GROUPS
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
CATEGORY_GROUP={'glossary':'A','it_configuration':'B','service_requirements':'C','service_sow':'D',
                'migration_sow':'D','migration_summary':'D','workflow':'D','bom_rules':'F','data_quality':'F'}

def document(id,title,body,group,**metadata):
    return dict(id=id,title=title,body=body.strip(),group=group,category=GROUPS[group],roles=['member','admin'],
                customer=None,version='knowledge-1',status='approved',valid_from='2026-01-01',valid_to='2099-12-31',
                owner='Kho tri thức chung',knowledge_type='theory',review_status='reference',**metadata)

def build(root=ROOT):
    root=Path(root);data=root/'data';documents=[];source_counts={}
    for file in sorted((data/'sources').glob('*.json')):
        rows=json.loads(file.read_text(encoding='utf8'))
        for d in rows:
            if d.get('customer') or d.get('is_example'):raise ValueError('Nguồn lý thuyết chứa hồ sơ khách hàng')
        documents.extend(rows);source_counts[file.name]=len(rows)
    new=root/'NewData'/'data'/'processed'/'company_knowledge.jsonl'
    if new.exists():
        rows=[json.loads(line) for line in new.read_text(encoding='utf8').splitlines() if line.strip()]
        for row in rows:
            m=row['metadata'];kind=m['category']
            if m.get('is_example') or m.get('customer_id') or kind not in CATEGORY_GROUP:continue
            d=document('ND-'+row['chunk_id'].upper(),m['title'],row['text'],CATEGORY_GROUP[kind],
                       data_type=kind,provenance={k:v for k,v in m.items() if k not in ('is_example','customer_id')},
                       service=m.get('service',''))
            d['review_status']=m.get('review_status','reference');documents.append(d)
        source_counts['NewData']=len(rows)
    # Exact normalized body deduplication preserves provenance aliases.
    unique={};ids=set()
    for d in documents:
        digest=hashlib.sha256(re.sub(r'\s+',' ',d['body']).strip().casefold().encode()).hexdigest()
        if digest in unique:
            unique[digest].setdefault('duplicate_sources',[]).append(d['id']);continue
        if d['id'] in ids:raise ValueError('Trùng ID nguồn: '+d['id'])
        ids.add(d['id']);unique[digest]=d
    docs=sorted(unique.values(),key=lambda d:d['id'])
    if not docs:raise ValueError('Kho tri thức rỗng; kiểm tra data/sources và NewData')
    payload=json.dumps(docs,ensure_ascii=False,indent=2)
    target=data/'knowledge_documents.json';tmp=target.with_suffix('.tmp');tmp.write_text(payload,encoding='utf8');tmp.replace(target)
    report=dict(documents=len(docs),groups=dict(Counter(d['group'] for d in docs)),sources=source_counts,
                duplicate_documents=len(documents)-len(docs),fingerprint=hashlib.sha256(payload.encode()).hexdigest(),
                review_status=dict(Counter(d['review_status'] for d in docs)))
    (data/'knowledge_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

def synchronize(connect,documents):
    """Mirror source additions/updates/deletions while preserving admin retirements."""
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS source_sync(id TEXT PRIMARY KEY,digest TEXT NOT NULL)')
        existing={r[0]:r[1] for r in c.execute('SELECT id,digest FROM source_sync')}
        ids={d['id'] for d in documents}
        for old in existing.keys()-ids:
            c.execute('DELETE FROM docs WHERE id=?',(old,));c.execute('DELETE FROM source_sync WHERE id=?',(old,))
        for d in documents:
            raw=json.dumps(d,ensure_ascii=False,sort_keys=True);digest=hashlib.sha256(raw.encode()).hexdigest()
            if existing.get(d['id'])==digest:continue
            old=c.execute('SELECT payload FROM docs WHERE id=?',(d['id'],)).fetchone()
            if old and json.loads(old[0]).get('status')=='retired':
                d={**d,'status':'retired'};raw=json.dumps(d,ensure_ascii=False,sort_keys=True)
            c.execute('INSERT OR REPLACE INTO docs VALUES(?,?)',(d['id'],raw))
            c.execute('INSERT OR REPLACE INTO source_sync VALUES(?,?)',(d['id'],digest))

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
