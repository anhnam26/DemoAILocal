# Chia sẻ tạm thời bằng URL HTTPS ngẫu nhiên trên Linux

Chế độ này dùng **Cloudflare Quick Tunnel**, không cần mua tên miền, tài khoản Cloudflare, IP public hoặc NAT inbound. Đây là chia sẻ thử nghiệm có chủ đích, **không phải production có SLA**. Cần IT phê duyệt việc truyền lưu lượng web qua Cloudflare; câu hỏi/ngữ cảnh AI vẫn gửi tới OpenRouter. URL ngẫu nhiên không thay thế đăng nhập.

## Chuẩn bị một lần

Các ví dụ giả định source tại `/opt/cyberant`, dữ liệu tại `/opt/cyberant/data` và Conda `cyberant`. Thay bằng đường dẫn tuyệt đối thực tế. Không dùng môi trường Python Windows trên Linux.

1. Cài Python/dependency theo `/opt/cyberant/docs/DEPLOYMENT.md`. Giữ nguyên API key/model trong `/opt/cyberant/.env`.
2. Cài `cloudflared` từ nguồn chính thức, chọn đúng distro/CPU: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/ . Script không tự tải/chạy installer và không thêm thư viện Python.
3. Kiểm tra `cloudflared --version`. Dùng bản được Cloudflare hỗ trợ. Không chạy ứng dụng bằng root.
4. Phải có DB hiện có với admin đang hoạt động: nếu chuyển server, restore snapshot nhất quán **trước** lần chạy đầu. Nếu cài mới, khởi tạo riêng ở loopback với origin HTTP localhost và chế độ LAN, đặt bootstrap password mạnh theo hướng dẫn triển khai, đăng nhập kiểm tra rồi dừng. Chế độ share không tự tạo DB rỗng để tránh mất dấu tài khoản cũ khi sai đường dẫn.
5. Đổi mật khẩu yếu/cũ, rà soát tài khoản và dữ liệu được phép chia sẻ. Bỏ bootstrap password khỏi cấu hình sau khởi tạo. Không chuyển `/opt/cyberant/data/initial-accounts.json` lên server; share sẽ từ chối nếu file plaintext này tồn tại.
6. Dừng service/tiến trình/Docker đang dùng cùng DB, chờ request đang chạy xong. Nếu service tên `cyberant`: `sudo systemctl stop cyberant`. Không bật lại service trong phiên share.
7. Kiểm tra quyền sở hữu bằng `ls -ld /opt/cyberant/data` và `ls -l /opt/cyberant/.env /opt/cyberant/data/app.sqlite3`. `.env`, thư mục dữ liệu và DB phải thuộc user chạy ứng dụng, không cấp quyền group/other. Sau khi xác nhận đúng đường dẫn và chủ sở hữu, ví dụ:

```bash
chmod 600 /opt/cyberant/.env /opt/cyberant/data/app.sqlite3
chmod 700 /opt/cyberant/data
```

Nếu có WAL/SHM, đặt quyền `600` cho các file đó khi app đã dừng. Nếu dùng `APP_DATA_DIR` ngoài source, áp dụng quyền tại đường dẫn đó. Không dùng `chmod -R 777`; không tự thay ownership cả source. Launcher kiểm tra và báo lỗi, không tự sửa quyền/xóa file. Source/kho tri thức nên chỉ cho service đọc, không cho user không liên quan truy cập.

## Mỗi lần chia sẻ

```bash
bash /opt/cyberant/start.sh --share
```

Hoặc khi đã activate đúng môi trường:

```bash
python /opt/cyberant/main.py --share
```

Terminal in `Public URL: https://<ngẫu-nhiên>.trycloudflare.com` sau khi app khởi động và tunnel báo kết nối. Chỉ gửi link này, không gửi `.env`, mật khẩu admin hoặc link file backup. Xác minh bằng 4G/5G trước khi gửi người dùng. Không có lời gọi kiểm tra public tự động hoặc lời gọi AI tính phí.

Launcher luôn bind `127.0.0.1`, kể cả khi `/opt/cyberant/start.sh` hoặc `.env` đặt `0.0.0.0`. Nó dùng production/cookie Secure và **chỉ origin HTTPS vừa cấp** trong môi trường tiến trình; không ghi URL vào `.env`, không cho wildcard. Tài khoản/DB không đổi; hostname mới cần đăng nhập lại. Không cần Nginx/Let's Encrypt cho phiên tunnel này. Đường HTTP LAN cũ không được phục vụ bởi phiên share.

Nếu `cloudflared` không có trong PATH hoặc mạng chặn UDP:

```bash
bash /opt/cyberant/start.sh --share --cloudflared /usr/local/bin/cloudflared --share-protocol http2
```

HTTP/2 vẫn cần kết nối outbound được IT cho phép (Cloudflare Tunnel thường dùng TCP 7844; QUIC dùng UDP 7844, cấp URL cần HTTPS). Không mở port 8088 inbound. Nếu có config named tunnel trong `/home/<user>/.cloudflared`, các thư mục cloudflare-warp, `/etc/cloudflared` hoặc `/usr/local/etc/cloudflared`, chương trình từ chối để không vô tình dùng route cũ. Dùng tài khoản/host chuyên biệt; không xóa config đang dùng của dịch vụ khác.

## Dừng, lỗi và dữ liệu

- Ctrl+C/SIGTERM/SIGHUP: đóng tunnel, cho Uvicorn dừng có kiểm soát (tối đa khoảng 400 giây để xử lý request). Chờ tác vụ hoàn tất trước khi dừng để tránh mất phản hồi.
- Tunnel thoát: app dừng, không tự tạo link mới hoặc tự gọi lại AI. Khi khởi động lại, dịch vụ cấp URL ngẫu nhiên mới, không bảo đảm giữ URL cũ.
- Khi đóng SSH, phiên foreground không bảo đảm tiếp tục. Không dùng `kill -9`: cleanup không chạy. Sau crash/kill cưỡng bức, kiểm tra và dừng đúng tiến trình cloudflared còn sót trước khi khởi động lại; không dùng `pkill cloudflared` nếu máy còn tunnel khác.
- Khóa `/opt/cyberant/data/.app-instance.lock` ngăn các process **bản mới** cùng dùng một thư mục dữ liệu, kể cả hai cổng khác nhau/direct Uvicorn. Không xóa file lock khi đang chạy; khóa được OS giải phóng khi process chết. Bản cũ không có khóa không được phát hiện ở cổng khác: phải dừng thủ công trước cập nhật. Không dùng NFS/shared DB, nhiều replica hoặc alias hardlink DB.
- URL và khóa không chứa API key. Quyền `umask 077` áp dụng cho file mới trong phiên share; không mã hóa hay tự backup file hiện có.

## Giới hạn bắt buộc hiểu trước khi dùng

Quick Tunnel không cam kết uptime, giới hạn 200 request in-flight (không phải 200 người), không hỗ trợ SSE. Dự án hiện dùng HTTP trả kết quả chat một lần; chưa đổi sang job/polling. Cloudflare có proxy read timeout hữu hạn (tài liệu tại thời điểm triển khai nêu mặc định khoảng 125 giây), trong khi hàng chờ/provider của app có thể lâu hơn. Tăng timeout Nginx không khắc phục giới hạn này. Nếu gặp 524/mất kết nối, chờ và kiểm tra lịch sử/usage, không tự gửi lại vì AI có thể đã tính phí. Cần thiết kế job/polling riêng nếu muốn tin cậy cho request dài.

Không có MFA, WAF hoặc rate limit IP thật mới trong tính năng này. Proxy headers vẫn tắt: app thấy IP loopback, chặn đăng nhập sai có thể dùng chung theo username; không tin `X-Forwarded-For` gửi tùy ý. Admin vẫn có quyền quản trị và xem lịch sử theo ứng dụng; kho tài liệu là kho chung, không phân tách phòng ban. Mã hóa backup và restore phải tổ chức riêng theo `/opt/cyberant/docs/DEPLOYMENT.md`. Repository/registry chứa kho tri thức cần hạn chế quyền truy cập.

## Checklist nghiệm thu trên Linux thực tế

- Khởi động bằng user không root, kiểm tra bind bằng `ss -ltnp`; 8088 chỉ loopback.
- Kiểm tra link qua 4G/5G, đăng nhập/logout, cookie Secure/HttpOnly/SameSite, HTTPS và hostname mới sau restart.
- Chưa đăng nhập: API dữ liệu 401; member: API admin 403. Thử URL `/.env`, `/data/app.sqlite3`, `/data/backups/`, `/knowledge/documents.json`, `/.git/config`: không trả file.
- Thử một chat đã được duyệt về nội dung/chi phí, thử tải lên và history/quota; kiểm tra timeout dưới tải. Không coi health OK là xác nhận AI hoạt động.
- Dừng tunnel đột ngột: app dừng. Ctrl+C: tunnel hết phục vụ. Thử chạy hai cổng cùng DB: tiến trình thứ hai phải thất bại trước migration/recovery.
- Xác nhận `.env` không đổi, dữ liệu vẫn có sau restart, backup/restore thành công ở môi trường riêng.

Nguồn: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/ và https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/ .
