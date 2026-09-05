# Triển khai WAF cơ bản — kế hoạch triển khai

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: PLAN-WAF | Phiên bản: company-demo-2.0 | Vai trò: sale, technical, admin | Khách: Chung

Kế hoạch DEMO tổng 5 ngày công, khung 5–7 ngày làm việc. Bước 1: khảo sát và khóa phạm vi. Bước 2: chuẩn bị cấu hình trong lab. Bước 3: triển khai trong khung đã duyệt. Bước 4: kiểm thử các tiêu chí: Sơ đồ luồng; chính sách; kết quả test; danh sách ngoại lệ. Bước 5: ký biên bản và theo dõi sau bàn giao. Điều kiện khởi công: Có DNS/TLS và test account; có đầu mối ứng dụng; không thay source code. Rủi ro lịch: Chưa gồm license, chống DDoS volumetric hoặc sửa lỗi ứng dụng. PM xác nhận lịch sau kiểm người/thiết bị.