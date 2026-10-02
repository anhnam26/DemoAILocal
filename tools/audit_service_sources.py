"""Read-only source/runtime audit. No app import, migration, sync or provider calls."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cyberant import config,rag,service_evidence,storage,sync_knowledge
from pypdf import PdfReader

S={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def workbook(path):
    """Report cached values, not recalculate Excel or certify cache freshness."""
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(t.text or '' for t in si.findall('.//s:t',S))
                     for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',S)]
        rels={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets=[]
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',S):
            target=rels[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            tree=ET.fromstring(z.read(target));cells=tree.findall('.//s:c',S);formulas=[]
            values={}
            for cell in cells:
                value=cell.findtext('s:v',default='',namespaces=S)
                if cell.get('t')=='s' and value:value=strings[int(value)]
                elif cell.get('t')=='inlineStr':value=''.join(t.text or '' for t in cell.findall('.//s:t',S))
                values[cell.attrib['r']]=value
                formula=cell.find('s:f',S)
                if formula is not None:
                    formulas.append(dict(cell=cell.attrib['r'],formula=formula.text,cached_value=value or None))
            effort=None
            if 'chuyen doi' in service_evidence.normalize(path.name) and 'thoi gian' in service_evidence.normalize(path.name):
                rows=[]
                for address,value in values.items():
                    if not re.fullmatch(r'D\d+',address):continue
                    row=address[1:]
                    try:duration=float(value);people=float(values.get('E'+row,''))
                    except ValueError:continue
                    rows.append(dict(row=int(row),duration_hours=duration,engineers=people,man_hours=duration*people))
                effort=dict(rows=rows,man_hours=sum(r['man_hours'] for r in rows),
                            summed_task_hours=sum(r['duration_hours'] for r in rows),
                            warning='Not project elapsed time or downtime; applicability requires project keys')
            sheets.append(dict(name=sheet.attrib['name'],state=sheet.get('state','visible'),cells=len(cells),
                               merged_ranges=len(tree.findall('.//s:mergeCell',S)),formulas=formulas,
                               empty_formula_caches=sum(f['cached_value'] is None for f in formulas),effort=effort))
        return dict(sheets=sheets,cache_freshness_verified=False)


def docx(path,documents):
    with zipfile.ZipFile(path) as z:
        tree=ET.fromstring(z.read('word/document.xml'))
        runs=[t.text for t in tree.findall('.//w:t',W) if t.text and t.text.strip()]
        records=[d for d in documents if d.get('service')==path.name]
        combined=re.sub(r'\s+',' ',' '.join(d['body'] for d in records))
        missing=sum(re.sub(r'\s+',' ',t).strip() not in combined for t in runs)
        return dict(body_text_runs=len(runs),missing_body_text_runs=missing,records=len(records),
                    tables=len(tree.findall('.//w:tbl',W)),
                    limitation='Text presence only; table relationships, images and headers not verified')


def runtime_comparison(path,documents):
    path=Path(path).resolve()
    if not path.is_file():return dict(path=str(path),available=False)
    # Do not use storage.connect(): it opens rw and attaches other stores.
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as c:
        c.execute('PRAGMA query_only=ON')
        rows=c.execute('SELECT id,payload FROM docs').fetchall()
        has_sync=c.execute("SELECT 1 FROM sqlite_master WHERE name='source_sync' AND type='table'").fetchone()
        sync=dict(c.execute('SELECT id,digest FROM source_sync')) if has_sync else None
    runtime={id:json.loads(payload) for id,payload in rows};source={d['id']:d for d in documents}
    common=runtime.keys()&source.keys()
    digests={id:hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for id,d in source.items()}
    return dict(path=str(path),available=True,source_count=len(source),runtime_count=len(runtime),
                source_missing_in_runtime=len(source.keys()-runtime.keys()),
                runtime_only_upload_or_legacy=len(runtime.keys()-source.keys()),
                changed_body=sum(runtime[id].get('body')!=source[id]['body'] for id in common),
                changed_payload=sum(runtime[id]!=source[id] for id in common),
                preserved_retired=sum(runtime[id].get('status')=='retired' and source[id]['status']!='retired' for id in common),
                runtime_review_status=dict(Counter(d.get('review_status','unknown') for d in runtime.values())),
                source_sync=dict(available=sync is not None,
                    missing_source_ids=len(source.keys()-sync.keys()) if sync is not None else None,
                    changed_digests=sum(sync[id]!=digests[id] for id in sync.keys()&source.keys()) if sync is not None else None),
                limitation='Explicit file snapshot only; does not establish the running process configuration')


def audit(source_dir,documents,runtime_db=None):
    files=[]
    for path in sorted(Path(source_dir).rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.docx','.xlsx','.pdf','.png'):continue
        item=dict(file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        try:
            if path.suffix.lower()=='.xlsx':item.update(workbook(path))
            elif path.suffix.lower()=='.docx':item.update(docx(path,documents))
            elif path.suffix.lower()=='.pdf':
                pages=PdfReader(path).pages
                item.update(pages=len(pages),text_chars_per_page=[len(p.extract_text() or '') for p in pages],
                            limitation='Text extraction does not verify diagram edges/branches')
            else:item['limitation']='Image requires human/OCR review; not contractual evidence'
        except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:item['error']=str(exc)
        files.append(item)
    services={}
    for service in service_evidence.SERVICES:
        docs=[d for d in documents if service_evidence.service_id(d)==service]
        present=set().union(*(service_evidence.facets(d) for d in docs))
        services[service]=dict(records=len(docs),types=dict(Counter(d.get('data_type','reference') for d in docs)),
                               evidence_origins=dict(Counter(service_evidence.link(d)['evidence_origin'] for d in docs)),
                               facets=sorted(present),missing_facets=sorted(set(service_evidence.FACET_LABELS)-present))
    titles=Counter((service_evidence.service_id(d),d['title']) for d in documents)
    data_dir=config.data_dir()
    return dict(read_only=True,corpus_count=len(documents),corpus_fingerprint=rag.fingerprint(documents),
                review_status=dict(Counter(d.get('review_status') for d in documents)),services=services,
                duplicate_title_groups=sum(n>1 for n in titles.values()),
                duplicate_policy='Review contextual duplicates; never merge by title alone',
                source_files=files,configuration=dict(env_file=str(config.env_path()),data_dir=str(data_dir),
                    expected_stores=[dict(path=str(p),exists=p.is_file()) for p in storage.paths(data_dir).values()]),
                runtime=runtime_comparison(runtime_db,documents) if runtime_db else {'checked':False},
                extraction_completeness_verified=False,technical_review_verified=False)


def evaluate(cases,documents):
    results=[]
    for case in cases:
        if case.get('stage')!='offline':continue
        q=case['question'];found,routing=rag.retrieve(q,documents,6)
        budget,output=rag.budgets(q,18000,2400);packing={}
        _,kept,size=rag.pack(q,found,budget,case.get('audience','auto'),packing)
        ids={d['id'] for d in kept};types={d.get('data_type') for d in kept}
        available={(s['service_id'],f) for s in routing.get('corpus_coverage',{}).get('services',[]) for f in s['present']}
        sent={(s['service_id'],f) for s in packing['coverage']['services'] for f in s['present']}
        fraction=len(available&sent)/len(available) if available else None
        checks=dict(intent=rag.intent(q)==case['intent'],
                    service=case['service_id'] in routing.get('service_ids',[]),
                    expected_ids=set(case.get('expected_ids',[]))<=ids,
                    expected_types=set(case.get('expected_types',[]))<=types,
                    available_facet_coverage=fraction is None or fraction>=.90)
        results.append(dict(id=case['id'],checks=checks,passed=all(checks.values()),
                            available_facet_coverage=fraction,selected_ids=sorted(ids),
                            estimated_input_bytes=size,output_limit=output,packing=packing))
    return dict(stage='offline_retrieval_only_not_answer_accuracy',cases=len(results),
                passed=sum(r['passed'] for r in results),results=results,provider_calls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=ROOT/'data')
    parser.add_argument('--runtime-db',type=Path,help='Explicit knowledge or legacy DB; read-only, never auto-migrate')
    parser.add_argument('--evaluate',action='store_true',help='Offline retrieval checks, not model accuracy')
    args=parser.parse_args();documents=sync_knowledge.load()
    if args.evaluate:
        cases=json.loads((ROOT/'knowledge/evaluation_services.json').read_text(encoding='utf8'))['cases']
        report=evaluate(cases,documents)
    else:report=audit(args.source_dir,documents,args.runtime_db)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.evaluate and report['passed']!=report['cases']:sys.exit(1)


if __name__=='__main__':main()