"""Validate the deployable corpus and mirror source revisions into SQLite."""
import hashlib,json
from pathlib import Path
from rag import GROUPS
ROOT=Path(__file__).resolve().parent

def document(id,title,body,group,**metadata):
    return dict(id=id,title=title,body=body,group=group,category=GROUPS[group],roles=['member','admin'],
                customer=None,version='knowledge-1',status='approved',valid_from='2026-01-01',valid_to='2099-12-31',
                owner='Kho tri thức chung',knowledge_type='theory',review_status='reference',**metadata)

def load(path=None):
    docs=json.loads(Path(path or ROOT/'knowledge/documents.json').read_text(encoding='utf8'))
    if not isinstance(docs,list) or not docs:raise ValueError('Kho tri thức phải là danh sách không rỗng')
    ids=set()
    for d in docs:
        if d.get('customer') or d.get('is_example') or d.get('knowledge_type')!='theory':raise ValueError('Chỉ nhập dữ liệu lý thuyết')
        for key in ('id','title','body','category','version','owner','valid_from','valid_to','status'):
            if not isinstance(d.get(key),str) or not d[key]:raise ValueError('Nguồn thiếu '+key)
        if d['id'] in ids:raise ValueError('Trùng mã nguồn')
        if d['group'] not in GROUPS or d['status'] not in ('approved','pending','retired'):raise ValueError('Nhóm/trạng thái không hợp lệ')
        ids.add(d['id'])
    return docs

def synchronize(connect,documents):
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
            if old and json.loads(old[0]).get('status')=='retired':raw=json.dumps({**d,'status':'retired'},ensure_ascii=False,sort_keys=True)
            c.execute('INSERT OR REPLACE INTO docs VALUES(?,?)',(d['id'],raw))
            c.execute('INSERT OR REPLACE INTO source_sync VALUES(?,?)',(d['id'],digest))
