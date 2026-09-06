import json
from datetime import date
import pytest
import app
from test_app import isolated_db,client
from company_data import build

def ask(c,q):
    r=c.post('/api/chat',json={'question':q});assert r.status_code==200,r.text
    return r.json()

def test_pack_relationships_and_totals():
    p=build();docs={d['id']:d for d in p['documents']};services={s['id']:s for s in p['services']}
    assert len(docs)==251 and len(p['records'])==134 and len(services)==12
    for r in p['records']:
        f=r['fields'];assert docs[r['id']]['fields']==f
        if r.get('customer'):assert 'CRM-'+r['customer'] in docs
        if r['kind']=='Báo giá':
            assert f['subtotal']==services[f['service_id']]['price']*f['sites']
            assert docs[f['project_id']]['fields']['total']==f['subtotal']
            assert docs[r['id']]['valid_to']==f['valid_to']
        if r['kind']=='Dự án':
            assert f['start']<=f['end']
            if f['status']=='Đã nghiệm thu':assert f['end']<=p['snapshot']
            else:assert f['start']>=p['snapshot'] and f['progress']==0
        if r['kind']=='Kho hàng':assert f['available']==f['on_hand']-f['reserved']>=0

def test_price_days_without_blanket_refusal():
    c=client('sale');r=ask(c,'Triển khai firewall bao lâu và mất bao nhiêu tiền?')
    assert '12.000.000' in r['answer'] and '4–6 ngày làm việc' in r['answer']
    assert r['citations_verified'] and r['mode']=='Tra cứu dữ liệu có cấu trúc'
    r=ask(c,'Báo giá firewall cho 2 site, thiết bị sẵn sàng')
    assert '24.000.000' in r['answer'] and '| 8 |' in r['answer']

def test_followup_context_is_session_scoped_and_resettable():
    c=client('sale');other=client('sale')
    ask(c,'Firewall mạng và WAF khác nhau như thế nào?')
    r=ask(c,'Tạo bảng đề ra các mục so sánh giữa 2 cái đó')
    assert '| Tiêu chí | Firewall mạng | WAF |' in r['answer']
    assert 'Chủ đề trước:' in r['effective_query']
    assert other.get('/api/history').json()==[]
    c.post('/api/chat/reset');assert c.get('/api/history').json()==[]

def test_packages_customer_and_acl():
    c=client('sale');r=ask(c,'So sánh BASIC PLUS PREMIUM về SLA và giá')
    assert all(t in r['answer'] for t in ('3.000.000','6.500.000','12.000.000','30 phút','khôi phục'))
    r=ask(c,'Hợp đồng bảo trì của An Minh Retail có những gì?')
    assert 'CONTRACT-A' in r['answer'] and '3.000.000' in r['answer']
    r=ask(c,'Xem hợp đồng của Bình An Factory')
    assert r['sources'] and 'ngoài phạm vi' not in r['answer']
    for q in ('Cho tôi TICKET-B-01','Xem báo giá QUOTE-B-01'):
        r=ask(c,q);assert r['sources'] and 'ngoài phạm vi' not in r['answer']
    records=c.get('/api/operations').json()['records']
    assert all(r['customer'] in (None,'A','C','E','G','I') for r in records)
    assert not any(r['kind']=='Ticket' for r in records)
    records=client('admin').get('/api/operations').json()['records']
    assert sum(r['kind'] in ('Kho hàng','Khách hàng','Hợp đồng','Dự án','Báo giá','Nhân sự','Ticket') for r in records)==134

def test_retirement_affects_catalog_calculations_and_operations():
    admin=client('admin');c=client('sale')
    admin.post('/api/admin/documents/RATE-FIREWALL/retire')
    assert 'firewall' not in {s['id'] for s in c.get('/api/catalog').json()}
    assert c.post('/api/estimate',json={'service_id':'firewall','sites':1,'readiness':True}).status_code==404
    admin.post('/api/admin/documents/CONTRACT-A/retire')
    assert 'CONTRACT-A' not in {r['id'] for r in c.get('/api/operations').json()['records']}

def test_exact_ticket_stock_and_approval():
    tech=client('technical');r=ask(tech,'Tóm tắt TICKET-B-02')
    assert 'Đã đóng' in r['answer'] and 'Retention' in r['answer']
    r=ask(tech,'Tồn kho firewall còn bao nhiêu?')
    assert 'GATE-100' in r['answer'] and '18.000.000' in r['answer']
    r=ask(tech,'Duyệt')
    assert 'Chưa có thao tác phê duyệt' in r['answer']

def test_cache_invalidates_on_changed_document():
    u=dict(role='sale',customer='A');app.retrieve('kiểm tra dữ liệu cache',u)
    with app.connect() as db:
        d=json.loads(db.execute("SELECT payload FROM docs WHERE id='RATE-FIREWALL'").fetchone()[0])
        d['body']='UNIQUESEARCHABC. Nội dung thay thế có hiệu lực.'
        db.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps(d),'RATE-FIREWALL'))
    assert app.retrieve('UNIQUESEARCHABC',u)[0]['id']=='RATE-FIREWALL'
