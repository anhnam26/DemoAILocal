"""Validate the deployable corpus and mirror source revisions into SQLite."""
import hashlib,json
from pathlib import Path
from cyberant.rag import GROUPS
ROOT=Path(__file__).resolve().parents[1]

def document(id,title,body,group,**metadata):
    return dict(id=id,title=title,body=body,group=group,category=GROUPS[group],roles=['member','admin'],
                customer=None,version='knowledge-1',status='approved',valid_from='2026-01-01',valid_to='2099-12-31',
                owner='Kho tri thức chung',knowledge_type='theory',review_status='reference',**metadata)

def load(path=None):
    manifest_path=Path(path or ROOT/'knowledge/manifest.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    if manifest.get('version')!=1 or not isinstance(manifest.get('documents'),list):raise ValueError('Manifest không hợp lệ')
    docs=[];seen_paths=set();base=manifest_path.parent.resolve()
    for entry in manifest['documents']:
        relative=entry['path'];file=(base/relative).resolve()
        if not file.is_relative_to(base/'documents') or file.suffix!='.json' or relative in seen_paths:raise ValueError('Đường dẫn nguồn không hợp lệ/trùng')
        seen_paths.add(relative);raw=file.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Checksum nguồn không khớp: '+relative)
        d=json.loads(raw)
        if d['id']!=entry['id']:raise ValueError('ID nguồn không khớp manifest')
        docs.append(d)
    actual={p.resolve() for p in (base/'documents').rglob('*.json')}
    if actual!={(base/e['path']).resolve() for e in manifest['documents']}:raise ValueError('Manifest không bao phủ toàn bộ nguồn')
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
        c.execute('BEGIN IMMEDIATE')
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
