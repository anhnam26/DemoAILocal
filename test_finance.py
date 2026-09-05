import json
from collections import Counter
import app
from test_app import isolated_db,client
from test_company import ask
from finance_data import build,SNAPSHOT
from finance_logic import calculate

def test_financial_ledger_reconciles():
    docs=build();byid={d['id']:d for d in docs}
    assert len(docs)==len(byid)==154
    inv=[d for d in docs if d['category']=='Chứng từ thu'];pay=[d for d in docs if d['category']=='Phiếu thu']
    assert len(inv)==40 and len(pay)==27
    for d in inv:
        f=d['fields'];receipts=[p['fields']['amount'] for p in pay if p['fields']['invoice_id']==d['id']]
        assert sum(receipts)==f['paid'] and f['amount']==f['paid']+f['outstanding']
        assert f['issued']<=SNAPSHOT and f['issued']<=f['due']
    for d in docs:
        f=d['fields']
        if d['category']=='Tài chính báo giá':
            assert sum(m['amount'] for m in f['milestones'])==f['total']==f['subtotal']+f['tax']
            assert all(m['invoice_id'] in byid for m in f['milestones'] if m['invoice_id'])
        if d['category']=='Công nợ':
            rows=[byid[id]['fields'] for id in f['invoice_ids']]
            assert f['billed']==sum(x['amount'] for x in rows)
            assert f['paid']==sum(x['paid'] for x in rows)
            assert f['outstanding']==f['billed']-f['paid']
        if d['category']=='Lịch định mức':assert sum(s['days'] for s in f['stages'])==f['effort']
        if d['category']=='Gói trọn bộ':assert f['subtotal']==sum(x['quantity']*x['unit_price'] for x in f['lines'])
    p=byid['FIN-PNL']['fields'];assert p['gross_profit']==p['revenue']-p['cogs'] and p['operating_result']==p['gross_profit']-p['opex']

def test_full_quote_exact_arithmetic():
    c=client('sale');r=c.post('/api/finance/estimate',json={'offer_id':'OFFER-FIREWALL','sites':2,'discount_percent':5}).json()
    assert r['subtotal']==78000000 and r['discount']==1200000 and r['net']==76800000
    assert r['tax']==7680000 and r['total']==84480000 and r['effort']==8
    assert r['year1']==148800000 and r['tco3']==328800000
    answer=ask(c,'Báo giá trọn gói firewall 2 site chiết khấu 5% gồm VAT')
    assert all(x in answer['answer'] for x in ('84.480.000','328.800.000','mô phỏng'))
    assert answer['mode']=='Tra cứu dữ liệu có cấu trúc'
    assert c.post('/api/finance/estimate',json={'offer_id':'OFFER-FIREWALL','sites':-1}).status_code==422
    assert c.post('/api/finance/estimate',json={'offer_id':'OFFER-FIREWALL','discount_percent':101}).status_code==422

def test_financial_acl_and_totals():
    sale=client('sale');tech=client('technical');admin=client('admin')
    s=sale.get('/api/finance').json();t=tech.get('/api/finance').json();a=admin.get('/api/finance').json()
    assert s['pnl'] is None and t['pnl'] is None and a['pnl']
    assert {c['customer'] for c in s['customers']}==set('ACEGI')
    for key in ('amount','paid','outstanding','overdue'):assert s['totals'][key]+t['totals'][key]==a['totals'][key]
    assert sum(a['aging'].values())==a['totals']['outstanding']
    assert sale.get('/api/documents/COST-A-01').status_code==404
    assert 'Quản trị' in ask(sale,'Lợi nhuận An Minh là bao nhiêu?')['answer']
    assert 'ngoài phạm vi' in ask(sale,'Xem công nợ Bình An Factory')['answer']
    assert 'AR-A' in ask(sale,'Công nợ An Minh Retail còn bao nhiêu?')['answer']
    assert 'FIN-QUOTE-A-01' in ask(sale,'Chi tiết thanh toán QUOTE-A-01 gồm VAT')['answer']

def test_source_retirement_invalidates_derived_calculation():
    admin=client('admin');c=client('sale')
    admin.post('/api/admin/documents/SKU-GATE-100/retire')
    assert c.get('/api/documents/OFFER-FIREWALL').status_code==404
    assert c.post('/api/finance/estimate',json={'offer_id':'OFFER-FIREWALL'}).status_code==404
    admin.post('/api/admin/documents/INV-A-01-1/retire')
    assert c.get('/api/documents/AR-A').status_code==404
    admin.post('/api/admin/documents/COST-A-02/retire')
    assert admin.get('/api/finance').json()['pnl'] is None

def test_security_pricing_and_sla_details():
    c=client('technical')
    r=ask(c,'Triển khai MFA giá bao nhiêu và mất mấy ngày?')
    assert '16.500.000' in r['answer'] and '4 ngày công' in r['answer']
    r=ask(c,'SLA PLUS chi tiết về khôi phục và bồi hoàn')
    assert '130.000' in r['answer'] and '8 giờ' in r['answer'] and '10%' in r['answer']
    r=ask(c,'Phân bổ ngày công chi tiết firewall')
    assert 'SCHEDULE-FIREWALL' in r['answer']
