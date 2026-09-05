# Khảo sát và thiết kế hạ tầng — runbook kỹ sư

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: RUN-AUDIT | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Checklist DEMO Khảo sát và thiết kế hạ tầng. Trước triển khai: xác minh model/firmware/license và scope 01 site, tối đa 20 thiết bị; sao lưu; kiểm tài khoản dự phòng; lab và phê duyệt change. Thao tác theo thứ tự: Phỏng vấn; inventory; topology; đánh giá hiện trạng; đề xuất. Xác nhận thành công bằng: Báo cáo hiện trạng; HLD; roadmap ưu tiên. Dừng nếu mất truy cập quản trị hoặc ứng dụng trọng yếu không đạt UAT; quay lui theo bản sao đã kiểm. Thu log có mốc giờ; che bí mật; không chạy lệnh không đúng phiên bản. Owner: trưởng nhóm kỹ thuật.