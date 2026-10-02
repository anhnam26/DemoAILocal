# CyberAnt — tra cứu tri thức nội bộ

FastAPI, HTML/CSS/JavaScript thuần, RAG trên CPU và OpenRouter. Chạy trực tiếp
bằng **Linux + Miniconda + Cloudflare Quick Tunnel**, không Docker/GPU/model local.

## Cấu trúc

- `cyberant/`: backend, cấu hình, tài khoản, hội thoại, usage, tri thức, vận hành.
- `static/`: giao diện và tài sản đang sử dụng.
- `knowledge/manifest.json` + `knowledge/documents/A…F/`: nguồn tri thức/checksum.
- `main.py`, `start.sh`: entrypoint và launcher Conda.
- `deploy/`: service Linux, reverse proxy tùy chọn.
- `tools/`: đóng gói server và chuyển nguồn tri thức cũ.
- `tests/`: kiểm thử offline, không gọi model thật.
- `docs/`: hướng dẫn hiện tại; `docs/archive/` là báo cáo lịch sử, không dùng để cài đặt.

## Bắt đầu trên Linux

Ví dụ source `/opt/cyberant`, config `/etc/cyberant/cyberant.env`. Thay đường dẫn
bằng vị trí thực tế. Không chạy app bằng root, không ghi đè config/dữ liệu đang dùng.

```bash
conda create -n cyberant python=3.14 pip -y
conda activate cyberant
cd /opt/cyberant
python -m pip install -r /opt/cyberant/requirements-lock.txt
export APP_ENV_FILE=/etc/cyberant/cyberant.env
```

Tạo config từ `.env.example` chỉ khi chưa có, điền API key/model,
đặt `APP_DATA_DIR=/var/lib/cyberant`. Config mode 600, thư mục dữ liệu 700.

### Giữ dữ liệu cũ

Dừng instance cũ, chuyển snapshot SQLite nhất quán qua kênh bảo mật.
Đích phải **chưa tồn tại**. Migration không sửa DB nguồn, không cần bootstrap.

```bash
python -m cyberant.operations migrate \
  --source /srv/cyberant-import/app.sqlite3 --target /var/lib/cyberant
python -m cyberant.operations check
```

### Cài mới

Đặt `BOOTSTRAP_ADMIN_PASSWORD` 14–128 ký tự trong config riêng rồi chạy:

```bash
python -m cyberant.operations init --target /var/lib/cyberant
```

Bỏ mật khẩu bootstrap khỏi config sau init. Không sinh tệp mật khẩu plaintext.
Server không tự init/migrate DB hoặc đồng bộ tri thức khi khởi động/import.

### Chia sẻ tạm thời

Cài cloudflared từ nguồn chính thức theo `docs/PUBLIC_SHARE.md` rồi chạy:

```bash
bash /opt/cyberant/start.sh --share
```

Terminal in URL HTTPS, đăng nhập bắt buộc; Ctrl+C đóng app/tunnel.
URL thay đổi mỗi lần chạy, không SLA, request AI dài có thể timeout.
Không mở cổng 8088 ra Internet. Có thể chạy nền bằng service mẫu.

## Dữ liệu không còn nằm trong một tệp

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

1.200 tài liệu theo nhóm A–F, 1.100 mang nhãn `draft_engineer_review`.
Chuẩn hóa không xác minh nội dung kỹ thuật hoặc nâng nhãn duyệt. Không nhập hồ sơ
khách hàng. Upload TXT/MD/PDF có text chờ admin duyệt.

Sửa nguồn phải cập nhật checksum/danh mục trong manifest. Thiếu/hỏng nguồn làm
đồng bộ thất bại trước khi ghi; đồng bộ bằng chức năng admin, không tự chạy startup.
RAG chọn tối đa 6 đoạn theo cấu hình, không gửi cả kho/toàn bộ lịch sử. SOW/BOM
ưu tiên bằng chứng cùng dịch vụ; chọn cách trình bày Sales/Kỹ sư, không đổi quyền.
Xem `docs/SERVICE_RAG.md` về coverage, audit read-only và đánh giá offline.
`RAG_INPUT_BYTES` là byte UTF-8, **không phải tokenizer**; tên cũ `RAG_INPUT_TOKENS`
vẫn hỗ trợ. Usage provider là số liệu thực. Kiểm ID trích dẫn không chứng minh
ngữ nghĩa câu trả lời. Không tự retry/đổi model. Usage chưa rõ phải đối soát.

## Kiểm thử và đóng gói

```bash
python -m unittest discover -s /opt/cyberant/tests -v
python /opt/cyberant/tools/package_server.py --output /tmp/cyberant-server.zip
```

Test dùng dữ liệu tạm/provider giả lập. Browser cần Playwright/Chromium trong môi
trường phát triển, không phải dependency runtime. Gói server dùng allowlist,
không chứa `.env`, DB, log, `.git`, venv, test hoặc artifacts. DB/config chuyển riêng.
Không upload toàn bộ folder làm web root.

## Tài liệu

- `docs/DEPLOYMENT.md`: cài đặt, service, cập nhật, backup/rollback.
- `docs/PUBLIC_SHARE.md`: Quick Tunnel, quyền riêng tư, giới hạn.
- `docs/DATA_LAYOUT.md`: cấu trúc dữ liệu, giao dịch và migration.
- `SECURITY.md`: phạm vi bảo vệ.

Windows dùng phát triển: venv + `Start-App.ps1`/`Stop-App.ps1`.
Đổi `APP_DATA_DIR` sang dữ liệu đã init/migrate trước khi chạy. DB cũ tại
`data/app.sqlite3` được giữ nguyên, không tự chuyển đổi.