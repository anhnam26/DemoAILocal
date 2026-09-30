"""Offline corpus audit and retrieval benchmark. Never imports app or opens its DB."""
import argparse,collections,json,re
from pathlib import Path
import rag,sync_knowledge
ROOT=Path(__file__).resolve().parent

def audit(documents):
    titles=collections.Counter(rag.norm(d['title']) for d in documents if d.get('data_type')=='glossary')
    rows=[]
    for d in documents:
        body=rag.norm(d['body']);flags=[]
        if d.get('review_status')=='draft_engineer_review':flags.append('technical_review_required')
        if d.get('data_type')=='glossary' and titles[rag.norm(d['title'])]>1:flags.append('repeated_glossary_title')
        if d.get('data_type')=='glossary' and 'cach thuc hien:' in body:flags.append('definition_mixed_with_procedure')
        if 'chua co' in body or 'chua xac nhan' in body:flags.append('unfilled_template_not_fact')
        if 'demo' in body:flags.append('illustrative_content')
        if not d.get('references'):flags.append('no_external_reference')
        rows.append(dict(id=d['id'],title=d['title'],status=d['status'],flags=flags))
    return dict(documents=len(documents),groups=dict(collections.Counter(d['group'] for d in documents)),
                flags=dict(collections.Counter(f for row in rows for f in row['flags'])),documents_review=rows)

def evaluate(documents,cases):
    active=[d for d in documents if d['status']=='approved'];rows=[]
    for case in cases:
        found,_=rag.retrieve(case['question'],active,6)
        _,selected,estimated=rag.pack(case['question'],found,12000)
        ids={d['id'] for d in found};packed={d['id'] for d in selected}
        required=case.get('required',[])
        hit=all(any(id in ids for id in alternatives) for alternatives in required)
        retained=all(any(id in packed for id in alternatives) for alternatives in required)
        rows.append(dict(id=case['id'],kind=case['kind'],question=case['question'],hit=hit,packed_hit=retained,
                         retrieved=[d['id'] for d in found],packed=[d['id'] for d in selected],estimated_bytes=estimated))
    scored=[r for r,c in zip(rows,cases) if c.get('required')]
    return dict(cases=len(rows),scored=len(scored),retrieval_pass=sum(r['hit'] for r in scored),
                packed_pass=sum(r['packed_hit'] for r in scored),results=rows,
                limitation='Source-ID coverage only; not an assessment of generated answers or semantic entailment.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cases',type=Path,default=ROOT/'knowledge/evaluation.json')
    args=parser.parse_args();docs=sync_knowledge.load()
    result={'corpus_digest':rag.fingerprint(docs),'audit':audit(docs)}
    if args.cases.exists():result['benchmark']=evaluate(docs,json.loads(args.cases.read_text(encoding='utf8')))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.get('benchmark',{}).items() if k!='results'},ensure_ascii=False))
if __name__=='__main__':main()
