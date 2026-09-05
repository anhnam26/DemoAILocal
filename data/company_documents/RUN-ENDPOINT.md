# Triển khai bảo vệ endpoint — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-ENDPOINT | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Triển khai bảo vệ endpoint. Trước triển khai: xác minh model/firmware/license và scope Tối đa 50 máy Windows trong 01 tenant; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Kiểm danh sách máy; pilot agent; policy; rollout; báo cáo. Xác nhận thành công bằng: Danh sách agent; policy; hướng dẫn xử lý cảnh báo. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.