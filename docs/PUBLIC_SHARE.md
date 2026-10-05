# Chia sẻ HTTPS tạm thời qua Cloudflare Quick Tunnel

Chạy trên server Linux bằng environment Conda đã có, không Docker:

```bash
cd /home/cba/Chatbot2/TestSystem
bash start.sh --share
```

Đường dẫn trên theo log server hiện tại; thay nếu project đã được chuyển.
Quick Tunnel cấp hostname ngẫu nhiên mỗi lần tạo tunnel. Không cần tài khoản/domain
Cloudflare; không SLA, dành cho test/chia sẻ tạm thời, không coi URL là secret.

## Chuẩn bị

- Với server đã có layout/database: giữ `.env` và data, không init/migrate lại.
  Chạy `operations check` khi app đã dừng; xem `DEPLOYMENT.md` cho cài mới thực sự.
- Có admin hoạt động, cấu hình API key/model; không có mật khẩu plaintext trong data.
- Config, layout và mọi DB thuộc user app, mode 600; thư mục mode 700.
- Data là bộ DB mới, không phải một `app.sqlite3` cũ. Không NFS/WAL/multiple workers.
- Được phép chia sẻ dữ liệu: Cloudflare mang lưu lượng web, OpenRouter nhận câu hỏi
  và nguồn liên quan. Kho tri thức dùng chung, admin có chức năng xem lịch sử.
- Cài cloudflared chính thức theo https://developers.cloudflare.com/cloudflare-one/downloads/ .
  Kiểm `cloudflared --version`; không dùng binary nguồn không rõ.
- User/host chuyên dụng không có config named tunnel tại các vị trí cloudflared mặc định.

## Cấu hình và lệnh chạy

Mặc định đọc `.env` trong root project. Chỉ đặt `APP_ENV_FILE` nếu server đang
sử dụng file riêng; không đổi sang đường dẫn minh họa không tồn tại.
Không `source .env` trong Bash: Python đọc file như dữ liệu, không thực thi shell.

```bash
bash start.sh --share
# Khi QUIC/UDP bị chặn:
bash start.sh --share --share-protocol http2
# Nếu executable không có trên PATH: dùng đường dẫn thật của binary đã cài.
bash start.sh --share --cloudflared /usr/bin/cloudflared
```

Script tìm/activate Conda `cyberant`; có thể đặt `CONDA_EXE` hoặc `CONDA_ENV_NAME`.
Không root, không cần mở port app inbound cho chế độ share. Port lấy từ APP_PORT
(hoặc CLI override rõ ràng), không bị ép thành 8088. API key/model/quota/RAG và
APP_DATA_DIR/APP_BACKUP_DIR vẫn theo cấu hình. Chỉ override runtime APP_HOST thành
127.0.0.1, APP_ENV thành production, APP_PORT theo port đã chọn, APP_ORIGINS thành
đúng URL HTTPS vừa nhận; không ghi lại `.env`. Nhờ vậy không phải sửa origin mỗi lần.
Cookie Secure/HttpOnly, đăng nhập và kiểm Host/Origin vẫn hoạt động. Không tự cho
phép wildcard trycloudflare.com hoặc origins LAN của file trong phiên share.

Chỉ dùng URL sau dòng `Public URL` khi app đã khởi động; người dùng đăng nhập
bằng tài khoản hiện có. Dòng này chưa đảm bảo URL truy cập được từ mọi mạng.

Chạy thường `bash start.sh` vẫn kiểm bảo mật `.env` gốc: development chỉ bind
loopback; LAN cần mode lan và origins private/loopback, không IP public HTTP;
production cần origins HTTPS. Không âm thầm sửa cấu hình không hợp lệ để chạy LAN.

Ctrl+C đóng app/tunnel, chờ request đang xử lý. Khi tunnel hỏng app dừng, không tự
retry câu hỏi. Đóng SSH có thể dừng phiên foreground; nếu dùng service, xem
`DEPLOYMENT.md` và thêm --share vào ExecStart một cách chủ động, không chạy hai bản.
Không chạy song song phiên LAN, share và service cùng data. Đổi mode không đổi dữ liệu.

## Giới hạn và xử lý lỗi

- Request AI dài có thể timeout qua Cloudflare; kiểm lịch sử/usage trước gửi lại.
- Không có streaming/SLA, IP ghi nhận có thể loopback; chưa có WAF/MFA/rate-limit IP thật.
- Cloudflare giới hạn Quick Tunnel 200 request đang xử lý; vượt giới hạn có thể trả 429.
- Mạng đích phải cho phép outbound Cloudflare và OpenRouter.
- Có thể thử `--share-protocol http2` nếu QUIC bị chặn; không tắt bảo mật Host/Origin.
- Sai quyền: sửa đúng file/thư mục theo user service, không chmod 777 toàn dự án.
- Missing layout: migrate vào đích mới và chỉnh APP_DATA_DIR; không xóa DB cũ.
- Startup/recovery/schema thất bại: không công bố link, dừng và kiểm private trước.
- SIGKILL/mất điện có thể để tunnel mồ côi khi chạy manual; kiểm process thủ công.
- Đóng share không xóa tài khoản/hội thoại. Không upload config/DB làm web root.

Tên miền ổn định/named tunnel hoặc Nginx HTTPS là thiết kế triển khai khác,
không tự thêm trong đợt chuẩn hóa này.

Tài liệu Cloudflare: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/ .