"""Complete sample inputs for every service estimate; compatible with the fictional catalogue."""
from pathlib import Path
import json,sqlite3
from company_data import build as base
from finance_data import build as finance
ROOT=Path(__file__).parent
def build():
    originals=base();services=originals['services'];new=[d for d in finance() if d['category']=='Gói trọn bộ' and d['fields']['service_id'] not in {s['id'] for s in services}]
    for d in new:
        f=d['fields'];services.append(dict(id=f['service_id'],name=d['title'].split(' — ')[0],price=f['service_fee'],days=f['effort'],scope=f['scope'],aliases=f['aliases'],conditions=f['conditions'],outputs='Hồ sơ phạm vi, báo cáo kiểm thử/pilot, hướng dẫn và danh sách việc tiếp theo',exclusions='Không gồm license, thiết bị, phí duy trì hoặc kiểm thử ngoài phạm vi đã được cấp quyền',delivery_min=f['delivery_min'],delivery_max=f['delivery_max'],valid_from='2026-01-01',valid_to='2027-12-31',source_id='RATE-'+f['service_id'].upper()))
    docs=[]
    for s in services:
        if s['id'] not in {x['id'] for x in originals['services'][:12]}:
            docs.append(dict(id=s['source_id'],title=s['name']+' — định mức công dịch vụ',category='Bảng giá',body=f'Gói DEMO {s["name"]}: phí công {s["price"]:,} VND, {s["days"]} ngày công; lịch 1 site/gói {s["delivery_min"]}–{s["delivery_max"]} ngày làm việc. Phạm vi {s["scope"]}. Điều kiện {s["conditions"]}. Không gồm thiết bị/license/duy trì và VAT; OFFER là gói có phạm vi tài chính riêng.',service=s))
        template=dict(service_id=s['id'],sites=1,readiness=True,complex=False,customer_id='A',requested_start='2026-09-14',engineers=1,scope=s['scope'],equipment='Thiết bị hoặc môi trường lab theo scope đã sẵn sàng',license='License lab hợp lệ và đủ phạm vi',access='Có tài khoản triển khai được cấp quyền; không nhập mật khẩu vào AI',window='Thứ Hai–thứ Sáu 08:30–17:30; change window theo PM',acceptance=s['outputs'],notes='Dữ liệu giả lập đầy đủ để test dự toán; lịch chưa giữ chỗ, không phải lịch thật.')
        docs.append(dict(id='INPUT-'+s['id'].upper(),title=s['name']+' — đầu vào dự toán đầy đủ',category='Đầu vào dự toán',body='## Hồ sơ đầu vào DEMO\n'+'\n'.join('- '+k+': '+str(v) for k,v in template.items()),estimate_template=template,requires=[s['source_id']]))
    for d in docs:d.update(roles=['sale','technical','admin'],customer=None,version='workflow-1.0',status='approved',valid_from='2026-01-01',valid_to='2027-12-31',owner='PM giả lập',synthetic=True)
    return docs
def install():
    docs=build();data=ROOT/'data'
    with sqlite3.connect(data/'demo.sqlite3') as db:
        for d in docs:
            row=db.execute('SELECT payload FROM docs WHERE id=?',(d['id'],)).fetchone()
            if row:
                old=json.loads(row[0])
                if old.get('version')!='workflow-1.0':continue
                d['status']=old['status']
            db.execute('INSERT OR REPLACE INTO docs VALUES(?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
    (data/'workflow_documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(documents=len(docs),templates=sum('estimate_template' in d for d in docs))))
if __name__=='__main__':install()
