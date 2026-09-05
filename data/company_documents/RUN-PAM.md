# Triển khai PAM khởi đầu — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-PAM | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Triển khai PAM khởi đầu. Trước triển khai: xác minh model/firmware/license và scope 10 quản trị viên, 20 tài sản; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Khảo sát quyền; thiết kế vault/session; tích hợp danh tính; pilot; nghiệm thu. Xác nhận thành công bằng: Ma trận quyền; workflow; biên bản kiểm truy vết. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.