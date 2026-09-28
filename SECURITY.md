# Dữ liệu và truy cập

Ứng dụng bind localhost, kiểm Host/Origin, cookie HttpOnly/SameSite, mật khẩu scrypt. Thành viên dùng chung tài liệu; chỉ admin duyệt nguồn, quản lý user và model. Hội thoại kiểm ownership ở backend. Chưa có TLS/SSO/MFA/HA cho phục vụ LAN.

OpenRouter mode gửi câu hỏi và đoạn nguồn ra API. API key đọc từ .env phía server, không trả trong health/admin UI. Không tự retry hoặc chuyển provider khi lỗi. Local mode chỉ gọi localhost.

Kho chỉ chứa lý thuyết và mẫu trống. Không tải dữ liệu khách hàng, secret hoặc thông tin chưa được phép chia sẻ. Mã trích dẫn hợp lệ không bảo đảm câu trả lời đúng ngữ nghĩa; cần đối chiếu nguồn.

Đợt chuyển đổi đã xóa dữ liệu khách hàng trong working tree, DB, backups và chỉ mục cũ. Git history và bản sao ngoài workspace không được rewrite/xóa trong đợt này. Báo sự cố qua kênh riêng của chủ hệ thống, không dán key hoặc hồ sơ nhạy cảm vào issue công khai.
