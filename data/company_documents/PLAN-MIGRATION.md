# Di chuyển firewall có kiểm soát — kế hoạch triển khai

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: PLAN-MIGRATION | Phiên bản: company-demo-2.0 | Vai trò: sale, technical, admin | Khách: Chung

Kế hoạch DEMO tổng 7 ngày công, khung 7–9 ngày làm việc. Bước 1: khảo sát và khóa phạm vi. Bước 2: chuẩn bị cấu hình trong lab. Bước 3: triển khai trong khung đã duyệt. Bước 4: kiểm thử các tiêu chí: Mapping policy; kế hoạch cutover; UAT; cấu hình hoàn công. Bước 5: ký biên bản và theo dõi sau bàn giao. Điều kiện khởi công: Thiết bị hai đầu sẵn có; change window; rollback được duyệt. Rủi ro lịch: Chưa gồm HA liên site hoặc viết lại toàn bộ thiết kế IP. PM xác nhận lịch sau kiểm người/thiết bị.