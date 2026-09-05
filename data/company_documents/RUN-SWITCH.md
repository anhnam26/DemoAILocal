# Triển khai switch và VLAN — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-SWITCH | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Triển khai switch và VLAN. Trước triển khai: xác minh model/firmware/license và scope 01 site, tối đa 03 switch, 10 VLAN; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Khảo sát uplink; VLAN/trunk; STP; quản trị; kiểm kết nối. Xác nhận thành công bằng: Topology; port map; bảng VLAN; backup cấu hình. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.