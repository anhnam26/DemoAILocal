# Phạm vi bảo vệ

Mật khẩu scrypt, phiên có thể thu hồi; member không truy cập admin hoặc usage tài khoản khác. Tài khoản model/limit đọc từ DB và kiểm lại khi gửi API. Quota dự trữ/ghi nhận bằng transaction; không phụ thuộc user-supplied usage, lịch sử chat hoặc giá model.

HTTPS xử lý bởi reverse proxy, APP_ORIGINS xác định Host/Origin được phép. `APP_ENV=lan` là lựa chọn HTTP nội bộ rõ ràng, không mã hóa mật khẩu/cookie; origin chỉ nhận private/loopback IP hoặc localhost. Phải dùng firewall giới hạn mạng tin cậy, không mở cổng này ra Internet. LAN và production yêu cầu mật khẩu admin chủ động cấu hình khi DB rỗng, không dùng file tài khoản development. Cookie Secure trong production, HttpOnly/SameSite. API key chỉ ở .env/env của backend, không trả trong UI. Không dùng cloud fallback hoặc retry tự động. Một process/instance duy nhất.

Chỉ đưa lý thuyết được phép chia sẻ vào kho. API gửi câu hỏi và nguồn liên quan tới OpenRouter. Chưa có SSO/MFA, kiểm tra PII tự động, kiểm chứng ngữ nghĩa trích dẫn hoặc kiểm thử xâm nhập độc lập.

Docker/package deploy loại .env, DB, plaintext credentials và local archives. Git history cũ có thể chứa file từng commit; xóa working tree không xóa lịch sử. Bản local archive chứa dữ liệu/tài khoản cũ và cần được giữ riêng, không tải cùng source server.

## Chia sẻ tạm thời

`main.py --share` chỉ hỗ trợ Linux, chủ động public ứng dụng qua Cloudflare Quick Tunnel. Chế độ này bind loopback, đặt production và exact HTTPS origin trong môi trường tiến trình, không sửa `.env` hoặc tắt kiểm tra Host/Origin. Yêu cầu DB có sẵn với admin hoạt động, không có `initial-accounts.json`, `.env`/DB thuộc user chạy app và không cấp quyền group/other. Thư mục dữ liệu riêng tư, umask 077 cho file mới. Không tự mã hóa SQLite/backup hoặc tự sửa quyền file cũ.

Các bản mới giữ khóa OS theo thư mục dữ liệu trước migration/recovery, kể cả direct Uvicorn; không chạy nhiều worker, không dùng shared/network filesystem và không chạy cùng bản cũ chưa có khóa. Khi tunnel thoát, app dừng; SIGKILL/mất điện không bảo đảm cleanup tiến trình tunnel, cần kiểm tra thủ công. Không chuyển toàn bộ thư mục dự án thành web root.

Cloudflare xử lý lưu lượng web: cần phê duyệt của công ty. Link ngẫu nhiên không phải kiểm soát truy cập và không có SLA. Không có MFA, WAF/rate limit theo IP thật được bổ sung trong đợt này; Uvicorn vẫn không tin proxy header tùy ý, nên sau tunnel các IP được ghi nhận là loopback và giới hạn login có thể dùng chung theo username. Đây không phải cấu hình production đã được pentest. Kho tri thức được dùng chung cho các tài khoản có quyền đăng nhập; admin có thể xem lịch sử theo chức năng hiện có. Chỉ public dữ liệu đã được phép.

Hướng dẫn đầy đủ: [PUBLIC_SHARE](docs/PUBLIC_SHARE.md).
