# Triển khai trực tiếp — server LAN

Không Docker. Ví dụ source `/opt/cyberant`; cấu hình `/etc/cyberant/cyberant.env`;
dữ liệu `/var/lib/cyberant`; backup `/var/backups/cyberant`. Thay đường dẫn/user
theo server thực tế. Các thư mục chứa dữ liệu phải thuộc user chạy app.

## 1. Chuẩn bị

Nếu dùng ZIP **private có .env/database**, đọc `PRIVATE_BUNDLE.md`: database đã
khởi tạo, không init/migrate lại. Các bước source-only bên dưới dành cho gói sạch.

1. Tạo user Linux không đặc quyền. Không chạy app bằng root.
2. Chép gói source-only từ `tools/package_server.py`, không copy toàn bộ máy dev.
3. Dùng Python environment hiện có (Conda nếu đã được cấu hình):

```bash
python --version
python -c "import sys; print(sys.executable)"
cd /opt/cyberant
python -m pip install -r /opt/cyberant/requirements-lock.txt
```

Phiên phát triển đã kiểm trên Python 3.13/Windows; lockfile cần kiểm trên server
Linux đích. Không tạo environment mới tự động. Tạo config từ mẫu khi chưa có, giữ API key/model cũ. Chỉ đổi cấu hình
được yêu cầu. Cài mới MODEL mặc định phải có giá trị để cấp quyền cho admin.

```bash
export APP_ENV_FILE=/etc/cyberant/cyberant.env
chmod 600 /etc/cyberant/cyberant.env
```

`APP_ENV_FILE` là biến môi trường launcher, không đặt nó trong chính file config.
Process env ghi đè file. CLI host/port ghi đè process/file. `APP_DATA_DIR` tương
đối được giải theo source root; production nên dùng tuyệt đối. `APP_BACKUP_DIR`
không nằm trong source. Không cấp group/other đọc DB/config/backup.

## 2. Chuyển DB cũ hoặc init mới — chọn đúng một

### Chuyển dữ liệu hiện có

Nếu đã dùng layout v1 (sáu kho), không migrate lại database legacy. Dừng app,
`operations backup --target <NEW private backup>` trên máy nguồn, chuyển toàn bộ
bộ backup qua SSH/SFTP rồi `operations restore --source <backup> --target /var/lib/cyberant`.
Chạy check và đối chiếu tài khoản/chat/usage. Các lệnh migrate bên dưới chỉ cho DB gộp cũ.

Dừng nhận request/chờ AI xong, dừng instance cũ. Lấy SQLite snapshot bằng backup
API cũ hoặc SQLite backup API; không copy riêng DB đang ghi WAL. Chuyển qua SSH/SFTP
đến `/srv/cyberant-import/app.sqlite3`, mode 600, thư mục cha 700.

```bash
python -m cyberant.operations migrate \
  --source /srv/cyberant-import/app.sqlite3 --target /var/lib/cyberant
python -m cyberant.operations check
```

Đích không được tồn tại. Nếu user service không ghi được `/var/lib`, admin hệ điều
hành chuẩn bị parent/quyền trước, không chạy migration/app bằng root.
Migration giữ nguồn, nâng schema trên staging, đối chiếu hash/số lượng, bảo toàn
bảng cũ trong archive và thu hồi phiên. Không sync corpus mới âm thầm khi migrate.
Đọc `migration-report.json`, kiểm tài khoản/quota/nguồn upload/retired sau chuyển.
Không copy `initial-accounts.json`, PID/log Windows hoặc backup cũ vào data mới.

### Cài mới

Đặt `BOOTSTRAP_ADMIN_PASSWORD` 14–128 ký tự và username hợp lệ trong config:

```bash
python -m cyberant.operations init --target /var/lib/cyberant
python -m cyberant.operations check
```

Bỏ secret bootstrap sau init. Chỉ tạo admin, không tạo tài khoản mẫu/mật khẩu rõ.
Server sẽ báo lỗi nếu layout/schema thiếu, không tự tạo DB trống.

## 3. Chạy

Luồng private ZIP và cấu hình LAN/firewall chi tiết ở README. Dùng Python hiện có:

```bash
cd /opt/cyberant
python main.py
```

Config development dùng loopback; LAN đặt APP_ENV=lan, APP_HOST là IP LAN server,
APP_ORIGINS đúng URL IP:port, firewall chỉ cho subnet cần dùng vào port. HTTP LAN
không mã hóa, app không nhận biết SSID. Không port forwarding/tunnel public hoặc
origin wildcard. start.sh chỉ là launcher Conda có sẵn, không bắt buộc.
Không chạy service/manual cùng
lúc trên một thư mục data. Luôn một worker, local disk, DELETE journals.

## 4. Service chạy nền

Sửa `/opt/cyberant/deploy/cyberant.service.example`: user, WorkingDirectory,
Python hiện có tuyệt đối, APP_ENV_FILE trỏ config thật (.env gói hoặc external file).
Service đọc cùng LAN config, dùng Python env trực tiếp, không cần activate Conda
và không tự install dependencies. Không chạy nhiều instance.

```bash
sudo cp /opt/cyberant/deploy/cyberant.service.example /etc/systemd/system/cyberant.service
sudo systemctl daemon-reload
sudo systemctl enable --now cyberant
sudo journalctl -u cyberant -n 100 --no-pager
sudo systemctl stop cyberant
```

Giữ IP server ổn định bằng DHCP reservation. systemd dừng nhóm app; timeout stop đủ cho
request đang chạy. Không kill -9 trừ khẩn cấp; usage có thể chuyển uncertain.
Nginx chỉ là ví dụ tùy chọn cho HTTPS nội bộ, không bắt buộc cho LAN tin cậy.

## 5. Backup/restore

Admin có nút sao lưu tạo bộ DB/manifest/checksum tại `APP_BACKUP_DIR`. Khóa ghi
bao phủ mọi connection trong suốt snapshot. Backup không tự chứa API key/corpus
source/code: lưu các phần này riêng, có phiên bản và quyền hạn chế.

CLI offline yêu cầu dừng app trước (instance lock):

```bash
python -m cyberant.operations backup --target /var/backups/cyberant/20261002-manual
python -m cyberant.operations restore \
  --source /var/backups/cyberant/20261002-manual --target /var/lib/cyberant-restored
```

Restore chỉ tới đích mới, kiểm checksum/integrity, thu hồi phiên. Đổi APP_DATA_DIR
sang bộ restored khi app dừng. Không merge DB hoặc restore từng kho riêng lẻ.
Thử restore định kỳ vào thư mục cách ly; sao lưu off-host mã hóa theo chính sách.
Rotation backup/log cần đặt theo nhu cầu đơn vị, không tự xóa bản cũ trong source.

## 6. Cập nhật và rollback

1. Đợi request xong, backup bộ dữ liệu/cấu hình, giữ code/lockfile cũ.
2. Dừng service. Cập nhật source-only; không rsync --delete vào data/config.
3. Cài dependency khi lockfile đổi. Chạy `operations check`.
4. Chạy app; kiểm `/api/health`, `/api/ready`, login, quyền, lịch sử, model/quota,
   tri thức upload/retired, phản hồi, backup. Corpus mới sync bằng admin có chủ đích.
5. Rollback phải dừng app, giữ bộ dữ liệu mới, khôi phục code + bộ backup cùng
   phiên bản. Usage phát sinh sau backup cần đối soát OpenRouter; restore không
   hoàn lại chi phí provider. Không dùng code cũ ghi vào bộ DB mới.

## Giới hạn xác minh

Kiểm thử phát triển chạy Windows/Python 3.13 với provider giả. Linux Conda, quyền
POSIX, systemd, firewall/subnet và truy cập Wi-Fi phải smoke test trên server thật.
Chạy LAN không thay chứng minh an toàn mạng hoặc HTTPS khi cần.