"""Read approved financial snapshots and compute proposals without using LLM arithmetic."""
import re
from business import has,norm,money,table

def calculate(offer,sites=1,discount_percent=0):
    if not 1<=sites<=5 or not 0<=discount_percent<=20:raise ValueError('Demo nhận 1–5 site và chiết khấu đề xuất 0–20%.')
    f=offer['fields'];subtotal=f['subtotal']*sites
    discount=(f['service_fee']*sites*discount_percent+50)//100
    net=subtotal-discount;tax=(net*f['tax_percent']+50)//100;monthly=f['support_monthly']*sites;annual=f['license_annual']*sites
    return dict(offer_id=offer['id'],sites=sites,subtotal=subtotal,discount_percent=discount_percent,discount=discount,net=net,tax_percent=f['tax_percent'],tax=tax,total=net+tax,effort=f['effort']*sites,delivery_min=f['delivery_min'],delivery_max=f['delivery_max'],monthly=monthly,license_annual=annual,year1=net+12*monthly,tco3=net+36*monthly+2*annual,scope=f['scope'],status='Đề xuất DEMO — chưa duyệt',lines=[{**x,'quantity':x['quantity']*sites,'amount':x['amount']*sites} for x in f['lines']])

def quote_answer(d,sites=1,discount_percent=0):
    r=calculate(d,sites,discount_percent)
    answer=f'## 1. {d["title"]} — {sites} gói/site\n'+table([['Hạng mục','SL','Đơn giá','Thành tiền']]+[[x['item'],x['quantity'],money(x['unit_price']),money(x['amount'])] for x in r['lines']])
    answer+='\n\n## 2. Dự toán thanh toán\n'+table([['Chỉ tiêu','Số tiền'],['Cộng dòng hàng',money(r['subtotal'])],[f'Chiết khấu {discount_percent}% chỉ trên công dịch vụ',money(r['discount'])],['Sau chiết khấu',money(r['net'])],[f'VAT mô phỏng {r["tax_percent"]}%',money(r['tax'])],['Tổng thanh toán',money(r['total'])]])
    answer+=f'\n\n## 3. Thời gian và duy trì\n- {r["effort"]} ngày công. Khung 1 gói/site {r["delivery_min"]}–{r["delivery_max"]} ngày làm việc sau đủ đầu vào; nhiều site do PM xếp lịch.\n- Phạm vi mỗi gói: {r["scope"]}.\n- Duy trì {money(r["monthly"])}/tháng; license gia hạn {money(r["license_annual"])}/năm.\n- Năm đầu trước thuế {money(r["year1"])}; TCO 3 năm trước thuế {money(r["tco3"])}.\n- TCO = giá mua sau chiết khấu + 36 tháng duy trì + 2 lần gia hạn license, giả định không tăng giá/quy mô.\n\n## 4. Điều kiện DEMO\n- VAT 10% chỉ là tham số mô phỏng; không phải xác định thuế suất thật.\n- Chiết khấu là đề xuất, không tự phê duyệt. Chưa gửi báo giá hoặc giữ hàng.\n- Gói OFFER không thay báo giá dịch vụ QUOTE đã ký trong kịch bản. [{d["id"]}] [FIN-RULES]'
    return answer

def dashboard(docs):
    invoices=[d for d in docs if d['category']=='Chứng từ thu'];costs=[d for d in docs if d['category']=='Giá vốn nội bộ' and d['fields']['recognition']=='Đã nghiệm thu']
    totals={k:sum(d['fields'][k] for d in invoices) for k in ('amount','paid','outstanding')}
    totals['overdue']=sum(d['fields']['outstanding'] for d in invoices if d['fields']['overdue_days']>0)
    ages={key:0 for key in ('not_due','1_30','31_60','over_60')}
    for d in invoices:
        f=d['fields'];days=f['overdue_days'];key='not_due' if days==0 else '1_30' if days<=30 else '31_60' if days<=60 else 'over_60';ages[key]+=f['outstanding']
    bycustomer={}
    for d in invoices:
        f=d['fields'];row=bycustomer.setdefault(d['customer'],dict(customer=d['customer'],billed=0,paid=0,outstanding=0,overdue=0,source_ids=[]))
        for k,field in [('billed','amount'),('paid','paid'),('outstanding','outstanding')]:row[k]+=f[field]
        if f['overdue_days']>0:row['overdue']+=f['outstanding']
        row['source_ids'].append(d['id'])
    names={d['customer']:d['fields']['name'] for d in docs if d['id'].startswith('CRM-')}
    for cid,r in bycustomer.items():r['name']=names.get(cid,'Khách '+cid)
    return dict(snapshot='2026-09-05',totals=totals,aging=ages,customers=list(bycustomer.values()),invoice_count=len(invoices),offers=[dict(id=d['id'],title=d['title'],**d['fields']) for d in docs if d['category']=='Gói trọn bộ'],pnl=next((d['fields'] for d in docs if d['id']=='FIN-PNL'),None))

def respond(q,docs,role):
    n=norm(q);byid={d['id']:d for d in docs}
    if any(has(q,t) for t in ('duyet','gui bao gia','chot gia','chot lich')) and not any(has(q,t) for t in ('ai duyet','quy trinh','chinh sach')):return None
    def excerpt(items):
        return '\n\n'.join('## '+d['title']+'\n'+d['body']+'\n['+d['id']+']' for d in items),items,True
    if any(has(q,t) for t in ('gia von','loi nhuan','lai gop','bien loi nhuan','pnl','chi phi quan ly')):
        if role!='admin':return 'Giá vốn và báo cáo lợi nhuận chỉ dành cho tài khoản Quản trị demo. Tài khoản này có thể xem giá bán và công nợ của khách được phân công.',[],True
        costs=[d for d in docs if d['category']=='Giá vốn nội bộ']
        customers=[d for d in docs if d['id'].startswith('CRM-') and (has(q,' '.join(d['fields']['name'].split()[:2])) or has(q,'khach '+d['customer']))]
        if customers:return excerpt([d for d in costs if d['customer'] in {x['customer'] for x in customers}])
        if 'FIN-PNL' in byid:return excerpt([byid['FIN-PNL']])
    direct=[d for d in docs if d.get('finance') and has(q,d['id'])]
    if direct:return excerpt(direct[:4])
    customers=[d for d in docs if d['id'].startswith('CRM-') and (has(q,' '.join(d['fields']['name'].split()[:2])) or has(q,'khach '+d['customer']) or has(q,'khach hang '+d['customer']))]
    ids={d['customer'] for d in customers}
    oldquotes=[d['id'] for d in docs if d['category']=='Báo giá' and has(q,d['id'])]
    if oldquotes and any(has(q,t) for t in ('chi tiet','vat','thue','thanh toan','tong tien','tai chinh')):
        items=[byid['FIN-'+id] for id in oldquotes if 'FIN-'+id in byid]
        if items:return excerpt(items)
    if any(has(q,t) for t in ('cong no','qua han','con no','da thu','phai thu')):
        if ids:
            items=[d for d in docs if d['category']=='Công nợ' and d['customer'] in ids]
            if items:return excerpt(items)
        data=dashboard(docs);sources=[d for d in docs if d['category']=='Chứng từ thu']
        if sources:
            rows=[['Khách DEMO','Đã phát hành','Đã thu','Còn nợ','Quá hạn']]+[[r['name'],money(r['billed']),money(r['paid']),money(r['outstanding']),money(r['overdue'])] for r in data['customers']]
            return '## Công nợ trong phạm vi tài khoản / 05-09-2026\n'+table(rows)+'\n\n- Chỉ cộng chứng từ được phép xem; không gồm đợt chưa phát hành hoặc toàn bộ sổ công ty.\n- Số liệu là snapshot giả lập, không tự thay đổi theo ngày hiện tại.\n'+' '.join('['+d['id']+']' for d in sources),sources,True
    if ids and any(has(q,t) for t in ('thanh toan','tai chinh','chi tiet bao gia','tien do thu','tong tien','vat')):
        items=[d for d in docs if d['category']=='Tài chính báo giá' and d['customer'] in ids]
        if items:return excerpt(items[:4])
    if any(has(q,t) for t in ('sla','boi hoan','tin dung dich vu','muc tieu khoi phuc','onsite','p4')) and any(has(q,t) for t in ('chi tiet','day du','boi hoan','tin dung','khoi phuc','onsite','p4','cap nhat')):
        details=[d for d in docs if d['category']=='SLA chi tiết'];selected=[d for d in details if has(q,d['fields']['package'])]
        if ids:
            packages={d['fields']['package'] for d in customers};selected=[d for d in details if d['fields']['package'] in packages]
        if selected or details:return excerpt(selected or details)
    offers=[d for d in docs if d['category']=='Gói trọn bộ'];matched=[d for d in offers if any(has(q,t) for t in d['fields']['aliases']+[d['fields']['service_id']])]
    wants=any(has(q,t) for t in ('tron goi','tron bo','tco','3 nam','nam dau','license','thiet bi va','bao gom thiet bi','sau thue','vat','tong chi phi'))
    newservice=matched and any(d['fields']['service_id'] not in {'firewall','wifi','backup','waf','switch','server','endpoint','pam','siem','audit','training','migration'} for d in matched)
    if matched and (wants or newservice and any(has(q,t) for t in ('gia','bao lau','ngay','chi phi','bao gia'))) and 'FIN-RULES' in byid:
        if len(matched)>3:return 'Hãy chọn tối đa 3 gói để so sánh chi tiết. Tab Tài chính demo có toàn bộ 20 gói.',[],True
        m=re.search(r'\b(\d+)\s*(?:site|chi nhanh|dia diem)\b',n);sites=int(m.group(1)) if m else 1
        m=re.search(r'(?:chiet khau|giam gia)\s*(\d+)\s*%',n);discount=int(m.group(1)) if m else 0
        try:answers=[quote_answer(d,sites,discount) for d in matched]
        except ValueError as e:return str(e),[],True
        return '\n\n'.join(answers),matched+[byid['FIN-RULES']],True
    if any(has(q,t) for t in ('phan bo ngay','lich chi tiet','tung giai doan','tung cong doan','ngay cong chi tiet')):
        ids={d['fields']['service_id'] for d in matched};items=[d for d in docs if d['category']=='Lịch định mức' and d['fields']['service_id'] in ids]
        if items:return excerpt(items)
    return None
