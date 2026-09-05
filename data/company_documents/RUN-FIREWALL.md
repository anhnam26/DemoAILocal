# Triển khai firewall / VPN — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-FIREWALL | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Triển khai firewall / VPN. Trước triển khai: xác minh model/firmware/license và scope 01 site, 01 firewall, tối đa 10 VLAN và 02 tunnel VPN; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Khảo sát routing/VLAN; thiết kế NAT/policy; cấu hình VPN; kiểm ứng dụng và bàn giao. Xác nhận thành công bằng: Backup cấu hình; sơ đồ; bảng policy; UAT Internet/VPN; hướng dẫn vận hành. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.