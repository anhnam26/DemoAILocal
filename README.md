# CyberAnt — chạy server trong mạng nội bộ

FastAPI, HTML/CSS/JavaScript thuần, RAG trên CPU và OpenRouter. Chạy trực tiếp
bằng **Python trên Linux hoặc Windows**, không Docker/GPU/model local. Thiết bị trong
mạng LAN/Wi-Fi được phép mở trình duyệt tới IP server và đăng nhập. Không tạo link
public/tunnel. `python main.py` không bắt buộc Conda.

> Gói private có `.env` và sáu database chứa API key, tài khoản, lịch sử, không mã
> hóa: chỉ chuyển qua kênh riêng, không upload public. Server vẫn cần Internet/API
> key hợp lệ để gọi OpenRouter. LAN không biến AI thành mô hình offline.

## Cấu trúc

- `cyberant/`: backend, cấu hình, tài khoản, hội thoại, usage, tri thức, vận hành.
- `static/`: giao diện và tài sản đang sử dụng.
- `knowledge/manifest.json` + `knowledge/documents/A…F/`: nguồn tri thức/checksum.
- `main.py`, `start.sh`: entrypoint và launcher Conda.
- `deploy/`: service Linux, reverse proxy tùy chọn.
- `tools/`: đóng gói server và audit tri thức read-only.
- `tests/`: kiểm thử offline, không gọi model thật.
- `docs/`: hướng dẫn vận hành hiện tại.

## 1. Đưa gói chuyển máy lên server

Chuyển ZIP private qua SSH/SFTP hoặc kênh riêng, giải nén vào **thư mục mới**.
Ví dụ Linux `/opt/cyberant`, Windows `D:\CyberAnt`; thay bằng vị trí thật.
Gói đã có `.env`, `data/layout.json` và sáu kho SQLite: **không chạy init/migrate
lại, không đè data hệ thống đang hoạt động, không chép .env.example đè .env**.
Giữ API key/model/budget và tài khoản/mật khẩu có sẵn; session cũ đã bị thu hồi
khi đóng gói nên đăng nhập lại. Gói là snapshot, không nhận các ghi mới máy nguồn.

Chạy bằng tài khoản thường sở hữu thư mục, không root/Administrator. Linux cần
quyền ghi data và thư mục backup ngoài project. Sau khi quyền sở hữu đã đúng:

```bash
cd /opt/cyberant
chmod 700 . data
find data -type d -exec chmod 700 {} +
find data -type f -exec chmod 600 {} +
chmod 600 .env
```

Windows giữ ACL riêng cho tài khoản chạy app và SYSTEM; không dùng thư mục chia sẻ
công khai. Không upload toàn folder làm web root.

## 2. Chuẩn bị Python có sẵn

Từ thư mục giải nén, dùng interpreter/environment **đã có**, không tạo env mới:

```text
python --version
python -c "import sys; print(sys.executable)"
python -m pip install -r requirements-lock.txt
```

Đã kiểm phát triển Python 3.13/Windows; dependency lock cần kiểm trên Linux/máy đích.
Nếu có Conda, activate environment đang dùng rồi chạy Python như bình thường.

## 3. Tìm IP LAN server và sửa `.env`

Server có thể nối router bằng Wi-Fi hoặc dây LAN; thiết bị khách phải có đường
truy cập đến server trong mạng được phép.

- Linux: `ip -4 addr show` và `ip route`, chọn IP trên card nối mạng nội bộ,
  không chọn `127.0.0.1`, IP Docker/VPN hoặc IP public.
- Windows: `ipconfig`, xem IPv4/Subnet Mask của Wi-Fi/Ethernet đang dùng.
- Nên đặt **DHCP reservation** trên router để IP không đổi. Đổi IP/port thì cập
  nhật `.env`, firewall, URL truy cập rồi restart app.

**Ví dụ** IP server `192.168.1.100`, mask `255.255.255.0`, subnet `192.168.1.0/24`.
Thay IP/subnet bằng giá trị thật. Mở `.env` trên server và sửa **bốn biến mạng**:

```dotenv
APP_ENV=lan
APP_HOST=192.168.1.100
APP_PORT=8088
APP_ORIGINS=http://192.168.1.100:8088
```

Giữ data paths portable của private ZIP:

```dotenv
APP_DATA_DIR=data
APP_BACKUP_DIR=../CyberAnt-private/backups
```

`APP_HOST` là IP card LAN **server**, không phải IP điện thoại; phải có trên server.
Bind đúng IP tránh lắng nghe mọi card như `0.0.0.0`. `APP_ORIGINS` là URL chính xác
trình duyệt mở, không path/wildcard/dấu `/` cuối; không dùng `0.0.0.0` làm URL.
ZIP giữ loopback cho tới khi bạn cấu hình IP thật. Development chỉ local; production
yêu cầu HTTPS, không dùng cho ví dụ HTTP LAN này. Không đổi API key/model/budget.

Process environment ghi đè file, CLI host/port ghi đè chúng. Dọn override cũ hoặc
bảo đảm chúng khớp `.env`. APP_ENV_FILE chỉ dùng khi chủ động lưu config ngoài project,
không đặt trong chính file config. Nếu dùng `.env` gói nhưng terminal trỏ config cũ:

```bash
# Linux — bỏ các override mạng/data cũ nếu có; kiểm cả Environment của service:
unset APP_ENV_FILE APP_DATA_DIR APP_BACKUP_DIR APP_ENV APP_HOST APP_PORT APP_ORIGINS
```

```powershell
# Windows PowerShell — không in API key ra màn hình:
'APP_ENV_FILE','APP_DATA_DIR','APP_BACKUP_DIR','APP_ENV','APP_HOST','APP_PORT','APP_ORIGINS' |
    ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
```

## 4. Giới hạn firewall chỉ cho mạng cần dùng

**Host/Origin không thay firewall.** Không port forwarding/NAT, DMZ hoặc tunnel
public trên router. Chỉ cho subnet cần dùng vào TCP `8088` trên server; không tắt
firewall hoặc mở port từ mọi nguồn. Ví dụ dưới dùng IP/subnet ở phần 3.

### Linux có UFW sẵn

Dùng quyền quản trị hệ điều hành. Kiểm rule hiện tại, giữ SSH quản trị được phép
trước khi bật/thay firewall; không cài/đổi firewall manager chỉ vì ví dụ này.

```bash
sudo ufw status numbered
# Rule 1 cho đúng subnet tới IP LAN; rule 2 chặn nguồn khác vào 8088:
sudo ufw insert 1 allow from 192.168.1.0/24 to 192.168.1.100 port 8088 proto tcp
sudo ufw insert 2 deny 8088/tcp
sudo ufw status numbered
```

Rule chỉ có tác dụng khi UFW active. Nếu inactive, chuẩn bị rule SSH/quản trị và
kiểm tác động trước `sudo ufw enable`, tránh tự khóa SSH. Nếu dùng firewalld/nftables
hoặc manager khác, cấu hình tương đương trên firewall đang dùng, không chồng manager.
Kiểm cả IPv6/VPN/routing và rule sẵn có. Ví dụ app bind một IP IPv4 LAN cụ thể.

### Windows Firewall — PowerShell Administrator

Mạng tin cậy cần profile **Private**, không đánh dấu mạng công cộng thành Private.
Firewall phải bật và mặc định chặn inbound không có rule cho phép:

```powershell
Get-NetConnectionProfile
Get-NetFirewallProfile -Name Private | Select-Object Enabled,DefaultInboundAction
New-NetFirewallRule -DisplayName 'CyberAnt LAN 8088' -Direction Inbound -Action Allow `
    -Protocol TCP -LocalAddress 192.168.1.100 -LocalPort 8088 `
    -RemoteAddress 192.168.1.0/24 -Profile Private
```

Kiểm và thu hẹp/tắt **rule Allow cũ mở Python/8088 từ mọi nguồn** nếu có; rule mới
không vô hiệu hóa rule rộng khác. Nếu không có Private/default inbound chặn, xử lý
theo chính sách máy/đơn vị trước, không tắt firewall để sửa lỗi.

> “Cùng Wi-Fi” ở đây là cùng mạng/subnet được phép. App không nhận biết SSID;
> thiết bị cắm dây cùng subnet cũng có thể truy cập. Chỉ một SSID thì cần VLAN/ACL
> router/AP. Guest Wi-Fi hoặc AP/client isolation có thể chặn dù cùng router.
> VPN/routing cần kiểm ở firewall/router. HTTP LAN không mã hóa mật khẩu/lưu lượng:
> chỉ dùng mạng tin cậy; mạng không tin cậy cần HTTPS nội bộ trước khi dùng dữ liệu nhạy cảm.

## 5. Kiểm database, chạy và dừng

Từ thư mục project, tài khoản thường:

```text
python -m cyberant.operations check
python main.py
```

Check CLI cần runtime lock riêng, không chạy khi app đang hoạt động. Một process/
một worker; không chạy service/launcher/manual đồng thời trên cùng data, không NFS.
Sau startup, kiểm từ server bằng IP đã bind, không `localhost`:

```text
http://192.168.1.100:8088/api/health
http://192.168.1.100:8088/api/ready
```

Ready phải trả `{"status":"ready","layout_version":1}`. Giữ terminal mở để chạy
foreground. Dừng bằng **Ctrl+C**, chờ shutdown/request hoàn tất. Không kill -9/
terminate khi AI đang chạy nếu không khẩn cấp; usage có thể cần đối soát.

### Chạy nền Linux (tùy chọn)

Sửa `deploy/cyberant.service.example`: user, WorkingDirectory, ExecStart dùng Python
**hiện có** (xem sys.executable), `Environment=APP_ENV_FILE=/opt/cyberant/.env` nếu
dùng config gói. Không giữ đường dẫn Conda/config ví dụ nếu máy bạn khác. User service
cần quyền ghi data/parent backup. Dừng foreground trước:

```bash
sudo cp /opt/cyberant/deploy/cyberant.service.example /etc/systemd/system/cyberant.service
sudo systemctl daemon-reload
sudo systemctl enable --now cyberant
sudo systemctl status cyberant --no-pager
sudo journalctl -u cyberant -n 100 --no-pager
# Dừng để bảo trì/backup CLI:
sudo systemctl stop cyberant
```

`start.sh` chỉ là launcher Conda **đã có**, không bắt buộc. Windows dùng `python main.py`
trong gói; checkout có Start-App.ps1/Stop-App.ps1 chạy nền local, không trong ZIP runtime.

## 6. Điện thoại/máy tính cùng mạng truy cập

1. Nối vào LAN/Wi-Fi được phép, không 4G/5G hoặc Guest Wi-Fi bị cô lập; server đang chạy.
2. Mở **http://192.168.1.100:8088** (thay IP thật). Localhost/127.0.0.1 trên điện thoại
   trỏ điện thoại, không server.
3. Đăng nhập tài khoản có sẵn. Quyền/model/quota vẫn do admin quản lý.

| Lỗi | Kiểm tra |
|---|---|
| Cannot listen | APP_HOST/IP server đổi/sai, port bị chiếm |
| Development phải loopback | APP_ENV=lan, bỏ override cũ rồi restart |
| Server mở được, thiết bị khác timeout | Firewall/subnet/profile Private, isolation, Guest Wi-Fi, VLAN/VPN |
| Host denied / Origin denied | URL/IP/port khớp APP_ORIGINS; không dùng wildcard |
| Thiếu layout/store | Đủ sáu DB/layout, APP_DATA_DIR đúng; không init đè data |
| Data in use | Dừng instance cũ, một worker/một bộ DB |
| UI chạy, AI lỗi | Internet, key/số dư/rate limit/model/quota; kiểm usage trước gửi lại |

## Cài mới hoặc dữ liệu legacy — không áp dụng cho private ZIP đã có DB

Nếu chỉ có source, tạo config từ .env.example, điền API key/model, cấu hình LAN ở
phần 3, chọn APP_DATA_DIR=data **chưa tồn tại**. Đặt BOOTSTRAP_ADMIN_PASSWORD 14–128
ký tự rồi `python -m cyberant.operations init --target data`; bỏ secret bootstrap sau
init. Admin đồng bộ tri thức có chủ đích; server không tự init/migrate/sync startup.
Layout v1 dùng backup/restore; chỉ migrate DB legacy theo docs/DEPLOYMENT.md.

## Dữ liệu không còn nằm trong một tệp

Dữ liệu runtime ở APP_DATA_DIR, gói private mặc định dùng `data/`, backup ngoài
project. ZIP source-only không có .env/data; private ZIP có đủ sáu DB/.env, phải
giữ bí mật. Backup CLI dừng app, restore vào đích mới,
không copy SQLite đang ghi hoặc restore từng kho riêng.

Các đường dẫn dưới `APP_DATA_DIR`:

| Kho | Nội dung |
|---|---|
| `auth/auth.sqlite3` | Tài khoản, hash mật khẩu, phiên, quyền model, hạn mức/usage |
| `users/users.sqlite3` | Hồ sơ người dùng, không chứa mật khẩu |
| `conversations/conversations.sqlite3` | Hội thoại, tin nhắn, phản hồi |
| `knowledge/knowledge.sqlite3` | Tri thức đã nhập, upload, duyệt/thu hồi |
| `audit/audit.sqlite3` | Nhật ký quản trị |
| `archive/archive.sqlite3` | Bảng nghiệp vụ cũ được bảo toàn khi migration |

Tài khoản/hồ sơ liên kết bằng ID. Usage ở cùng auth để kiểm quyền/dự trữ ngân sách
nhất quán; xóa chat không xóa usage. **DELETE journals + FULL synchronous, không WAL.**
Một process/một worker, đĩa local, không NFS. Xem `docs/DATA_LAYOUT.md`.

## Tri thức và AI

1.200 tài liệu nhóm A–F, 1.100 draft đã accepted cho knowledge use trong acceptance.
Accepted không phải xác minh nội dung/lệnh/firmware bởi kỹ sư. Không nhập hồ sơ
khách hàng. Upload TXT/MD/PDF có text chờ admin duyệt.

Sửa nguồn phải cập nhật checksum/danh mục trong manifest. Thiếu/hỏng nguồn làm
đồng bộ thất bại trước khi ghi; đồng bộ bằng chức năng admin, không tự chạy startup.
RAG theo intent/configured caps, tối đa 24 nguồn, không gửi cả kho/toàn bộ lịch sử. SOW/BOM
ưu tiên bằng chứng cùng dịch vụ; chọn cách trình bày Sales/Kỹ sư, không đổi quyền.
Xem `docs/SERVICE_RAG.md` về coverage, audit read-only và đánh giá offline.
`RAG_INPUT_BYTES` là byte UTF-8, **không phải tokenizer**; tên cũ `RAG_INPUT_TOKENS`
vẫn hỗ trợ. Usage provider là số liệu thực. Kiểm ID trích dẫn không chứng minh
ngữ nghĩa câu trả lời. Không tự retry/đổi model. Usage chưa rõ phải đối soát.

## Kiểm thử và đóng gói

```bash
# Chạy từ checkout phát triển, không phải gói runtime giải nén:
python -m unittest discover -s tests -v
python tools/package_server.py --list
python tools/package_server.py --output /tmp/cyberant-server.zip
```

Test dùng dữ liệu tạm/provider giả lập. Browser cần Playwright/Chromium trong môi
trường phát triển, không phải dependency runtime. Gói server dùng allowlist,
source-only mặc định không chứa `.env`, DB, log, `.git`, venv, test hoặc artifacts.
Private mode chỉ rõ runtime đã dừng/env file, có secrets và sáu DB; xem PRIVATE_BUNDLE.md.
Không upload toàn bộ folder làm web root.
Gói runtime dùng danh sách module/static rõ ràng và corpus theo manifest/checksum;
không kèm tools/test/evaluation fixtures. Audit trong SERVICE_RAG.md chạy từ checkout
phát triển; không cần tải công cụ biên soạn lên server.

## Tài liệu

- `docs/DEPLOYMENT.md`: cài đặt, service, cập nhật, backup/rollback.
- `docs/PRIVATE_BUNDLE.md`: gói riêng chuyển máy có .env/sáu DB.
- `docs/DATA_LAYOUT.md`: cấu trúc dữ liệu, giao dịch và migration.
- `docs/CONVERSATION_WEB.md`: bộ nhớ trong chat, kiến thức chung, nguồn Internet và phí.
- `SECURITY.md`: phạm vi bảo vệ.

Linux/systemd/firewall và truy cập từ điện thoại thật cần kiểm trên máy đích;
test phát triển offline không chứng minh router đã giới hạn truy cập đúng.