"""One-time extraction of theoretical sources before removing obsolete demo data."""
import json,re
from pathlib import Path
from sync_knowledge import document,build
ROOT=Path(__file__).resolve().parent
dest=ROOT/'data'/'sources';dest.mkdir(exist_ok=True)
old=[]
for d in json.loads((ROOT/'data'/'demo_documents.json').read_text(encoding='utf8')):
    # Strict allowlist: conceptual KB, runbooks, technical primers and comparisons.
    if d.get('customer') or not d['id'].startswith(('TECH-','KB-','TERM-','CMP-','RUN-')):continue
    body=d['body']; body=re.sub(r'^DỮ LIỆU DEMO GIẢ LẬP[^\n]*\n','',body)
    old.append(document(d['id'],d['title'],body,'A' if d['id'].startswith(('TERM-','CMP-')) else 'B',
                        provenance={'source':'legacy_demo','note':'Kiến thức tham khảo biên soạn; cần rà soát trước áp dụng.'}))
for d in json.loads((ROOT/'data'/'security_documents.json').read_text(encoding='utf8')):
    old.append(document(d['id'],d['title'],d['body'],'E',references=d.get('references',[]),provenance={'source':'security_documents'}))
(dest/'theory.json').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf8')
k=json.loads((ROOT/'.local-internal'/'knowledge.json').read_text(encoding='utf8'))
services=[]
for d in k['documents']:
    if d['kind']!='service':continue
    services.append(document(d['id'].upper(),d['title'],re.sub(r'^Khối \d+\n','',d['body'],flags=re.M),'C',
                             provenance={'source':'DataReal','location':d.get('location'),'sha256':d['sha256']},
                             service=d['title']))
(dest/'services.json').write_text(json.dumps(services,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(build(),ensure_ascii=False,indent=2))
