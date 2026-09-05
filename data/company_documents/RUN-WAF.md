# Triển khai WAF cơ bản — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-WAF | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Triển khai WAF cơ bản. Trước triển khai: xác minh model/firmware/license và scope 01 ứng dụng web, 01 tên miền, tối đa 10 API chính; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Khảo sát HTTP/TLS; cấu hình reverse proxy; staging policy; tuning; bàn giao. Xác nhận thành công bằng: Sơ đồ luồng; chính sách; kết quả test; danh sách ngoại lệ. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.