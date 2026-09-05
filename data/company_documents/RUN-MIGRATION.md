# Di chuyển firewall có kiểm soát — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-MIGRATION | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Di chuyển firewall có kiểm soát. Trước triển khai: xác minh model/firmware/license và scope 01 site, tối đa 150 policy và 04 VPN; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Đối chiếu policy; chuyển đổi lab; chạy song song; cutover; hậu kiểm. Xác nhận thành công bằng: Mapping policy; kế hoạch cutover; UAT; cấu hình hoàn công. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.