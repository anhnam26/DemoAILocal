# Triển khai server

## Cấu hình

Compose chạy một process uvicorn, bind container 8088 nhưng chỉ publish vào loopback của host. Nginx/Caddy trên host làm HTTPS; mẫu Nginx ở `deploy/nginx.conf.example`. Đặt `APP_ORIGINS` đúng origin gồm scheme + hostname + port nếu có, phân cách dấu phẩy nếu cần nhiều origin. Chặn Host/Origin khác, cookie Secure/HttpOnly/SameSite trong production. Không dùng wildcard.

Uvicorn hiện không tin proxy headers; IP trong phiên là IP proxy và login rate limit theo IP proxy + username. Nếu cần IP client thật, thiết lập allowlist proxy chính xác và kiểm lại trước bật; không đặt tin mọi IP trên cổng public. App kiểm Origin độc lập và cookie Secure dựa vào APP_ENV, không dựa vào header client.

```sh
cp .env.example .env
# Chỉnh .env: key, models, APP_ORIGINS, bootstrap password
docker compose build
docker compose up -d
docker compose ps
docker compose logs --tail=100 app
curl http://127.0.0.1:8088/api/health
```

Health chỉ xác nhận backend sống; không thử key, model availability hoặc số dư. Admin chọn model trong bốn giá trị server cấu hình; client không được chọn model tùy ý cho chat. Khi xóa một model khỏi .env, tài khoản đang dùng model đó phải được admin gán lại; không tự chuyển sang model khác.

Dockerfile dùng non-root UID 10001, root filesystem read-only, volume data riêng, bỏ capabilities, giới hạn thư mục temp. Không COPY .env/data/test/archives vào image. Dependency runtime đã khóa cho Python 3.14/Linux; cần build image thật và kiểm trên server đích.

## Giữ tài khoản đang có khi chuyển server

DB `data/app.sqlite3` hiện giữ tài khoản/mật khẩu đã hash, hội thoại, tài liệu upload, usage và audit. Docker khởi tạo mới sẽ không dùng DB này trừ khi chuyển riêng. Không copy trực tiếp DB đang ghi WAL.

1. Dừng nhận yêu cầu mới/chờ các lượt hoàn tất. Dùng nút **Hệ thống → Sao lưu cơ sở dữ liệu** để tạo SQLite snapshot nhất quán trong `data/backups`.
2. Chuyển snapshot qua kênh bảo mật tới server, đặt tên `app.sqlite3` vào named volume `/app/data` **trước lần khởi động đầu tiên**.
3. Bảo đảm UID 10001 có quyền đọc/ghi volume. Không ghi đè DB của deployment đang hoạt động. Sao lưu file .env riêng; không đặt vào image.
4. Khởi động và kiểm đăng nhập, danh sách 1.194 tài liệu, model/hạn mức và báo cáo usage.

Có thể tạo volume bằng `docker compose create`, rồi dùng container công cụ để chép snapshot vào volume trước `docker compose start`. Tên volume thực tế xem qua `docker volume ls`, không đoán tên nếu đã đổi project name. Nếu đã khởi động với DB rỗng, dừng app và xử lý DB mới rõ ràng trước khi restore; không ghép hai DB.

## Backup / cập nhật / restore

Backup SQLite bao gồm usage, tài khoản, nguồn đã import và upload. Giữ thêm `knowledge/documents.json`, phiên bản code và cấu hình .env riêng. Backup chứa dữ liệu người dùng, không công khai. Khi restore, dừng app, dùng snapshot thống nhất, bảo đảm quyền file và khởi động lại. Pending in-flight khi crash được chuyển thành chưa rõ usage để admin đối soát; không tự bỏ lượng token có thể đã dùng.

`docker compose up -d --build` cập nhật image, giữ named volume. Không dùng `docker compose down -v` nếu cần giữ dữ liệu. Thay nội dung knowledge trong source cần build lại image (hoặc thiết kế mount chỉ đọc riêng); nút đồng bộ áp dụng bản knowledge đang ở container.

Không chạy nhiều worker hoặc nhiều replica: quota dùng SQLite transaction, nhưng khóa hội thoại và hàng chờ vẫn trong một tiến trình. Chưa kiểm thử tải/khôi phục trên server đích. Cần smoke test HTTPS, đăng nhập, backup/restore và hạn mức sau khi có server/tên miền.
