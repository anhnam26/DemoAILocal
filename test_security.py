import app
from test_app import isolated_db,client
from security_data import build

def test_security_sources_and_audience():
    docs=build();assert len(docs)==48 and len({d['topic'] for d in docs})==24
    assert all(d['references'][0]['url'].startswith('https://') for d in docs)
    sale=client('sale');tech=client('technical')
    assert sale.get('/api/documents/SEC-LAB-RANSOMWARE').status_code==404
    assert tech.get('/api/documents/SEC-LAB-RANSOMWARE').status_code==200
    d=sale.get('/api/documents/SEC-GUIDE-MFA').json()
    assert d['references'] and d['reviewed_at']=='2026-09-05'

def test_security_retrieval_relevance():
    for q,topic in [('MFA chống phishing là gì?','MFA'),('Zero Trust là gì?','ZERO-TRUST'),('Ưu tiên lỗ hổng theo KEV thế nào?','KEV'),('Checklist ứng cứu khi nghi nhiễm ransomware','RANSOMWARE'),('Bảo mật API kiểm quyền đối tượng','API'),('Prompt injection AI nội bộ RAG','AI-RAG')]:
        found=app.retrieve(q,app.PROFILES['technical'])
        assert any(d.get('topic')==topic for d in found),(q,[d['id'] for d in found])
    found=app.retrieve('Checklist ứng cứu khi nghi nhiễm ransomware',app.PROFILES['technical'])
    assert all(len(d['body'])>250 for d in found)
    assert any('Báo đầu mối' in d['body'] for d in found)

def test_retired_security_doc_is_not_returned():
    a=client('admin');c=client('sale');id='SEC-GUIDE-MFA'
    a.post('/api/admin/documents/'+id+'/retire')
    assert c.get('/api/documents/'+id).status_code==404
    assert id not in {d['id'] for d in app.retrieve('MFA chống phishing',app.PROFILES['sale'])}
