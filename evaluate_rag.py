"""Repeatable offline evaluation; does not call a model or send data externally."""
import json
from pathlib import Path
import rag,model_provider
root=Path(__file__).resolve().parent
docs=json.loads((root/'data/knowledge_documents.json').read_text(encoding='utf8'))
questions=json.loads((root/'NewData/data/evaluation/questions.json').read_text(encoding='utf8'))
cfg=model_provider.settings();results=[]
for case in questions:
    found,route=rag.retrieve(case['question'],docs,cfg['top_k'])
    messages,selected,count=rag.pack(case['question'],found,cfg['input_budget'])
    expected=set(case['expected_categories'])
    kinds={d.get('data_type') for d in found};packed={d.get('data_type') for d in selected}
    baseline=sum(rag.estimate_tokens(d['body']) for d in docs if d['group'] in route['groups'])
    results.append(dict(id=case['id'],question=case['question'],category_hit=bool(kinds&expected),packed_category_hit=bool(packed&expected),
                        selected=[{'id':d['id'],'title':d['title'],'type':d.get('data_type')} for d in selected],
                        groups=route['groups'],estimated_input=count,whole_groups_estimated_input=baseline,
                        reduction_vs_groups=round(1-count/baseline,4) if baseline else None))
report=dict(questions=len(results),category_hits=sum(x['category_hit'] for x in results),
            packed_category_hits=sum(x['packed_category_hit'] for x in results),results=results)
(root/'artifacts').mkdir(exist_ok=True)
(root/'artifacts/retrieval_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
