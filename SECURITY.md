# Bảo mật và giới hạn

- Mật khẩu scrypt, cookie HttpOnly/SameSite strict, Secure trong production.
- Thu hồi phiên khi khóa/đổi quyền/reset mật khẩu; migration/restore thu hồi phiên cũ.
- Member không truy cập API admin/hội thoại tài khoản khác.
- Kiểm lại quyền model/hạn mức trước provider; usage không phụ thuộc việc xóa chat.
- API key chỉ ở cấu hình backend; không trả UI/log/gói source.
- Init yêu cầu mật khẩu admin chủ động cấu hình; không đọc/sinh mật khẩu plaintext.
- Host/Origin chính xác, không wildcard. Không tin proxy headers tùy ý. IP sau
  Quick Tunnel có thể là loopback; chưa có rate limit IP thật/chống bot chuyên dụng.
- Không root. Config/DB/backup mode 600, thư mục 700, umask 077.
- Không tự mã hóa SQLite/backup; bảo vệ ổ đĩa/kênh truyền. Backup chứa dữ liệu riêng tư.
- Một process/một worker, local disk. DELETE journals + FULL synchronous bắt buộc
  để giao dịch attached dùng super-journal. Không NFS/multiple replicas.
- Không tự retry yêu cầu AI có phí. Usage không rõ giữ ngân sách chờ đối soát.

Quick Tunnel public tạm thời, URL ngẫu nhiên không thay phân quyền. Cloudflare xử lý
lưu lượng web, OpenRouter/provider xử lý câu hỏi/ngữ cảnh. Chỉ chia sẻ dữ liệu được
phép và được đơn vị quản lý chấp thuận. Chưa SSO/MFA, kiểm PII tự động hoặc pentest.
Kiểm ID trích dẫn không chứng minh ngữ nghĩa. PDF không tin cậy vẫn có rủi ro tài
nguyên; giới hạn 2MB/30 trang không thay sandbox/OCR.

Không đưa `.env`, `initial-accounts.json`, DB/log/backup/artifacts hoặc lịch sử Git
lên server như source public. Nếu secret lộ, xoay secret; xóa working tree không
xóa lịch sử Git/bản sao. Dữ liệu/cấu hình cũ được giữ riêng, không xóa tự động.

Xem `docs/DEPLOYMENT.md`, `docs/DATA_LAYOUT.md`, `docs/PUBLIC_SHARE.md`.