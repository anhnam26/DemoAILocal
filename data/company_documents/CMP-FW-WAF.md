# So sánh firewall mạng và WAF

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: CMP-FW-WAF | Phiên bản: company-demo-2.0 | Vai trò: sale, technical, admin | Khách: Chung

| Tiêu chí | Firewall mạng | WAF |
| Mục tiêu | Kiểm soát kết nối giữa các vùng mạng | Bảo vệ ứng dụng web và API |
| Lưu lượng | Kết nối IP/port, VPN, NAT theo tính năng | HTTP/HTTPS và nội dung yêu cầu web |
| Vị trí thường dùng | Biên Internet hoặc giữa VLAN/vùng mạng | Trước web server, reverse proxy hoặc dịch vụ WAF |
| Bài toán mẫu | Chặn truy cập trái phép giữa mạng khách và máy chủ | Lọc yêu cầu web có mẫu tấn công hoặc bất thường |
| Giới hạn | Không tự thay cho bảo vệ logic ứng dụng | Không thay firewall mạng hoặc sửa source code |
| Cần phối hợp | WAF, endpoint, backup, giám sát | Firewall, phát triển ứng dụng, giám sát |
| Gói dịch vụ DEMO | 12.000.000 VND / 4 ngày công | 14.000.000 VND / 5 ngày công |