# Tích hợp SIEM cơ bản — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-SIEM | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Tích hợp SIEM cơ bản. Trước triển khai: xác minh model/firmware/license và scope 10 nguồn log, 05 use case; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Khảo sát nguồn; parser; đồng bộ thời gian; use case; kiểm cảnh báo. Xác nhận thành công bằng: Sơ đồ log; danh mục use case; SOP phân loại cảnh báo. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.