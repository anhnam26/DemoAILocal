"""Idempotent corpus revision; writes JSON only, never opens SQLite."""
import json,re
from pathlib import Path
import sync_knowledge
ROOT=Path(__file__).resolve().parent
DATE='2026-09-30'
def ref(title,url):return dict(title=title,url=url,checked_at=DATE)
RFC1122=ref('RFC 1122 — Internet layers','https://www.rfc-editor.org/rfc/rfc1122')
RFC9293=ref('RFC 9293 — TCP','https://www.rfc-editor.org/rfc/rfc9293')
RFC1034=ref('RFC 1034 — DNS concepts','https://www.rfc-editor.org/rfc/rfc1034')
ARTICLES=[
 ('KB-NET-LAYERS','Mô hình OSI và TCP/IP: phân lớp và ánh xạ','A',['OSI','TCP/IP','phân lớp'],[RFC1122,ref('IBM — OSI model','https://www.ibm.com/think/topics/osi-model')],'''OSI là mô hình tham chiếu khái niệm gồm 7 tầng, dùng mô tả chức năng truyền thông, thiết kế và khoanh vùng sự cố; không phải một giao thức truyền dữ liệu.
Từ dưới lên: 1 Physical (Vật lý): tín hiệu và môi trường truyền; 2 Data Link (Liên kết dữ liệu): frame và liên kết cục bộ; 3 Network (Mạng): địa chỉ logic và định tuyến; 4 Transport (Giao vận): truyền dữ liệu đầu cuối; 5 Session (Phiên): quản lý hội thoại; 6 Presentation (Trình bày): biểu diễn/chuyển đổi dữ liệu; 7 Application (Ứng dụng): dịch vụ giao tiếp cho ứng dụng.
TCP/IP là bộ giao thức Internet và kiến trúc thường mô tả bằng 4 lớp: Link, Internet, Transport, Application. RFC 1122 mô tả link, IP và transport; RFC 1123 xử lý application. Cách dạy 5 lớp tách Physical khỏi Data Link; phải nói rõ quy ước đang dùng.
Ánh xạ gần đúng: OSI 1–2 vào Link; OSI 3 vào Internet; OSI 4 vào Transport; OSI 5–7 vào Application. Đây là ánh xạ chức năng, không phải mọi giao thức đều khớp tuyệt đối một tầng.
Ví dụ IP thuộc Internet; TCP và UDP thuộc Transport; DNS thuộc Application. TCP/IP không có lớp Session và Presentation riêng, nhưng các chức năng tương ứng vẫn có thể được ứng dụng/thư viện thực hiện.
OSI hữu ích để học, mô tả và chia bước kiểm tra; TCP/IP sát bộ giao thức triển khai trên Internet. Không nên kết luận OSI chỉ có lý thuyết vô dụng hoặc TCP/IP không có kiến trúc.'''),
 ('ND-A9A43D59581C2EE5D4C3','TCP — Transmission Control Protocol','A',['TCP','bắt tay ba bước','byte stream'],[RFC9293],'''TCP (Transmission Control Protocol) là giao thức tầng Transport cung cấp luồng byte tin cậy, có thứ tự giữa hai đầu cuối. TCP không giữ ranh giới thông điệp của ứng dụng.
Sequence number đánh số byte, acknowledgment xác nhận, phát hiện mất dữ liệu và truyền lại. Bắt tay thông thường SYN → SYN-ACK → ACK thiết lập kết nối; đóng kết nối dùng FIN/ACK hoặc kết thúc bằng RST tùy tình huống.
Flow control giới hạn lượng gửi theo khả năng nhận; congestion control điều tiết theo tình trạng mạng. Đây là hai mục tiêu khác nhau.
TCP không tự mã hóa và không bảo đảm thời gian giao nhận cố định; khi kết nối hỏng ứng dụng vẫn phải xử lý lỗi. ACK của TCP không chứng minh ứng dụng đã hoàn tất nghiệp vụ.
Port nhận diện đầu cuối dịch vụ; IP kết hợp port và giao thức giúp phân biệt luồng. Cấu hình NAT/VIP là chủ đề riêng, không phải định nghĩa hoặc cơ chế TCP.'''),
 ('KB-NET-DNS','DNS: phân giải tên, resolver, authoritative và TTL','A',['DNS','Domain Name System','tên miền','phân giải tên'],[RFC1034],'''DNS là hệ thống phân cấp, phân tán lưu các bản ghi theo tên miền. Phân giải tên thành địa chỉ là một chức năng; DNS không chỉ chứa địa chỉ IP.
Authoritative server trả dữ liệu có thẩm quyền cho zone mà nó phục vụ. Recursive resolver tìm câu trả lời thay cho client, có thể hỏi các máy chủ khác và lưu cache; hai vai trò không đồng nhất.
A chứa địa chỉ IPv4, AAAA chứa IPv6, CNAME là bí danh, MX chỉ mail exchanger, NS chỉ máy chủ tên. Không mặc định một tên chỉ có một địa chỉ.
TTL là thời gian bản ghi được phép giữ trong cache theo dữ liệu nhận được; thay bản ghi ở authoritative không tức thời xóa cache ở mọi client/resolver. Cần kiểm tra đúng resolver và thời gian TTL còn lại.
DNS thành công không chứng minh dịch vụ đích, route, firewall hoặc TLS hoạt động. Không đổi DNS nội bộ sang DNS công cộng tùy tiện khi có zone riêng.'''),
]


ARTICLES.extend([
 ('KB-NET-DNS-TROUBLE','Chẩn đoán: truy cập IP được nhưng tên miền không được','B',['DNS','tên miền','truy cập IP','phân giải sai','DNS cache'],[RFC1034],'''Phạm vi: quy trình chẩn đoán tổng quát, không phải lệnh cấu hình cho một hệ điều hành cụ thể. Truy cập bằng IP được nhưng tên miền lỗi là dấu hiệu cần kiểm DNS; chưa đủ để kết luận chắc chắn lỗi DNS.
1. Thu tên đầy đủ, lỗi cụ thể, thời điểm, máy bị ảnh hưởng, resolver đang dùng và địa chỉ mong đợi; không thu mật khẩu.
2. Kiểm tra câu trả lời DNS từ resolver cấu hình: đúng A/AAAA/CNAME hay NXDOMAIN, timeout, SERVFAIL. So sánh với authoritative hoặc resolver nội bộ được phép; không gửi tên nội bộ ra dịch vụ ngoài.
3. Nếu địa chỉ cũ, kiểm TTL/cache ở client và resolver, bản ghi và zone/split DNS. Nếu timeout, kiểm đường tới resolver và policy liên quan. Không xóa/đổi cấu hình trước khi lưu bằng chứng.
4. Nếu phân giải đúng nhưng ứng dụng lỗi, kiểm port dịch vụ, route, proxy, TLS/chứng thư và virtual host. Truy cập IP trực tiếp có thể khác tên miền vì Host header hoặc TLS SNI.
5. Sau thay đổi được duyệt, thử lại đúng tên từ các client liên quan, ghi trước/sau; khôi phục cấu hình resolver/bản ghi cũ nếu thay đổi làm lỗi nặng hơn. Cần biết nền tảng trước khi đưa lệnh cụ thể.'''),
 ('KB-NET-UDP','UDP: datagram và khác biệt với TCP','A',['UDP','User Datagram Protocol'],[ref('RFC 768 — UDP','https://www.rfc-editor.org/rfc/rfc768.txt'),RFC9293],'''UDP cung cấp dịch vụ datagram trên IP với cơ chế giao thức tối giản. UDP giữ đơn vị thông điệp, không tự thiết lập kết nối kiểu bắt tay TCP.
UDP không bảo đảm giao nhận, thứ tự hay chống lặp; ứng dụng cần tự xử lý hoặc dùng giao thức phía trên nếu cần các tính chất đó. Không suy ra mọi ứng dụng dùng UDP đều không tin cậy: chúng có thể bổ sung cơ chế riêng.
TCP cung cấp luồng byte có thứ tự và truyền lại; UDP cung cấp datagram không có bảo đảm tương đương. Lựa chọn tùy yêu cầu độ trễ, mất gói, điều khiển tắc nghẽn và thiết kế ứng dụng; không khẳng định UDP luôn nhanh hơn.
Cả TCP và UDP dùng port và thuộc tầng Transport trong kiến trúc Internet; bản thân chúng không cung cấp mã hóa dữ liệu.'''),
 ('KB-NET-DHCP','DHCP IPv4: cấp địa chỉ, lease và relay','A',['DHCP','DHCP relay','lease','DORA'],[ref('RFC 2131 — DHCP','https://www.rfc-editor.org/rfc/rfc2131.txt')],'''DHCP cấp địa chỉ và thông tin cấu hình mạng cho host. Bài này nói về DHCP IPv4; không áp dụng máy móc quy trình này cho DHCPv6.
Luồng cấp mới thường là DHCPDISCOVER → DHCPOFFER → DHCPREQUEST → DHCPACK. Đây không phải chuỗi bắt buộc cho mọi trạng thái: gia hạn và dùng lại địa chỉ có quy trình khác.
Lease giới hạn thời gian sử dụng địa chỉ; client cần gia hạn. DHCP server quản lý pool và ràng buộc cấp phát; cần loại trừ địa chỉ tĩnh và tránh pool chồng lấn.
Relay chuyển tiếp thông điệp khi client và server khác subnet; không cần đặt một DHCP server trên mọi VLAN. Cấu hình phải biết subnet, đường đi, server và relay cụ thể.
Khi không nhận được IP, kiểm link/VLAN, pool còn địa chỉ, server, relay và policy theo luồng thực tế; cần log trước khi kết luận. Nhận được IP chưa chứng minh DNS, gateway hoặc Internet hoạt động.''')])

ARTICLES.append(('KB-NET-VLAN','VLAN: miền quảng bá, phân đoạn và các bước triển khai chung','A',
 ['VLAN','virtual LAN','phân đoạn mạng','access','trunk'],
 [ref('RFC 5517 — Introduction: VLAN broadcast domains (informational)','https://www.rfc-editor.org/rfc/rfc5517.txt')],'''VLAN (Virtual LAN) phân chia mạng Ethernet thành các miền quảng bá logic ở Layer 2. Các host cùng VLAN có thể liên lạc Layer 2 khi đường chuyển tiếp cho phép; khác VLAN cần chức năng Layer 3 để liên lạc IP. VLAN không phải mã hóa và không thay thế firewall hoặc chính sách kiểm soát truy cập.
VLAN và IP subnet là hai khái niệm khác nhau: VLAN thuộc Layer 2, subnet thuộc Layer 3. Thiết kế thông thường ánh xạ mỗi VLAN với một subnet riêng; không suy ra VLAN tự cấp địa chỉ, tự định tuyến hoặc tự bảo vệ mọi luồng.
Bước 1 — Thu thập sơ đồ, mục tiêu phân đoạn, danh sách cổng/thiết bị, VLAN ID, subnet/gateway và luồng được phép. Xác nhận hãng, model, firmware và quyền thay đổi trước khi viết lệnh; sao lưu cấu hình và chuẩn bị đường quản trị dự phòng.
Bước 2 — Lập bảng VLAN và cổng. Cổng access thường phục vụ thiết bị đầu cuối trong một VLAN; đường trunk thường mang nhiều VLAN bằng gắn thẻ 802.1Q. Hành vi native/untagged/PVID và loại cổng phụ thuộc thiết bị; phải đối chiếu hai đầu, không sao chép mặc định giữa các hãng.
Bước 3 — Tạo VLAN, gán cổng theo kế hoạch và chỉ cho các VLAN cần thiết đi qua uplink. Nếu cần liên lạc giữa VLAN, cấu hình gateway/định tuyến và policy được duyệt; nếu cần DHCP, xác định server, pool và relay theo subnet. Không tự mở toàn bộ inter-VLAN traffic.
Bước 4 — Kiểm tra VLAN membership, đường uplink, IP/mask/gateway, DHCP và DNS; thử cả luồng cần cho phép lẫn luồng phải chặn. Ping thành công không chứng minh toàn bộ policy đúng.
Bước 5 — Ghi nhận kết quả, lưu cấu hình theo quy trình và theo dõi. Nếu mất quản trị hoặc phân đoạn sai, dùng đường dự phòng và khôi phục cấu hình/cổng theo bản sao đã kiểm tra; không tiếp tục đổi hàng loạt khi chưa có rollback.
Đây là bước chung, không có lệnh theo hãng. Cần bổ sung model switch/router/firewall, firmware, sơ đồ và VLAN/subnet mong muốn để đưa hướng dẫn cụ thể. Không cần FortiNAC hoặc Wi-Fi cho định nghĩa VLAN cơ bản. RFC 5517 là tài liệu informational về private VLAN; chỉ dùng phần mở đầu cho khái niệm miền quảng bá, không coi private VLAN là hành vi mặc định của mọi VLAN.'''))

def main():
    path=ROOT/'knowledge/documents.json';docs=json.loads(path.read_text(encoding='utf8'));by_id={d['id']:d for d in docs};changes=[]
    for d in docs:
        d.setdefault('content_kind',{'glossary':'concept','service_requirements':'survey','it_configuration':'procedure','workflow':'workflow'}.get(d.get('data_type'),'reference'))
        lines=d['body'].splitlines();clean=[line for line in lines if not ('DEMO' in line and re.search(r'\bVND\b|\d[\d.,]*\s*(?:đồng|ngày công)',line))]
        if clean!=lines:
            d['body']='\n'.join(clean);d['version']='knowledge-2';changes.append(dict(id=d['id'],action='remove_demo_commercial_line'))
        if not d['body'].strip():
            d['body']='Nội dung thương mại minh họa đã được thu hồi; không dùng làm báo giá hoặc cam kết.';d['status']='retired'
    by_id['CMP-BACKUP-HA']['aliases']=['backup','HA','sao lưu','tính sẵn sàng cao','high availability']
    for id,title,group,aliases,refs,body in ARTICLES:
        old=by_id.get(id);doc=sync_knowledge.document(id,title,body,group,aliases=aliases,references=refs,
            content_kind='troubleshooting' if group=='B' else 'concept',data_type='reference_article',
            provenance={'source':'referenced_editorial','review_note':'Biên soạn đối chiếu nguồn; không chứng nhận cấu hình theo hãng/phiên bản.'})
        doc['version']='knowledge-2'
        if id=='KB-NET-VLAN':
            doc.update(scope='generic',review_status='draft_engineer_review')
            doc['provenance']['review_note']='Định nghĩa đối chiếu RFC 5517; checklist biên soạn cần kỹ sư rà soát trước áp dụng, chưa chứng nhận hãng/phiên bản.'
        if old and old['status']=='retired':doc['status']='retired'
        if old:docs[docs.index(old)]=doc
        else:docs.append(doc)
        changes.append(dict(id=id,action='reference_article'))
    path.write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report_path=ROOT/'docs/knowledge-curation.json'
    previous=json.loads(report_path.read_text(encoding='utf8')).get('changes',[]) if report_path.exists() else []
    changes=list({(c['id'],c['action']):c for c in previous+changes}.values())
    report_path.write_text(json.dumps(dict(date=DATE,changes=changes,limitation='Other drafts remain drafts; audit queue is not completed human review.'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Documents:',len(docs),'changes:',len(changes))
if __name__=='__main__':main()
