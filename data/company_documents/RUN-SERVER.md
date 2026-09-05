# Máy chủ và ảo hóa — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-SERVER | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Máy chủ và ảo hóa. Trước triển khai: xác minh model/firmware/license và scope 02 host, tối đa 08 máy ảo; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Kiểm phần cứng; cài hypervisor; tạo mạng lưu trữ; máy ảo mẫu; bàn giao. Xác nhận thành công bằng: Danh mục VM; cấu hình network/storage; checklist backup. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.