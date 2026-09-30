# Triển khai server

**Chia sẻ Internet tạm thời, URL ngẫu nhiên không cần mua tên miền:** xem [PUBLIC_SHARE](PUBLIC_SHARE.md). Linux đã chuẩn bị có thể chạy `bash /opt/cyberant/start.sh --share`; phải dừng instance LAN/service dùng cùng DB trước. Đây không phải phương án production có SLA.

## Mạng LAN: server 192.168.1.50

Để chạy Python trực tiếp và truy cập từ các thiết bị cùng LAN, đặt trong `.env` trên server:

```dotenv
APP_HOST=0.0.0.0
APP_PORT=8088
APP_ENV=lan
APP_ORIGINS=http://192.168.1.50:8088,http://127.0.0.1:8088,http://localhost:8088
```

Sau khi đã cài môi trường `cyberant` và dependency (phần dưới), mỗi lần chỉ cần **`bash /opt/cyberant/start.sh`**, thay `/opt/cyberant` bằng thư mục source thực tế. Script tự activate Conda và chạy `python main.py --host 0.0.0.0 --port 8088`; gọi từ thư mục nào cũng được. Không cần chmod khi gọi qua Bash. Nếu Conda không được tìm thấy, dùng `CONDA_EXE=/duong/dan/miniconda3/bin/conda bash /opt/cyberant/start.sh`.

Script không tự cài package hoặc sửa `.env`. Cần tạo `.env` từ mẫu chỉ khi chưa có; giữ key/model cũ. Cài mới DB rỗng cần `BOOTSTRAP_ADMIN_USERNAME=admin` và `BOOTSTRAP_ADMIN_PASSWORD` từ 14–128 ký tự. Chế độ LAN/production bỏ qua file mật khẩu development và không sinh `initial-accounts.json`. DB đã có tài khoản không cần bootstrap; xóa secret khỏi cấu hình sau lần tạo admin.

Thiết bị khác mở **http://192.168.1.50:8088/** khi tiến trình hoạt động. Không mở `0.0.0.0`: đó là địa chỉ bind. HTTP LAN không mã hóa mật khẩu/cookie; chỉ dùng mạng tin cậy, không port-forward ra Internet. HTTPS phải dùng cấu hình production ở phần dưới.

Chạy trực tiếp chiếm terminal, dừng bằng Ctrl+C và chờ hoàn tất; không bảo đảm tiếp tục khi đóng SSH. Muốn chạy nền/tự khởi động thì dùng systemd. Có thể thêm `--host 127.0.0.1 --port 8090` sau lệnh script để ghi đè mặc định; phải chỉnh origin tương ứng.

Biến môi trường terminal/Conda ghi đè `.env`. Service mẫu mới để app đọc `.env`; nếu dùng service cũ có `Environment=APP_ENV=production`, bỏ dòng đó khi chuyển sang LAN rồi daemon-reload/restart. Không chạy đồng thời service và Python thủ công, kể cả ở hai cổng khác nhau nếu cùng DB.

Nếu UFW đang chặn và mạng LAN thực tế là `192.168.1.0/24`, cho phép bằng `sudo ufw allow from 192.168.1.0/24 to any port 8088 proto tcp`. Không cần port forwarding. IP server cần được giữ cố định hoặc đặt DHCP reservation trên router.

## Linux có Miniconda3: chạy bằng main.py

Ví dụ dưới đây dùng thư mục `/opt/cyberant`; thay bằng vị trí folder thực tế và chạy bằng tài khoản Linux có quyền đọc code/.env, ghi thư mục `data`.

```bash
conda create -n cyberant python=3.14 pip -y
conda activate cyberant
cd /opt/cyberant
python -m pip install -r requirements-lock.txt
```

Không cần Docker cho cách chạy này. Với LAN giữ cấu hình `APP_ENV=lan` ở đầu tài liệu. **Chỉ khi dùng reverse proxy HTTPS**, giữ key/model và chuyển sang cấu hình sau:

```dotenv
APP_ENV=production
APP_HOST=127.0.0.1
APP_PORT=8088
APP_ORIGINS=https://ai.example.com
```

`APP_ORIGINS` phải khớp tên miền HTTPS thực tế. Nginx trên cùng host chuyển tiếp đến `127.0.0.1:8088`; dùng mẫu `deploy/nginx.conf.example` sau khi cấp chứng chỉ. Bỏ `APP_DATA_DIR=/app/data` nếu đã sao chép cấu hình Docker: mặc định bản Python dùng `<thư mục dự án>/data`. Nếu cần dữ liệu ngoài source, đặt APP_DATA_DIR thành đường dẫn tuyệt đối phù hợp.

Giữ tài khoản cũ: dùng SQLite snapshot nhất quán (nút Hệ thống → Sao lưu), chép thành `data/app.sqlite3` trước lần chạy đầu tiên. Không copy đơn lẻ DB đang ghi WAL, không ghi đè DB deployment đang hoạt động. Không đưa `initial-accounts.json`, PID/log Windows hoặc môi trường Python Windows lên Linux. Nếu cài mới chưa có tài khoản, đặt BOOTSTRAP_ADMIN_PASSWORD ít nhất 14 ký tự; xóa biến này sau khi tạo admin thành công.

Chạy trực tiếp để kiểm tra:

```bash
python main.py
```

Ứng dụng phục vụ cả giao diện, API, tài khoản, kho tri thức và RAG trên cùng cổng; không cần một tiến trình frontend riêng. Chạy lệnh health trong terminal khác:

```bash
curl http://127.0.0.1:8088/api/health
```

Lệnh Python trực tiếp chiếm terminal. Trên server nên dùng service dưới đây để chạy nền và có lệnh stop, không phải Ctrl+C. Nếu đã chạy thử trực tiếp, kết thúc tiến trình đó trước khi bật service; không chạy hai bản cùng DB. `python main.py --help` xem tùy chọn host/port.

## Chạy nền bằng systemd và lệnh start/stop

Trên Linux có systemd, lấy đường dẫn Python sau khi activate Conda:

```bash
python -c "import sys; print(sys.executable)"
sudo cp deploy/cyberant.service.example /etc/systemd/system/cyberant.service
sudo nano /etc/systemd/system/cyberant.service
```

Thay `User=YOUR_LINUX_USER`, `WorkingDirectory=/opt/cyberant`, và cả hai đường dẫn trong `ExecStart=` bằng tài khoản/thư mục/Python thực tế. Tài khoản service phải có quyền ghi thư mục data. Dùng đường dẫn Python của env Conda nên service không cần gọi `conda activate`. Đường dẫn chứa dấu cách phải được đặt trong dấu nháy kép. App tự đọc `.env`; không ghi API key vào file service.

```bash
sudo systemctl daemon-reload
sudo systemctl start cyberant
sudo systemctl status cyberant --no-pager
```

Sau khi cấu hình một lần, dùng hai lệnh:

```bash
sudo systemctl start cyberant
sudo systemctl stop cyberant
```

Xem log: `sudo journalctl -u cyberant -n 100 --no-pager`. Khởi động lại sau chỉnh .env/code: `sudo systemctl restart cyberant`. Muốn tự chạy khi server boot: `sudo systemctl enable cyberant`.

Service gửi SIGTERM, cho phép tới 420 giây để tắt; Uvicorn đợi request tối đa 400 giây. DB và tài khoản không bị xóa. Chỉ một process/worker, không auto-reload. Đã kiểm entrypoint bằng môi trường Python 3.14 sạch trên Windows; chưa chạy Conda/systemd trên server Linux thực.

## Docker (tùy chọn): cấu hình

Compose chạy một process uvicorn, bind container 8088 nhưng chỉ publish vào loopback của host. Nginx/Caddy trên host làm HTTPS; mẫu Nginx ở `deploy/nginx.conf.example`. Đặt `APP_ORIGINS` đúng origin gồm scheme + hostname + port nếu có, phân cách dấu phẩy nếu cần nhiều origin. Chặn Host/Origin khác, cookie Secure/HttpOnly/SameSite trong production. Không dùng wildcard.

Uvicorn hiện không tin proxy headers; IP trong phiên là IP proxy và login rate limit theo IP proxy + username. Nếu cần IP client thật, thiết lập allowlist proxy chính xác và kiểm lại trước bật; không đặt tin mọi IP trên cổng public. App kiểm Origin độc lập và cookie Secure dựa vào APP_ENV, không dựa vào header client.

```sh
cp .env.example .env
# Chỉnh .env: key, models, APP_ORIGINS, bootstrap password
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 app
curl http://127.0.0.1:8088/api/health
```

Health chỉ xác nhận backend sống; không thử key, model availability hoặc số dư. Admin chọn model trong bốn giá trị server cấu hình; client không được chọn model tùy ý cho chat. Khi xóa một model khỏi .env, tài khoản đang dùng model đó phải được admin gán lại; không tự chuyển sang model khác.

Dockerfile dùng non-root UID 10001, root filesystem read-only, volume data riêng, bỏ capabilities, giới hạn thư mục temp. Không COPY .env/data/test/archives vào image. Dependency runtime đã khóa cho Python 3.14/Linux; cần build image thật và kiểm trên server đích.

## Docker: giữ tài khoản đang có khi chuyển server

DB `data/app.sqlite3` hiện giữ tài khoản/mật khẩu đã hash, hội thoại, tài liệu upload, usage và audit. Docker khởi tạo mới sẽ không dùng DB này trừ khi chuyển riêng. Không copy trực tiếp DB đang ghi WAL.

1. Dừng nhận yêu cầu mới/chờ các lượt hoàn tất. Dùng nút **Hệ thống → Sao lưu cơ sở dữ liệu** để tạo SQLite snapshot nhất quán trong `data/backups`.
2. Chuyển snapshot qua kênh bảo mật tới server, đặt tên `app.sqlite3` vào named volume `/app/data` **trước lần khởi động đầu tiên**.
3. Bảo đảm UID 10001 có quyền đọc/ghi volume. Không ghi đè DB của deployment đang hoạt động. Sao lưu file .env riêng; không đặt vào image.
4. Khởi động và kiểm đăng nhập, danh sách tài liệu đã duyệt (corpus chuẩn 1.200 bản ghi, số hiển thị phụ thuộc thu hồi/hiệu lực), model/hạn mức và báo cáo usage.

Có thể tạo volume bằng `docker compose create`, rồi dùng container công cụ để chép snapshot vào volume trước `docker compose start`. Tên volume thực tế xem qua `docker volume ls`, không đoán tên nếu đã đổi project name. Nếu đã khởi động với DB rỗng, dừng app và xử lý DB mới rõ ràng trước khi restore; không ghép hai DB.

## Cập nhật source Linux và dọn gói triển khai

1. Chờ các lượt đang xử lý hoàn tất, sao lưu SQLite bằng nút admin và lưu `.env` ở nơi riêng có quyền hạn chế.
2. Dừng bằng Ctrl+C hoặc `sudo systemctl stop cyberant`. Không cập nhật file trong lúc tiến trình cũ vẫn phục vụ.
3. Giữ bản code/lockfile cũ để rollback. Cập nhật source và chỉ cài lại dependency khi cần bằng Python trong env `cyberant`. **Không ghi đè `.env` hoặc xóa `data`; không dùng `rsync --delete` trên thư mục chứa dữ liệu.**
4. Chạy `bash /opt/cyberant/start.sh` hoặc khởi động service. Kiểm health, đăng nhập, lịch sử, model/quota, phản hồi và backup.
5. Nếu cần rollback, dừng app, khôi phục code và snapshot tương ứng. Usage phát sinh sau snapshot có thể cần đối soát; không giả định restore DB hoàn lại chi phí provider.

Để dữ liệu độc lập với source cho cài mới, có thể đặt `APP_DATA_DIR` là thư mục tuyệt đối do tài khoản service sở hữu. Với hệ thống đang chạy, chuyển snapshot có kiểm soát trước khi đổi đường dẫn; đường dẫn sai có thể khởi tạo DB mới thay vì tìm tài khoản cũ.

Gói chuyển server không cần `.git`, `.vscode`, `__pycache__`, `.pytest_cache`, môi trường Python Windows, PID/log Windows hoặc `data/initial-accounts.json`. Chuyển snapshot DB riêng. Source hiện không kèm test hay công cụ đánh giá offline theo yêu cầu. Giữ lockfile, công cụ đồng bộ runtime và tài liệu vận hành để cập nhật. `Run.txt` cũ được hợp nhất vào README và tài liệu này.

## Backup / cập nhật / restore

Backup SQLite bao gồm usage, tài khoản, nguồn đã import và upload. Giữ thêm `knowledge/documents.json`, phiên bản code và cấu hình .env riêng. Backup chứa dữ liệu người dùng, không công khai. Khi restore, dừng app, dùng snapshot thống nhất, bảo đảm quyền file và khởi động lại. Pending in-flight khi crash được chuyển thành chưa rõ usage để admin đối soát; không tự bỏ lượng token có thể đã dùng.

`docker compose up -d --build` cập nhật image, giữ named volume. Không dùng `docker compose down -v` nếu cần giữ dữ liệu. Thay nội dung knowledge trong source cần build lại image (hoặc thiết kế mount chỉ đọc riêng); nút đồng bộ áp dụng bản knowledge đang ở container.

Không chạy nhiều worker hoặc nhiều replica: quota dùng SQLite transaction, nhưng khóa hội thoại và hàng chờ vẫn trong một tiến trình. Chưa kiểm thử tải/khôi phục trên server đích. Cần smoke test HTTPS, đăng nhập, backup/restore và hạn mức sau khi có server/tên miền.
