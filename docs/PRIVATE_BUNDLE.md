# Gói chuyển máy riêng tư

Gói private có source/corpus, `.env`, `data/layout.json` và đủ sáu database layout v1.
Nó chứa API key, password hash, tài khoản, lịch sử và usage: **ZIP không mã hóa**.
Không commit, upload public hoặc gửi qua kênh không tin cậy. Giữ quyền owner-only;
chuyển qua SSH/SFTP hoặc kênh riêng được phép. Không chạy hai bản cùng lúc nếu
không muốn cùng key/quota nhà cung cấp bị sử dụng độc lập bởi hai máy.

## Tạo gói (trên máy nguồn)

Chờ request hoàn tất và dừng đúng app. Công cụ từ chối runtime đang bị lock hoặc
còn usage reserved/sent. Dùng Python hiện có, không tạo environment mới:

```powershell
python -B D:\TestSystem\tools\package_server.py --output D:\CyberAnt-private\transfer-new.zip --private-runtime D:\TestSystem\data --env-file D:\TestSystem\.env
```

Không ghi đè output đã có. SQLite backup/restore tạo snapshot sáu kho; chỉ bản
copy bị thu hồi session, mọi tài khoản/chat/usage vẫn giữ. Không đưa log, PID,
lock, backup cũ hay initial-accounts vào ZIP. `.env` nguồn không thay đổi;
chỉ bản trong ZIP đổi APP_DATA_DIR=data và APP_BACKUP_DIR=../CyberAnt-private/backups.
Giữ nguyên API key, model, budget và cấu hình mạng. Biến process env không tự
được ghi vào gói; máy đích cần bỏ override APP_ENV_FILE/APP_DATA_DIR cũ.

## Chạy trên máy đích

Giải nén vào thư mục riêng **mới**, không đè data của hệ thống đang hoạt động.
Trên Linux đặt quyền thư mục riêng 700, `.env` và database 600. Dùng interpreter
đã có với dependencies trong requirements-lock.txt; không chạy `operations init`
hoặc migrate lại vì database đã có sẵn. Từ thư mục giải nén:

```text
python -m cyberant.operations check
python main.py
```

Mặc định gói hiện tại vẫn chạy loopback http://127.0.0.1:8088; đăng nhập bằng tài
khoản hiện có, session cũ không dùng được. Internet, key hợp lệ và số dư/rate
limit provider vẫn cần cho generation. Có .env/DB không thay thế Python/dependency.
Muốn các thiết bị cùng LAN/Wi-Fi truy cập, làm theo README: APP_ENV=lan,
APP_HOST là IP LAN server và APP_ORIGINS chứa đúng URL IP:port, firewall chỉ
cho subnet tin cậy. Không mở port forwarding/tunnel. ZIP giữ loopback vì chưa
biết IP máy đích; chỉ sửa mạng trong .env máy đích, không thay API key/dữ liệu.
Linux/systemd/firewall cần kiểm trên máy đích; `python main.py` không yêu cầu Conda.

Gói source-only mặc định vẫn không có secret/DB, dùng cho cài mới hoặc cập nhật
source mà không ghi đè runtime. Private bundle là snapshot chuyển máy, không
phải gói public và không phải bản cập nhật để đè hệ thống đang chạy.