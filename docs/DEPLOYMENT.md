# Triển khai trực tiếp — `.env` server, LAN hoặc chia sẻ HTTPS tạm thời

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
Nếu không đặt biến này, đọc `.env` ở root source, không phụ thuộc working directory.
Không copy `.env.example` đè server có sẵn, không `source .env` trong shell.
Khi file không tồn tại/mode không hợp lệ, sửa cấu hình thật thay vì dùng network defaults.
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

### Chia sẻ công khai tạm thời trên Linux

Sau khi dừng service/instance cũ, kiểm `cloudflared --version`, quyền .env/data,
tài khoản admin và dùng đúng environment đã có:

```bash
cd /home/cba/Chatbot2/TestSystem  # thay bằng source root thật
bash start.sh --share
# Hoặc nếu QUIC bị chặn:
bash start.sh --share --share-protocol http2
```

Không cần đổi APP_ORIGINS sang URL ngẫu nhiên trước chạy. Runtime share override
bind/security/origin nhưng giữ port/API key/model/data/quota/usage của server.
Không mở port app inbound; chỉ gửi link khi đã thấy `Public URL` và đăng nhập.
Xem `PUBLIC_SHARE.md`. Quick Tunnel không SLA, không cho production ổn định.
Nếu chọn service share, thêm --share vào ExecStart và có thể --share-protocol http2;
cân nhắc Restart=no vì on-failure sẽ tạo URL mới. Dừng service trước chạy manual.

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

**Với server đang có dữ liệu:** dùng source-only, không dùng private ZIP snapshot
để upgrade. Không chuyển `.env` máy Windows, `data`, logs, PID/lock hoặc backup lên
đè server. Giữ nguyên file server và APP_ENV_FILE đang sử dụng.

Patch tối thiểu cho share cần cập nhật đồng bộ `main.py`, `start.sh`,
`cyberant/config.py`, và thêm `cyberant/public_share.py`; chép docs mới nếu cần.
Giữ provider fixes hiện có: `cyberant/provider_errors.py`, `cyberant/model_provider.py`,
`cyberant/app.py`. Nếu server trước checkpoint provider, nâng source-only đồng bộ
thay vì chỉ thêm share rồi bỏ mất diagnostics. Dependency lock không đổi trong đợt này.

Trình tự trên server (không xóa/reinitialize runtime):

1. Chờ AI xong, dừng phiên Ctrl+C hoặc service. Backup cấu hình và bộ DB bằng
   operations backup vào đích private mới; giữ source cũ để rollback.
2. Chép code mới; không rsync --delete và không copy .env.example đè .env.
3. Kiểm Python hiện có, chạy `python -m cyberant.operations check` ở source root
   bằng cùng environment/config; `bash -n start.sh`; `cloudflared --version` nếu share.
4. Chạy thường hoặc share, không hai phiên. Kiểm ready/login/lịch sử/quyền/models/
   quota/usage; tránh gọi chat trả phí chỉ để smoke test. Với share dùng HTTPS URL mới.

Nếu cấu hình hiện tại là `APP_ENV=development`, `APP_HOST=0.0.0.0`, muốn LAN:
chỉ đổi mode thành lan và APP_ORIGINS thành các **URL private/loopback thật**.
Giữ port và bind hiện có nếu firewall phù hợp (hoặc bind đúng IP private để hẹp hơn);
loại IP public HTTP khỏi origins. Không xóa origins validation. Nếu muốn public,
chọn --share thay vì mở HTTP public. Không khẳng định .env máy dev trùng .env server.

1. Đợi request xong, backup bộ dữ liệu/cấu hình, giữ code/lockfile cũ.
2. Dừng service. Cập nhật source-only; không rsync --delete vào data/config.
3. Cài dependency khi lockfile đổi. Chạy `operations check`.
4. Chạy app; kiểm `/api/health`, `/api/ready`, login, quyền, lịch sử, model/quota,
   tri thức upload/retired, phản hồi, backup. Corpus mới sync bằng admin có chủ đích.
5. Rollback phải dừng app, giữ bộ dữ liệu mới, khôi phục code + bộ backup cùng
   phiên bản. Usage phát sinh sau backup cần đối soát OpenRouter; restore không
   hoàn lại chi phí provider. Không dùng code cũ ghi vào bộ DB mới.

## 7. Chat lỗi OpenRouter (503/504)

`GET /api/model` hoặc `/api/ready` trả 200 chỉ xác nhận trạng thái nội bộ, không
kiểm kết nối/key/model OpenRouter. Dòng access log `POST /api/chat ... 503` không
phải nguyên nhân gốc và không nhất thiết là HTTP 503 do OpenRouter trả về.

Khi lỗi, chat hiển thị **Mã lỗi**; tìm cùng `error_id` trong dòng JSON có
`event="provider_failure"` trên terminal chạy app hoặc journal của service:

```bash
sudo journalctl -u cyberant -n 100 --no-pager
```

Log chỉ chứa loại exception, model, stage (`completion`/`web_lookup`), thời gian,
HTTP status nếu có và ID bản ghi usage; cùng metadata lưu trong audit. Không ghi
API key, cookie, prompt, raw exception hoặc response body. Giữ log nội bộ vì vẫn
có metadata vận hành. Không bật debug HTTP/raw headers để tìm lỗi.

| `kind` | Cách kiểm tra |
|---|---|
| `connection_error` | Kết nối thất bại; kiểm DNS, chứng chỉ TLS/giờ server, outbound TCP 443, proxy bắt buộc |
| `http_timeout` | Connect/read/write/pool timeout (HTTP ứng dụng 504); xem `exception_type`, thời gian và trạng thái mạng/provider |
| `transport_error` | Gửi/nhận bị ngắt hoặc lỗi giao thức; kiểm đường mạng, proxy và provider |
| `deadline_exceeded` | Hết thời gian tổng cho các stage (HTTP ứng dụng 504), không tự tăng timeout hoặc gửi lại |
| `invalid_json` | Phản hồi không đọc được thành JSON; kiểm provider/gateway, không log raw body |
| `invalid_response` | JSON/cấu trúc nội dung không hợp lệ; kiểm model/provider, usage vẫn được giữ nếu có |
| `empty_content` | Model không trả nội dung, có thể vẫn tính token/phí; kiểm usage |
| `http_status` | Xem `http_status`: 401 key, 402 số dư, 429 giới hạn; các status khác cần kiểm model/provider |

Kiểm HTTPS cơ bản trên **chính server**, bằng Python environment đang chạy app:

```bash
python -B -c "import httpx; r=httpx.get('https://openrouter.ai/api/v1/models', timeout=httpx.Timeout(20, connect=15), trust_env=False); print('HTTP:', r.status_code); print('Content-Type:', r.headers.get('content-type'))"
```

Lệnh GET catalog công khai không gửi key/prompt và không yêu cầu generation. HTTP
200 chỉ chứng minh kết nối catalog tại thời điểm kiểm, không xác minh key, số dư
hoặc model completion. Nếu lỗi, gửi loại exception cuối sau khi che secret.
Ứng dụng dùng `trust_env=False`: không tự đọc proxy/CA từ environment. Nếu mạng
bắt buộc proxy/TLS inspection, cần cấu hình có chủ đích sau khi xác minh; không
tắt kiểm chứng TLS (`verify=False`) hoặc tự bật proxy toàn bộ.

Không tự retry/đổi model. Lượt gửi thất bại có thể vẫn tính phí: kiểm usage và đối
soát OpenRouter trước khi gửi lại; không tự giải phóng usage `uncertain`. Usage
đã đo được vẫn ghi nhận kể cả nội dung rỗng/sai cấu trúc. Các HTTP rejection giữ
chính sách settlement hiện có.

### Cập nhật bản chẩn đoán vào server đang có dữ liệu

Thay `/opt/cyberant` bằng **đường dẫn tuyệt đối** của app thật. Đợi chat hoàn tất,
sao lưu dữ liệu/cấu hình theo mục 5 rồi dừng app (Ctrl+C nếu chạy `bash start.sh`,
hoặc `systemctl stop` nếu dùng service). Giữ bản code cũ để rollback.

Chuyển các file đã kiểm thử qua SSH/SFTP và cập nhật **cùng lúc**:

- `/opt/cyberant/cyberant/app.py`
- `/opt/cyberant/cyberant/model_provider.py`
- `/opt/cyberant/cyberant/provider_errors.py` (file mới, bắt buộc)

Đây là bản vá code, không đổi schema/dependency. Không chép `.env`, `data/` hoặc
corpus từ một snapshot khác; không init/migrate. Nếu dùng ZIP source-only mới,
giải nén vào thư mục staging riêng và chỉ lấy ba file trên, không đè toàn bộ app.
Checkout đóng gói sau này cần cả allowlist mới trong `tools/package_server.py`.
Chạy `python -B -m cyberant.operations check` khi app đã dừng, khởi động lại đúng
environment/config cũ, kiểm ready/login. Bản vá giúp chẩn đoán, **không chứng minh
đã sửa được nguyên nhân mạng/provider trên server thật**. Thử chat thật có phí
do người vận hành quyết định; nếu lỗi, gửi dòng JSON cùng mã lỗi trong chat.

### IP công cộng trong access log

Các request IP công cộng trả 400 là request **đi vào ứng dụng**, không phải lỗi
OpenRouter. Có thể bị Host guard từ chối, nhưng access log không xác nhận lý do.
400 không thay firewall. Với launcher hiện tại `proxy_headers=False`, kiểm đường
NAT/port forwarding/DMZ/tunnel/reverse proxy và firewall subnet nếu thấy IP ngoài
LAN. Nếu dùng launcher khác/proxy headers, xác minh nguồn IP log trước khi kết
luận. Không thêm IP công cộng vào origins để bỏ lỗi; outbound OpenRouter vẫn cần
Internet trong khi inbound ứng dụng chỉ được phép từ LAN dự kiến.

## Giới hạn xác minh

Kiểm thử phát triển chạy Windows/Python 3.13 với provider giả. Linux Conda, quyền
POSIX, systemd, firewall/subnet và truy cập Wi-Fi phải smoke test trên server thật.
Chạy LAN không thay chứng minh an toàn mạng hoặc HTTPS khi cần.