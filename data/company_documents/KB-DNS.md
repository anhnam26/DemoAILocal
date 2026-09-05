# Ứng dụng không truy cập bằng tên — bài học ẩn danh

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: KB-DNS | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Tình huống tổng hợp DEMO không gắn khách: IP còn truy cập được nhưng DNS phân giải sai. Kiểm tra: Kiểm resolver, TTL, zone nội bộ và split DNS; giữ bản cấu hình trước thay. Bài học: Thử nhiều client; phân biệt cache DNS và lỗi route. Nêu giả thuyết rõ, chỉ kết luận khi có log/test. Chuyển trưởng nhóm nếu ảnh hưởng nhiều site.