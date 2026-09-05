"""Linked fictional financial ledger. All amounts are integer VND, never real tax guidance."""
from pathlib import Path
from datetime import date,timedelta
from collections import Counter
import json,sqlite3
from business import money,table
from company_data import build as company_build
ROOT=Path(__file__).parent
SNAPSHOT='2026-09-05'
TAX=10 # Explicit exercise parameter, NOT an applicable statutory VAT determination.

def workday(day,offset):
    step=1 if offset>=0 else -1
    for _ in range(abs(offset)):
        day+=timedelta(days=step)
        while day.weekday()>4:day+=timedelta(days=step)
    return day

def build():
    pack=company_build();base={d['id']:d for d in pack['documents']};docs=[]
    def add(id,title,kind,fields,body,customer=None,roles=None):
        d=dict(id=id,title=title,category=kind,fields=fields,body=body,customer=customer,roles=roles or ['sale','technical','admin'],version='finance-1.0',status='approved',valid_from='2026-01-01',valid_to='2027-12-31',owner='Kế toán và PM giả lập',synthetic=True,as_of=SNAPSHOT,finance=True)
        docs.append(d);return d
    add('FIN-RULES','Quy ước tài chính và phạm vi sổ demo','Chính sách tài chính',dict(snapshot=SNAPSHOT,tax_percent=TAX,currency='VND'),
        '## 1. Phạm vi\n- Tất cả giá, giá vốn, thuế, thanh toán, công nợ và SLA là giả lập; ảnh chụp ngày 05/09/2026.\n- VAT mô phỏng cố định 10% để minh họa phép tính; không xác định thuế suất pháp luật cho bất kỳ hàng hóa/dịch vụ nào.\n- Giá gói chuẩn cũ là phí dịch vụ chưa thuế. OFFER là phương án mở rộng gồm các dòng thiết bị/license riêng; không tự thay báo giá QUOTE đã có.\n\n## 2. Công thức\n- Thành tiền = số lượng × đơn giá; chiết khấu chỉ trên công dịch vụ trong công cụ demo.\n- Thuế mô phỏng = giá sau chiết khấu × 10%, làm tròn đến VND; tổng trả = trước thuế + thuế.\n- Công nợ = chứng từ yêu cầu thu đã phát hành trừ phiếu thu được phân bổ. Khoản chưa phát hành không tính là nợ quá hạn.\n- Tiền thu không đồng nghĩa doanh thu; báo giá được duyệt không đồng nghĩa đã nghiệm thu.\n\n## 3. Quyền và giới hạn\n- Sale/kỹ thuật xem hồ sơ khách được phân công. Giá vốn, lợi nhuận và chi phí quản lý chỉ admin.\n- Không tạo hóa đơn điện tử, gửi yêu cầu thu tiền, giữ kho hay thanh toán thật. Mọi chứng từ ở đây là mẫu minh họa.')
    components={'firewall':[('GATE-100',1),('LIC-GATE',1)],'wifi':[('AP-AX',5)],'backup':[('NAS-4',1),('HDD-8',2)],'waf':[('WAF-VM',1)],'switch':[('SW-24',3),('SFP-10',2)],'server':[('SRV-1',2)],'endpoint':[('EDR-50',1)],'pam':[('PAM-20',1)],'siem':[('SIEM-10',1)],'audit':[],'training':[],'migration':[('GATE-300',1),('LIC-GATE',1)]}
    annual={'LIC-GATE','WAF-VM','EDR-50','PAM-20','SIEM-10'}
    for s in pack['services']:
        lines=[dict(item=s['name'],quantity=1,unit_price=s['price'],amount=s['price'],type='service',source_id=s['source_id'])]
        for sku,quantity in components[s['id']]:
            d=base['SKU-'+sku];f=d['fields'];lines.append(dict(item=d['title'],quantity=quantity,unit_price=f['price'],amount=quantity*f['price'],type='license' if sku in annual else 'hardware',source_id=d['id']))
        support=0 if s['id'] in ('audit','training') else 3000000
        fields=dict(service_id=s['id'],aliases=s['aliases'],scope=s['scope'],lines=lines,service_fee=s['price'],effort=s['days'],delivery_min=s['delivery_min'],delivery_max=s['delivery_max'],support_monthly=support,license_annual=sum(x['amount'] for x in lines if x['type']=='license'),tax_percent=TAX,conditions=s['conditions'],status='Phương án trọn gói DEMO',source_ids=[x['source_id'] for x in lines]+(['SLA-BASIC'] if support else []),unit='gói chuẩn')
        subtotal=sum(x['amount'] for x in lines);fields.update(subtotal=subtotal,tax=subtotal//10,total=subtotal+subtotal//10,year1=subtotal+12*support,tco3=subtotal+36*support+2*fields['license_annual'])
        body='## 1. Cấu phần gói chuẩn DEMO\n'+table([['Hạng mục','SL','Đơn giá','Thành tiền']]+[[x['item'],x['quantity'],money(x['unit_price']),money(x['amount'])] for x in lines])+f'\n\n## 2. Tổng và thời gian\n- Trước thuế: {money(subtotal)}; VAT mô phỏng 10%: {money(fields["tax"])}; tổng: {money(fields["total"])}.\n- Công triển khai {s["days"]} ngày công; lịch mẫu {s["delivery_min"]}–{s["delivery_max"]} ngày làm việc sau đủ đầu vào.\n- Phạm vi: {s["scope"]}. Điều kiện: {s["conditions"]}.\n\n## 3. Duy trì\n- BASIC mẫu {money(support)}/tháng'+(' (không kèm bảo trì định kỳ cho gói này).' if not support else ' cho 1 site/tối đa 10 thiết bị; tính riêng phí gói mua ban đầu.')+f'\n- License gia hạn giả định giữ nguyên {money(fields["license_annual"])}/năm.\n- Tổng năm đầu trước thuế {money(fields["year1"])}; TCO 3 năm trước thuế {money(fields["tco3"])}.\n- TCO gồm mua ban đầu + 36 tháng hỗ trợ + 2 lần gia hạn license; không tính lạm phát, nâng cấp hoặc tăng quy mô.\n- Giá và SKU đều DEMO; thiết bị thật cần xác minh tương thích/sizing.'
        add('OFFER-'+s['id'].upper(),s['name']+' — trọn gói và TCO','Gói trọn bộ',fields,body)
        totaldays=s['days'];stages=[('Khảo sát và thiết kế',max(1,totaldays//4)),('Cấu hình / triển khai',max(0,totaldays-max(1,totaldays//4)-1)),('Kiểm thử và bàn giao',1)]
        fields=dict(service_id=s['id'],effort=totaldays,stages=[dict(name=n,days=v) for n,v in stages],waiting_equipment=7,waiting_approval=2,working_hours='08:30–17:30, nghỉ trưa 1 giờ; thứ Hai–thứ Sáu',buffer_days=2)
        add('SCHEDULE-'+s['id'].upper(),s['name']+' — phân bổ ngày công','Lịch định mức',fields,'## 1. Phân bổ DEMO\n'+table([['Công đoạn','Ngày công']]+[[n,v] for n,v in stages])+f'\n\n## 2. Điều kiện lịch\n- Tổng {totaldays} ngày công, 1 kỹ sư; giai đoạn 0 ngày gộp vào buổi kiểm/bàn giao của gói ngắn.\n- Đệm điều phối tối đa 2 ngày làm việc trong khung mẫu; không tính thành công tính phí.\n- Nếu phải mua hàng: giả định chờ 7 ngày làm việc; duyệt change 2 ngày làm việc. Các việc có thể chồng lịch, PM xác nhận trước cộng thời gian.\n- Chỉ tính thứ Hai–thứ Sáu trong mô phỏng, chưa xử lý lịch nghỉ lễ. Lịch nhiều dự án chưa có bộ máy cân bằng nhân sự.')
    security=[('MFA','Triển khai MFA',10000000,4,'50 người dùng, 2 ứng dụng SaaS, 1 tenant','mfa,xác thực đa yếu tố',5000000),('ZTNA','Pilot Zero Trust / ZTNA',28000000,10,'1 ứng dụng nội bộ, 30 người dùng, 1 IdP','zero trust,ztna',18000000),('VULN','Đánh giá lỗ hổng',12000000,4,'20 tài sản, quét được cấp quyền, 1 lần kiểm lại','lỗ hổng,vulnerability,quét',0),('PENTEST','Kiểm thử bảo mật web',30000000,10,'1 web, 10 luồng nghiệp vụ, 3 vai trò test, 1 retest','pentest,kiểm thử bảo mật',0),('SOC','Khởi tạo giám sát SOC',48000000,12,'10 nguồn log, 5 use case, không gồm license SIEM','soc,giám sát an ninh',0),('IR','Retainer ứng cứu sự cố',6000000,2,'Khởi tạo đầu mối và diễn tập bàn; tối đa 8 giờ công hỗ trợ/tháng','retainer,ứng cứu sự cố',0),('DLP','Pilot DLP bảo vệ dữ liệu',25000000,8,'50 endpoint, 3 nhóm dữ liệu, 1 tenant','dlp,chống thất thoát',20000000),('AWARENESS','Đào tạo nhận thức ATTT',6000000,2,'20 học viên, 2 buổi, bài kiểm tra và báo cáo','nhận thức,awareness,phishing',0)]
    for sid,name,fee,days,scope,aliases,licensefee in security:
        monthly=15000000 if sid=='SOC' else 18000000 if sid=='IR' else 0
        lines=[dict(item=name,quantity=1,unit_price=fee,amount=fee,type='service',source_id='OFFER-'+sid)]
        if licensefee:lines.append(dict(item='License lab DEMO 12 tháng',quantity=1,unit_price=licensefee,amount=licensefee,type='license',source_id='OFFER-'+sid))
        subtotal=fee+licensefee
        fields=dict(service_id=sid.lower(),aliases=aliases.split(','),scope=scope,lines=lines,service_fee=fee,effort=days,delivery_min=days,delivery_max=days+2,support_monthly=monthly,license_annual=licensefee,tax_percent=TAX,subtotal=subtotal,tax=subtotal//10,total=subtotal+subtotal//10,year1=subtotal+12*monthly,tco3=subtotal+36*monthly+2*licensefee,conditions='Có scope, quyền kiểm thử, đầu mối, dữ liệu lab và change được duyệt',source_ids=[],status='Phương án ATTT DEMO',unit='gói chuẩn')
        add('OFFER-'+sid,name+' — giá và phạm vi','Gói trọn bộ',fields,f'## 1. Gói ATTT DEMO\n- {scope}.\n- Công khởi tạo/dịch vụ {money(fee)}; license lab 12 tháng {money(licensefee)}.\n- Trước thuế {money(subtotal)}; VAT mô phỏng 10% {money(subtotal//10)}; tổng {money(fields["total"])}.\n\n## 2. Thời gian và duy trì\n- {days} ngày công; {days}–{days+2} ngày làm việc sau đủ đầu vào.\n- Phí duy trì riêng {money(monthly)}/tháng; chỉ SOC/IR có phí định kỳ trong bảng này.\n- SOC mẫu nhận cảnh báo 8x5, phản hồi ban đầu P1 1 giờ phục vụ; không phải SOC24/7. IR mẫu tiếp nhận P1 24x7 trong 1 giờ, vượt 8 giờ công/tháng tính 1.500.000 VND/giờ sau duyệt.\n- Các điều khoản SOC/IR chỉ áp dụng đúng gói tương ứng; không áp SLA bảo trì thiết bị sang pentest/đào tạo.\n\n## 3. Bàn giao và ngoại lệ\n- Hồ sơ phạm vi, báo cáo kiểm thử/pilot và danh sách việc tiếp theo.\n- Không bảo đảm tìm mọi lỗi; không có lệnh khai thác, không kiểm hệ thống ngoài scope. Giá không phải báo giá hãng thật.')
    for idx,p in enumerate(pack['packages']):
        fields=dict(package=p['id'],monthly=p['monthly'],response_p1=p['p1'],response_p2=p['p2'],response_p3=p['p3'],response_p4=['3 ngày làm việc','2 ngày làm việc','1 ngày làm việc'][idx],recovery_target=['24 giờ phục vụ','8 giờ','4 giờ'][idx],update_minutes=[120,60,30][idx],onsite_target=['8 giờ phục vụ','4 giờ','2 giờ'][idx],credit_per_breach_percent=2,credit_cap_percent=10,maintenance_minutes=[120,120,180][idx],report_days=2)
        add('SLA-DETAIL-'+p['id'],'Phụ lục SLA '+p['id']+' — mốc giờ và bồi hoàn','SLA chi tiết',fields,f'## 1. SLA phản hồi DEMO\n- Gói {p["id"]}: {money(p["monthly"])}/tháng/site trước thuế; {p["hours"]}; tối đa 10 thiết bị/site.\n- Phản hồi ban đầu: P1 {p["p1"]}; P2 {p["p2"]}; P3 {p["p3"]}; P4 {fields["response_p4"]}.\n- Cập nhật P1 mỗi {fields["update_minutes"]} phút trong giờ phục vụ.\n\n## 2. Mục tiêu xử lý có điều kiện\n- Mục tiêu khôi phục P1 {fields["recovery_target"]} sau đủ quyền, cấu hình và người phối hợp; không phải bảo đảm xử lý xong mọi sự cố.\n- Mục tiêu có mặt onsite nội thành {fields["onsite_target"]} sau duyệt điều phối; quota onsite theo SLA-{p["id"]}.\n- Bảo trì {p["maintenance"]}, cửa sổ mẫu {fields["maintenance_minutes"]} phút/lần; báo cáo sau 2 ngày làm việc.\n\n## 3. Đo SLA và tín dụng dịch vụ\n- Bắt đầu khi kênh tiếp nhận ghi ticket đủ thông tin; phút ngoài giờ BASIC không tính vào giờ phục vụ.\n- Chờ thông tin có ghi nhận chỉ tạm dừng đồng hồ mục tiêu khôi phục, không xóa vi phạm phản hồi đã xảy ra.\n- Vi phạm phản hồi P1 được xác nhận: tín dụng dịch vụ 2% phí tháng/site/lần, tối đa 10% phí tháng/site; không tính trên toàn giá trị hợp đồng.\n- Ví dụ 1 vi phạm tại 1 site: {money(p["monthly"]*2//100)}, trần tháng {money(p["monthly"]//10)}. Yêu cầu đối soát trong 5 ngày làm việc, xác nhận trong 5 ngày tiếp theo; chỉ bù kỳ sau khi đã duyệt.\n- Mọi mức trên là phụ lục DEMO, không sửa nghĩa vụ hợp đồng thật.')
    invoices=[];receipts=[];costs=[]
    for i,c in enumerate(pack['clients']):
        cid=c['id']
        for j in range(2):
            qid=f'QUOTE-{cid}-{j+1:02}';q=base[qid]['fields'];project=base[q['project_id']]['fields'];net=q['subtotal'];tax=net//10;gross=net+tax
            amounts=[gross*40//100,gross*40//100,gross-(gross*40//100)*2]
            issued=[date(2026,9,1),date.fromisoformat(project['end']),workday(date.fromisoformat(project['end']),1)] if j==0 else [workday(date.fromisoformat(project['start']),-5),date.fromisoformat(project['end']),workday(date.fromisoformat(project['end']),1)]
            milestones=[]
            for k,(label,amount,when) in enumerate(zip(['Tạm ứng 40%','Hoàn tất triển khai 40%','Sau nghiệm thu 20%'],amounts,issued)):
                due=workday(when,3 if k==0 else 7);iid=f'INV-{cid}-{j+1:02}-{k+1}'
                milestones.append(dict(name=label,amount=amount,planned_issue=when.isoformat(),due=due.isoformat(),invoice_id=iid if when.isoformat()<=SNAPSHOT else None))
                if when.isoformat()>SNAPSHOT:continue
                paid=amount if (i+k+j)%3==0 else amount//2 if (i+k+j)%3==1 else 0
                fields=dict(customer_id=cid,quote_id=qid,project_id=q['project_id'],milestone=label,amount=amount,paid=paid,outstanding=amount-paid,issued=when.isoformat(),due=due.isoformat(),status='Đã thu đủ' if paid==amount else 'Thu một phần' if paid else 'Chưa thu',overdue_days=max(0,(date.fromisoformat(SNAPSHOT)-due).days) if paid<amount else 0)
                invoices.append(dict(id=iid,**fields))
                add(iid,f'{c["name"]} — {label} / {qid}','Chứng từ thu',fields,f'## 1. Chứng từ yêu cầu thu DEMO {iid}\n- Khách {c["name"]}; báo giá {qid}; dự án {q["project_id"]}.\n- Mốc {label}; phát hành {when}; hạn {due}; tổng gồm thuế mô phỏng {money(amount)}.\n\n## 2. Đối soát đến {SNAPSHOT}\n- Đã thu {money(paid)}; còn phải thu {money(amount-paid)}; trạng thái {fields["status"]}.\n- Quá hạn {fields["overdue_days"]} ngày lịch nếu còn dư nợ.\n- Chỉ là chứng từ minh họa, không phải hóa đơn thuế hoặc yêu cầu thanh toán thật.',cid)
                if paid:
                    rid='PAY-'+iid[4:];paid_on=min(workday(due,-1),date.fromisoformat(SNAPSHOT))
                    pf=dict(customer_id=cid,invoice_id=iid,quote_id=qid,amount=paid,paid_on=paid_on.isoformat(),method='Chuyển khoản giả lập',status='Đã đối soát mẫu')
                    receipts.append(dict(id=rid,**pf));add(rid,f'Phiếu thu {c["name"]} / {iid}','Phiếu thu',pf,f'## Phiếu thu DEMO {rid}\n- Ngày {paid_on}; số tiền {money(paid)}; phân bổ duy nhất cho {iid}.\n- Khách {c["name"]}; báo giá {qid}; hình thức chuyển khoản giả lập.\n- Không chứa tài khoản ngân hàng thật, không thực hiện giao dịch.',cid)
            fields=dict(customer_id=cid,quote_id=qid,project_id=q['project_id'],service_id=q['service_id'],sites=q['sites'],subtotal=net,discount=0,tax_percent=TAX,tax=tax,total=gross,effort=project['effort'],start=project['start'],end=project['end'],milestones=milestones,status='Chi tiết kịch bản đã duyệt',scope='Phí dịch vụ; không thiết bị hoặc license')
            add('FIN-'+qid,f'{c["name"]} — chi tiết tiền và lịch {qid}','Tài chính báo giá',fields,'## 1. Giá dịch vụ DEMO\n'+table([['Trước thuế','Chiết khấu','VAT mô phỏng 10%','Tổng thanh toán'],[money(net),'0%',money(tax),money(gross)]])+f'\n\n## 2. Lịch và công\n- Dự án {q["project_id"]}: {project["start"]} → {project["end"]}; {project["effort"]} ngày công; {q["sites"]} site.\n- Không gồm thiết bị/license. Đây là diễn giải tài chính của {qid}, không cộng gói OFFER vào báo giá này.\n\n## 3. Tiến độ thu\n'+table([['Đợt','Số tiền','Hạn dự kiến','Chứng từ']]+[[m['name'],money(m['amount']),m['due'],m['invoice_id'] or 'Chưa phát hành tại snapshot'] for m in milestones]),cid)
            cost=project['effort']*1200000;travel=q['sites']*500000;presales=net*5//100;totalcost=cost+travel+presales
            cf=dict(customer_id=cid,quote_id=qid,project_id=q['project_id'],service_revenue=net,labor=cost,travel=travel,presales=presales,total_cost=totalcost,gross_profit=net-totalcost,margin_percent=round((net-totalcost)*100/net,2),recognition='Đã nghiệm thu' if j else 'Dự kiến, chưa ghi nhận',status='Dự toán nội bộ DEMO')
            costs.append(cf);add('COST-'+cid+f'-{j+1:02}',f'{c["name"]} — giá vốn và lãi gộp','Giá vốn nội bộ',cf,f'## Giá vốn nội bộ DEMO / {qid}\n- Giá dịch vụ trước thuế {money(net)}.\n- Công nội bộ {project["effort"]} × 1.200.000 VND = {money(cost)}; đi lại {money(travel)}; presales 5% = {money(presales)}.\n- Tổng giá vốn {money(totalcost)}; lãi gộp {money(net-totalcost)}; biên {cf["margin_percent"]}%.\n- Trạng thái {cf["recognition"]}; chưa trừ chi phí quản lý, thuế thu nhập hoặc dự phòng. Định mức giả lập, không phải lương thật.',cid,['admin'])
        rows=[x for x in invoices if x['customer_id']==cid];billed=sum(x['amount'] for x in rows);paid=sum(x['paid'] for x in rows);overdue=sum(x['outstanding'] for x in rows if x['overdue_days']>0)
        f=dict(customer_id=cid,billed=billed,paid=paid,outstanding=billed-paid,overdue=overdue,invoice_ids=[x['id'] for x in rows],snapshot=SNAPSHOT,status='Đối soát snapshot')
        add('AR-'+cid,f'{c["name"]} — tổng hợp công nợ','Công nợ',f,'## Công nợ DEMO đến '+SNAPSHOT+'\n'+table([['Đã phát hành','Đã thu','Còn phải thu','Trong đó quá hạn'],[money(billed),money(paid),money(billed-paid),money(overdue)]])+'\n\n'+table([['Chứng từ','Hạn','Còn nợ','Ngày quá hạn']]+[[x['id'],x['due'],money(x['outstanding']),x['overdue_days']] for x in rows])+'\n\n- Không gồm các đợt chưa phát hành, không gộp phí bảo trì định kỳ chưa có chứng từ trong bộ sổ này.',cid)
    recognized=[c for c in costs if c['recognition']=='Đã nghiệm thu'];revenue=sum(c['service_revenue'] for c in recognized);cogs=sum(c['total_cost'] for c in recognized);opex=35000000
    f=dict(revenue=revenue,cogs=cogs,gross_profit=revenue-cogs,opex=opex,operating_result=revenue-cogs-opex,period='Danh mục dự án đã nghiệm thu trong snapshot, không phải toàn công ty',status='Báo cáo quản trị DEMO',source_ids=['COST-'+c['customer_id']+'-02' for c in recognized])
    add('FIN-PNL','Kết quả danh mục dự án đã nghiệm thu','Báo cáo quản trị',f,'## Báo cáo quản trị DEMO\n'+table([['Chỉ tiêu','VND'],['Doanh thu dịch vụ đã nghiệm thu',money(revenue)],['Giá vốn',money(cogs)],['Lãi gộp',money(revenue-cogs)],['Chi phí quản lý phân bổ giả lập',money(opex)],['Kết quả trước thuế mô phỏng',money(revenue-cogs-opex)]])+'\n\n- Chỉ gồm 10 dự án đã nghiệm thu trong bộ dữ liệu, không phải BCTC công ty.\n- Không gồm doanh thu chưa nghiệm thu, VAT mô phỏng, phí bảo trì hoặc bán phần cứng; không suy ra số dư tiền mặt từ bảng này.',roles=['admin'])
    for d in docs:
        f=d['fields'];requires=list(f.get('source_ids',[]))
        if d['category']=='Công nợ':requires+=f['invoice_ids']
        if d['category'] in ('Tài chính báo giá','Chứng từ thu','Giá vốn nội bộ'):requires += [f['quote_id'],f['project_id']]
        if d['category']=='Phiếu thu':requires.append(f['invoice_id'])
        if d['category']=='Lịch định mức':requires.append('RATE-'+f['service_id'].upper())
        if d['category']=='SLA chi tiết':requires.append('SLA-'+f['package'])
        d['requires']=list(dict.fromkeys(id for id in requires if id!=d['id']))
    return docs

def install():
    docs=build();data=ROOT/'data';export=data/'finance_documents';export.mkdir(exist_ok=True)
    with sqlite3.connect(data/'demo.sqlite3') as db:
        for d in docs:
            old=db.execute('SELECT payload FROM docs WHERE id=?',(d['id'],)).fetchone()
            if old:
                old=json.loads(old[0])
                if old.get('version')!='finance-1.0':continue
                d['status']=old['status']
            db.execute('INSERT OR REPLACE INTO docs VALUES(?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
            (export/(d['id']+'.md')).write_text('# '+d['title']+'\n\n'+d['body'],encoding='utf8')
    (data/'finance_documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')
    report=dict(documents=len(docs),snapshot=SNAPSHOT,categories=dict(Counter(d['category'] for d in docs)),synthetic=True,tax_note='10% là tham số mô phỏng, không phải thuế suất áp dụng thực tế')
    (data/'finance_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':install()
