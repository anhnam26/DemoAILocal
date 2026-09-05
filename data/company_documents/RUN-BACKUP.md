# Backup và diễn tập restore — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-BACKUP | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Backup và diễn tập restore. Trước triển khai: xác minh model/firmware/license và scope 01 hệ thống nguồn, tối đa 02TB, 01 kho backup; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Đánh giá dữ liệu; lịch backup; retention; phân quyền; restore cách ly. Xác nhận thành công bằng: Chính sách backup; báo cáo restore; runbook RPO/RTO. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.