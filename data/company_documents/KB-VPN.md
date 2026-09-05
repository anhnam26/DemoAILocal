# VPN rớt định kỳ — bài học ẩn danh

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: KB-VPN | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: Chung

Tình huống tổng hợp DEMO không gắn khách: Log cho thấy chu kỳ đàm phán lại trùng thời điểm mất kết nối; chưa đủ căn cứ để quy lỗi đường truyền. Kiểm tra: Kiểm lifetime, proposal, route và thời gian hệ thống hai đầu; so sánh log cùng múi giờ. Bài học: Theo dõi ổn định sau change và lưu cấu hình trước/sau. Nêu giả thuyết rõ, chỉ kết luận khi có log/test. Chuyển trưởng nhóm nếu ảnh hưởng nhiều site.