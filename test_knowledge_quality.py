import json
from pathlib import Path
import pytest
import rag,sync_knowledge,knowledge_quality
ROOT=Path(__file__).resolve().parent

@pytest.fixture(scope='module')
def corpus():return sync_knowledge.load()

@pytest.mark.parametrize('question,expected',[
    ('Mô hình OSI khác gì với TCP/IP?','KB-NET-LAYERS'),
    ('TCP là gì?','ND-A9A43D59581C2EE5D4C3'),
    ('DNS cache và TTL hoạt động ra sao?','KB-NET-DNS'),
    ('Truy cập IP được nhưng tên miền không được','KB-NET-DNS-TROUBLE'),
    ('Khi nào nên dùng backup và khi nào dùng HA?','CMP-BACKUP-HA'),
    ('Quy trình RMA gồm những bước nào?','ND-258DF984EE1F1E9E071C')])
def test_multiple_intents_retrieve_and_retain(question,expected,corpus):
    found,_=rag.retrieve(question,corpus)
    budget,_=rag.budgets(question,18000,2400)
    _,selected,_=rag.pack(question,found,budget)
    assert expected in [d['id'] for d in selected]
    for d in selected:
        original=next(f for f in found if (f['id'],f['chunk'])==(d['id'],d['chunk']))
        assert original['body']==d['body']

def test_atomic_procedure_not_truncated_or_deduplicated():
    body='Điều kiện: được duyệt.\nBước 1: kiểm tra.\nRollback: khôi phục cấu hình.'
    a=sync_knowledge.document('A','Procedure',body,'B')
    b=sync_knowledge.document('B','Different procedure',body+'\nCảnh báo riêng.','B')
    assert len(rag.chunks(a))==1
    _,selected,_=rag.pack('Quy trình?',rag.chunks(a)+rag.chunks(b),6000)
    assert [d['body'] for d in selected]==[body,b['body']]
    huge={**a,'body':body*1000}
    _,selected,_=rag.pack('Quy trình?',rag.chunks(huge),6000)
    assert not selected

def test_glossary_separates_concept_without_changing_source_digest():
    d=sync_knowledge.document('TCP','TCP','TCP\nĐịnh nghĩa: giao thức.\nĐầu vào: IP\nCách thực hiện: NAT\nRollback: phục hồi','A',data_type='glossary')
    chunks=rag.chunks(d)
    assert len(chunks)==2 and 'NAT' not in chunks[0]['body']
    assert chunks[0]['source_digest']==chunks[1]['source_digest']
    assert chunks[0]['content_kind']=='concept' and chunks[1]['content_kind']=='procedure'

def test_corpus_integrity_and_review_labels(corpus):
    by_id={d['id']:d for d in corpus}
    assert len(by_id)==len(corpus)
    assert 'Transmission Control Protocol' in by_id['ND-A9A43D59581C2EE5D4C3']['body']
    assert by_id['KB-NET-LAYERS']['references']
    assert '12.000.000 VND' not in by_id['CMP-FW-WAF']['body']
    assert by_id['RUN-SIEM']['body'] and by_id['RUN-SIEM']['status']=='approved'
    assert any(d['review_status']=='draft_engineer_review' for d in corpus)

def test_audit_flags_are_not_automatic_approval(corpus):
    report=knowledge_quality.audit(corpus)
    assert report['documents']==len(corpus)
    assert report['flags']['technical_review_required']>1000

def test_unscored_negative_not_counted_as_success(corpus):
    report=knowledge_quality.evaluate(corpus,[dict(id='negative',kind='insufficient',question='xyzabc',required=[])])
    assert report['scored']==0 and report['negative_cases_not_scored']==1
    assert report['results'][0]['hit'] is None and report['retrieval_pass']==0


def test_adaptive_caps_and_proxy_are_explicit():
    assert rag.budgets('DNS là gì?',18000,2400)==(8000,1000)
    assert rag.budgets('Các bước cấu hình VLAN',18000,2400)==(18000,2400)
    assert rag.budgets('So sánh OSI TCP/IP',5000,700)==(5000,700)
    assert rag.estimate_tokens('tiếng Việt')==len('tiếng Việt'.encode('utf8'))
