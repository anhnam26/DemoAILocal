# Phạm vi bảo vệ

Mật khẩu scrypt, phiên có thể thu hồi; member không truy cập admin hoặc usage tài khoản khác. Tài khoản model/limit đọc từ DB và kiểm lại khi gửi API. Quota dự trữ/ghi nhận bằng transaction; không phụ thuộc user-supplied usage, lịch sử chat hoặc giá model.

HTTPS xử lý bởi reverse proxy, APP_ORIGINS xác định Host/Origin được phép. `APP_ENV=lan` là lựa chọn HTTP nội bộ rõ ràng, không mã hóa mật khẩu/cookie; origin chỉ nhận private/loopback IP hoặc localhost. Phải dùng firewall giới hạn mạng tin cậy, không mở cổng này ra Internet. LAN và production yêu cầu mật khẩu admin chủ động cấu hình khi DB rỗng, không dùng file tài khoản development. Cookie Secure trong production, HttpOnly/SameSite. API key chỉ ở .env/env của backend, không trả trong UI. Không dùng cloud fallback hoặc retry tự động. Một process/instance duy nhất.

Chỉ đưa lý thuyết được phép chia sẻ vào kho. API gửi câu hỏi và nguồn liên quan tới OpenRouter. Chưa có SSO/MFA, kiểm tra PII tự động, kiểm chứng ngữ nghĩa trích dẫn hoặc kiểm thử xâm nhập độc lập.

Docker/package deploy loại .env, DB, plaintext credentials và local archives. Git history cũ có thể chứa file từng commit; xóa working tree không xóa lịch sử. Bản local archive chứa dữ liệu/tài khoản cũ và cần được giữ riêng, không tải cùng source server.
