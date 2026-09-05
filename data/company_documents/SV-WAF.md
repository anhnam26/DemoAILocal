# WAF và bảo vệ ứng dụng web

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: SV-WAF | Phiên bản: demo-1.0 | Vai trò: sale, technical, admin | Khách: Chung

DỮ LIỆU DEMO GIẢ LẬP — KHÔNG PHẢI CHÍNH SÁCH THẬT CYBERANT.
WAF lọc lưu lượng HTTP/HTTPS tới ứng dụng web, giúp phát hiện và hạn chế các mẫu tấn công ở lớp ứng dụng. Firewall mạng kiểm soát kết nối mạng và chính sách giữa các vùng. Hai giải pháp có vai trò bổ sung, không thay thế hoàn toàn cho nhau. Cần hỏi ứng dụng public/private, lưu lượng, TLS, DNS, kiến trúc reverse proxy, API, yêu cầu lưu log và quy trình điều chỉnh false positive. WAF không thay thế sửa lỗi ứng dụng. Dịch vụ mẫu gồm khảo sát, thiết kế, cấu hình, tuning và bàn giao.