"""Deterministic business facts from the same approved, ACL-filtered documents as RAG."""
import re, unicodedata

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.lower().replace('đ','d')) if unicodedata.category(c)!='Mn')

def has(q,term):return bool(re.search(r'(?<!\w)'+re.escape(norm(term))+r'(?!\w)',norm(q)))
def money(n):return f'{n:,.0f}'.replace(',','.')+' VND'
def table(rows):
    def line(row):return '| '+' | '.join(str(x).replace('|','/').replace('\n',' ') for x in row)+' |'
    return '\n'.join([line(rows[0]),line(['---']*len(rows[0]))]+[line(r) for r in rows[1:]])

def service_matches(q,docs):
    matched=[d for d in docs if d.get('service') and any(has(q,a) for a in d['service']['aliases']+[d['service']['id']])]
    # WAF's full name contains the word firewall; migration has its own package.
    if has(q,'web application firewall') and not has(q,'firewall mạng'):matched=[d for d in matched if d['service']['id']!='firewall']
    if any(d['service']['id']=='migration' for d in matched):matched=[d for d in matched if d['service']['id']!='firewall']
    return matched

def context_query(q,previous):
    n=norm(q)
    explicit=any(has(n,t) for t in ('firewall','waf','wifi','wi-fi','backup','vpn','switch','server','endpoint','pam','siem','migration','basic','plus','premium','bao hanh','bao tri')) or bool(re.search(r'\b(?:crm|quote|contract|project|ticket|sku)-',n))
    if explicit:return q
    follow=any(has(n,t) for t in ('hai cai','2 cai','hai loai','2 loai','hai goi','2 goi','cai do','goi do','dich vu nay','no','o tren','vua roi','lap bang','tao bang','con gia','con thoi gian','bao lau','gia bao nhieu','duyet'))
    if previous and follow and len(q)<250:
        # Bounded topic text, never previous generated answers or another session.
        return q+'\nChủ đề trước: '+previous.split('\nChủ đề trước: ')[-1][:450]
    return q

def respond(q,docs):
    """Returns (answer, source documents, needs_review) or None for the local LLM."""
    n=norm(q);byid={d['id']:d for d in docs};matched=service_matches(q,docs)
    direct=[d for d in docs if has(q,d['id'])]
    def excerpts(items,lead='Thông tin DEMO từ hồ sơ đang được phép xem:'):
        sections=[]
        for i,d in enumerate(items):
            if d['body'].startswith('## '):sections.append(d['body']+'\n\n['+d['id']+']');continue
            parts=re.split(r'(?<=[.!?])\s+(?=[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỹ])',d['body'])
            sections.append(f'## {i+1}. {d["title"]}\n'+'\n'.join('- '+p for p in parts)+'\n\n['+d['id']+']')
        return lead+'\n\n'+'\n\n'.join(sections),items,True
    if direct:return excerpts(direct[:4],'Thông tin từ tài liệu tham khảo và bài tập biên soạn:' if any(d.get('knowledge_type') for d in direct) else 'Thông tin DEMO từ hồ sơ đang được phép xem:')
    # An actual approval requires a workflow, never a chat keyword.
    if any(has(n,t) for t in ('duyet','cam ket','chot gia','chot lich','gui bao gia')) and not any(has(n,t) for t in ('quy trinh','ai duyet','can ai','cap duyet','chinh sach')):
        items=matched[:2]+[byid[k] for k in ('BIZ-DISCOUNT','BIZ-CHANGE') if k in byid]
        return excerpts(items,'Chưa có thao tác phê duyệt hay gửi báo giá nào được thực hiện. Đây là đề xuất DEMO; quản lý kinh doanh duyệt giá, PM xác nhận lịch. Dữ liệu để đối chiếu:')
    # Select customer records by known name or explicit customer letter, already filtered by ACL.
    customers=[d for d in docs if d['id'].startswith('CRM-') and (has(n,d['fields']['name']) or has(n,' '.join(d['fields']['name'].split()[:2])) or has(n,'khach '+d['customer']) or has(n,'khach hang '+d['customer']))]
    if customers:
        kinds=[]
        for words,kind in [(('hop dong','sla','bao tri','ho tro','p1'),'Hợp đồng'),(('du an','tien do','lich','thi cong'),'Dự án'),(('bao gia','chi phi','gia'),'Báo giá'),(('ticket','su co'),'Ticket')]:
            if any(has(n,w) for w in words):kinds.append(kind)
        if not kinds:kinds=['Khách hàng','Hợp đồng']
        items=[d for d in docs if d.get('customer') in {c['customer'] for c in customers} and d['category'] in kinds]
        if matched:items=[d for d in items if not d.get('fields',{}).get('service_id') or d['fields']['service_id'] in {x['service']['id'] for x in matched}]
        if items:return excerpts(items[:4])
        return 'Không có hồ sơ loại này trong phạm vi được cấp. Hãy chọn hồ sơ khả dụng ở tab Hồ sơ công ty.',[],True
    # Tables are copied from curated source rows, not generated numeric facts.
    comparisons=[('CMP-FW-WAF',has(n,'firewall') and has(n,'waf')),('CMP-BACKUP-HA',has(n,'backup') and has(n,'ha')),('CMP-WARRANTY-MAINT',has(n,'bao hanh') and has(n,'bao tri'))]
    if any(has(n,t) for t in ('so sanh','khac nhau','phan biet','lap bang','tao bang')):
        for id,match in comparisons:
            if match and id in byid:
                d=byid[id];return d['title']+' — dữ liệu DEMO:\n\n'+table(d['table'])+'\n\n['+id+']',[d],True
    packages=[d for d in docs if d.get('package_data')]
    if any(has(n,t) for t in ('sla','goi bao tri','goi ho tro','basic','plus','premium','p1','p2','p3')):
        selected=[d for d in packages if has(n,d['package'])] or packages
        if selected:
            rows=[['Gói DEMO','Phí/tháng','Giờ hỗ trợ','Phản hồi P1','P2','P3','Bảo trì']]
            for d in selected:
                s=d['package_data'];rows.append([s['id'],money(s['monthly']),s['hours'],s['p1'],s['p2'],s['p3'],s['maintenance']])
            answer=table(rows)+'\n\nGiá cho 1 site / tối đa 10 thiết bị, chưa VAT, phần cứng, license và công ngoài scope. SLA là thời gian phản hồi, không phải khôi phục xong. '
            if any(has(n,t) for t in ('onsite','may muon','thiet bi muon')):answer+='\n'+'\n'.join(f"{d['package']}: onsite {d['package_data']['onsite']}; máy mượn {d['package_data']['loan']}." for d in selected)
            return answer+'\n'+' '.join('['+d['id']+']' for d in selected),selected,True
    if any(has(n,t) for t in ('ton kho','kho hang','con hang','sku','gia thiet bi','gia phan cung')):
        stock=[d for d in docs if d['category']=='Kho hàng' and (not matched or d['fields']['service_id'] in {x['service']['id'] for x in matched})]
        if stock:
            rows=[['Mã','Tên hàng DEMO','Đơn giá chưa VAT','Tồn','Giữ','Khả dụng']]
            for d in stock:
                f=d['fields'];rows.append([f['sku'],d['title'],money(f['price']),f['on_hand'],f['reserved'],f['available']])
            return table(rows)+'\n\nẢnh chụp kho giả lập ngày 05/09/2026; chưa đặt giữ hàng. '+' '.join('['+d['id']+']' for d in stock),stock,True
    # Match specific policy questions before generic price words.
    policies=[(('chiet khau',),'DISCOUNT'),(('thanh toan','tam ung','dat coc'),'PAYMENT'),(('bao hanh',),'WARRANTY'),(('rma','may muon'),'RMA'),(('cho thue','thue thiet bi'),'RENTAL'),(('gia han','eol','eos'),'LICENSE'),(('phat sinh','them tunnel','them 1 tunnel'),'CHANGE'),(('nghiem thu','ho so ban giao'),'ACCEPTANCE'),(('bao tri dinh ky','quy trinh bao tri'),'MAINTENANCE')]
    for terms,key in policies:
        if any(has(n,t) for t in terms) and 'BIZ-'+key in byid:return excerpts([byid['BIZ-'+key]])
    if any(has(n,t) for t in ('gia','bao gia','chi phi','bao nhieu tien','mat bao nhieu','bao lau','may ngay','bao nhieu ngay','so ngay','thoi gian trien khai')):
        # Vendor-specific prices need actual approved SKUs, not fictional device substitutions.
        if any(has(n,t) for t in ('cloudflare','fortigate 60','fortigate 100','fortigate 200','fortiweb 100')):return None
        if not matched and any(has(n,t) for t in ('bang gia','bao gia bao nhieu','danh muc dich vu')):matched=[d for d in docs if d.get('service')]
        if matched:
            quantity=re.search(r'\b(\d+)\s*(?:site|chi nhanh|dia diem)\b',n);sites=int(quantity.group(1)) if quantity else 1
            if not 1<=sites<=5:return 'Dự toán tự động DEMO áp dụng 1–5 site. Quy mô này cần PM lập phương án nguồn lực riêng.',matched,True
            rows=[['Dịch vụ DEMO','Phí công / '+str(sites)+' site','Ngày công','Lịch mẫu 1 site']]
            details=[]
            for d in matched:
                s=d['service'];rows.append([s['name'],money(s['price']*sites),s['days']*sites,f"{s['delivery_min']}–{s['delivery_max']} ngày làm việc"])
                if len(matched)<=3:details.append(f"{s['name']}: {s['scope']}. Điều kiện: {s['conditions']}. [{d['id']}]")
            answer='## 1. Giá và thời gian tham khảo\n\n'+table(rows)+'\n\n## 2. Phạm vi áp dụng\n\n'+'\n\n'.join('- '+x for x in details)+'\n\n## 3. Điều kiện cần nhớ\n- Giá tham khảo giả lập, chưa VAT, thiết bị và license.\n- Ngày công khác ngày lịch; nhiều site cần PM xếp lịch.\n- Khung trên chưa gồm thời gian chờ thiết bị, quyền truy cập và duyệt change.'
            if any(has(n,t) for t in ('ha','chua co thiet bi','phuc tap')):answer+=' Nhu cầu có ngoại lệ: số trên chỉ là gói chuẩn để so sánh; chưa phải dự toán áp dụng cho cấu hình riêng này.'
            return answer+'\n'+' '.join('['+d['id']+']' for d in matched),matched,True
    return None
