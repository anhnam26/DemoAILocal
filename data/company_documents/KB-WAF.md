# False positive API — bài học ẩn danh

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: KB-WAF | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Tình huống tổng hợp DEMO không gắn khách: API upload hợp lệ bị chặn sau bật rule mới. Kiểm tra: Thu request đã che dữ liệu, test staging, giới hạn ngoại lệ đúng endpoint. Bài học: Không tắt toàn bộ WAF vì một API bị chặn. Nêu giả thuyết rõ, chỉ kết luận khi có log/test. Chuyển trưởng nhóm nếu ảnh hưởng nhiều site.