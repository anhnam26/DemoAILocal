# Triển khai WAF cơ bản — phạm vi và bàn giao

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: SCOPE-WAF | Phiên bản: company-demo-2.0 | Vai trò: sale, technical, admin | Khách: Chung

Bao gồm: Khảo sát HTTP/TLS; cấu hình reverse proxy; staging policy; tuning; bàn giao. Quy mô: 01 ứng dụng web, 01 tên miền, tối đa 10 API chính. Bàn giao: Sơ đồ luồng; chính sách; kết quả test; danh sách ngoại lệ. Ngoại lệ: Chưa gồm license, chống DDoS volumetric hoặc sửa lỗi ứng dụng. Để tư vấn sơ bộ có thể dùng gói chuẩn; chỉ cần hỏi thêm các mục khác với phạm vi chuẩn.