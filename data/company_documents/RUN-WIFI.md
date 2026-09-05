# Khảo sát và cấu hình Wi-Fi — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-WIFI | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Khảo sát và cấu hình Wi-Fi. Trước triển khai: xác minh model/firmware/license và scope 01 site, tối đa 05 AP; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Khảo sát RF; thiết kế SSID/VLAN; cấu hình; đo phủ sóng; kiểm roaming. Xác nhận thành công bằng: Sơ đồ AP; báo cáo vùng phủ; cấu hình; UAT roaming. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.