# Chia sẻ HTTPS tạm thời qua Cloudflare Quick Tunnel

Phương án chính đã chọn: Linux + Miniconda + `start.sh --share`, không Docker.
URL ngẫu nhiên thay đổi sau mỗi khởi động, không SLA, không coi URL là secret.

## Chuẩn bị

- Hoàn tất init/migrate và `operations check` theo `DEPLOYMENT.md`.
- Có admin hoạt động, cấu hình API key/model; không có mật khẩu plaintext trong data.
- Config, layout và mọi DB thuộc user app, mode 600; thư mục mode 700.
- Data là bộ DB mới, không phải một `app.sqlite3` cũ. Không NFS/WAL/multiple workers.
- Được phép chia sẻ dữ liệu: Cloudflare mang lưu lượng web, OpenRouter nhận câu hỏi
  và nguồn liên quan. Kho tri thức dùng chung, admin có chức năng xem lịch sử.
- Cài cloudflared chính thức theo https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ .
  Kiểm `cloudflared --version`; không dùng binary nguồn không rõ.
- User/host chuyên dụng không có config named tunnel tại các vị trí cloudflared mặc định.

```bash
export APP_ENV_FILE=/etc/cyberant/cyberant.env
bash /opt/cyberant/start.sh --share --cloudflared /usr/bin/cloudflared
```

Script tìm/activate Conda `cyberant`; có thể đặt `CONDA_EXE` hoặc `CONDA_ENV_NAME`.
Không root, không cần mở 8088 inbound. Share luôn bind `127.0.0.1`, đặt production
và exact origin URL trong môi trường tiến trình, không sửa file config.
Chỉ dùng URL sau dòng `Public URL`; người dùng đăng nhập như trước.

Ctrl+C đóng app/tunnel, chờ request đang xử lý. Khi tunnel hỏng app dừng, không tự
retry câu hỏi. Chạy nền bằng service theo `DEPLOYMENT.md`, xem URL qua journalctl.
Không chạy song song phiên LAN, share và service cùng data. Đổi mode không đổi dữ liệu.

## Giới hạn và xử lý lỗi

- Request AI dài có thể timeout qua Cloudflare; kiểm lịch sử/usage trước gửi lại.
- Không có streaming/SLA, IP ghi nhận có thể loopback; chưa có WAF/MFA/rate-limit IP thật.
- Mạng đích phải cho phép outbound Cloudflare và OpenRouter.
- Có thể thử `--share-protocol http2` nếu QUIC bị chặn; không tắt bảo mật Host/Origin.
- Sai quyền: sửa đúng file/thư mục theo user service, không chmod 777 toàn dự án.
- Missing layout: migrate vào đích mới và chỉnh APP_DATA_DIR; không xóa DB cũ.
- Startup/recovery/schema thất bại: không công bố link, dừng và kiểm private trước.
- SIGKILL/mất điện có thể để tunnel mồ côi khi chạy manual; kiểm process thủ công.
- Đóng share không xóa tài khoản/hội thoại. Không upload config/DB làm web root.

Tên miền ổn định/named tunnel hoặc Nginx HTTPS là thiết kế triển khai khác,
không tự thêm trong đợt chuẩn hóa này.