# CyberAnt — OpenRouter Knowledge

Một ứng dụng dùng OpenRouter, kho lý thuyết chung, tài khoản và lịch sử riêng. Không còn model GPU, runtime llama.cpp hoặc chế độ local trong dự án server.

## Chạy trực tiếp với Miniconda trên Linux

```bash
conda create -n cyberant python=3.14 pip -y
conda activate cyberant
cd /duong/dan/TestSystem
python -m pip install -r requirements-lock.txt
python main.py
```

Điền `.env` trước khi chạy: API key, bốn model, `APP_ENV=production` và `APP_ORIGINS` đúng tên miền HTTPS. `main.py` chạy toàn bộ giao diện/API/SQLite/RAG trong một process, mặc định `127.0.0.1:8088`; đọc `.env` trong thư mục dự án. Có thể đổi `APP_HOST`/`APP_PORT` hoặc dùng `--host`/`--port`.

Để chạy nền và tắt bằng lệnh, cài service theo [hướng dẫn Miniconda/systemd](docs/DEPLOYMENT.md), rồi dùng `sudo systemctl start cyberant` / `sudo systemctl stop cyberant`. Chạy trực tiếp `python main.py` chiếm terminal. Không chạy đồng thời service, Python trực tiếp và Docker với cùng DB.

DB mặc định của bản Conda là `data/app.sqlite3` ngay trong dự án. Để giữ tài khoản cũ, chuyển snapshot SQLite nhất quán vào đó trước lần khởi động đầu tiên. Nếu cài mới, đặt `BOOTSTRAP_ADMIN_PASSWORD` ít nhất 14 ký tự. Không mang file mật khẩu tham khảo `data/initial-accounts.json` lên server.

## Chạy bằng Docker (tùy chọn)

1. Sao chép `.env.example` thành `.env` trên server. Điền key, bốn model, `APP_ORIGINS=https://<tên-miền>` và mật khẩu admin ban đầu ít nhất 14 ký tự. Không ghi đè `.env` đang có nếu chưa lưu lại key/model.
2. Chạy `docker compose up -d --build`. Dừng bằng `docker compose stop`.
3. Cấu hình reverse proxy HTTPS theo `deploy/nginx.conf.example`, thay tên miền và certificate. App chỉ được publish ở `127.0.0.1:8088` của server.
4. Đăng nhập admin. Sau khi DB đã có tài khoản, bỏ `BOOTSTRAP_ADMIN_PASSWORD` khỏi cấu hình và tạo lại container để loại secret khỏi môi trường tiến trình.

Chưa có tên miền thì chuẩn bị cấu hình trước; production không chấp nhận origin HTTP. Để thử trên máy, dùng `APP_ENV=development`, origin `http://127.0.0.1:8088` và chạy Python trực tiếp. Chưa có Docker trên máy làm việc hiện tại nên bản container chưa được build/run tại đây; mã đã kiểm trong môi trường Python sạch.

## Quản trị tài khoản và token

**Người dùng → Tạo/Sửa tài khoản**: chọn vai trò, model trong `.env`, hạn mức tháng, mật khẩu và trạng thái. Để trống mật khẩu khi tạo: cấp ngẫu nhiên; khi sửa: giữ mật khẩu cũ. Admin có thể nhập mật khẩu mới cho mọi tài khoản hoặc cấp lại ngẫu nhiên. Đổi mật khẩu/khóa/đổi vai trò thu hồi phiên. Model và hạn mức cập nhật ngay, không cần đăng xuất.

**Hạn mức = token đầu vào + đầu ra**, bao gồm reasoning nếu nhà cung cấp tính trong usage. Tháng tính theo **UTC**, tự chuyển kỳ bằng khóa `YYYY-MM`, không cần cron và không xóa lịch sử sử dụng. Mặc định tài khoản cũ/mới: **1.000.000 token/tháng**; admin cũng chịu hạn mức. `0` chặn gọi AI, vẫn đăng nhập/đọc tài liệu được.

Trước gọi API, SQLite giữ trước ngân sách đầu vào ước lượng + trần đầu ra bằng transaction. Lượt chạy song song dùng chung hạn mức; không cho cùng chi phần còn lại. Sau phản hồi cập nhật theo `usage` thực và trả phần thừa. Mô hình/tokenizer khác nhau có thể vượt ước lượng: số thực vẫn được ghi đầy đủ và chặn lượt sau; đây không phải hạn mức cứng do OpenRouter thực thi.

**Theo dõi token theo tháng**: lọc tài khoản và tháng; xem token vào/ra, tổng đã dùng, đang giữ, chưa rõ, model và chi phí provider báo. Xóa hội thoại/reset mật khẩu/đổi model không reset lượng đã dùng. Hạn mức hiện tại hiển thị cùng thống kê; chưa lưu lịch sử các mức hạn mức theo từng tháng.

Timeout/mất mạng/khởi động lại lúc gọi có thể đã bị provider tính token: hệ thống giữ ngân sách ở trạng thái **Cần đối soát**, không ghi giả là 0. Admin xem mã generation nếu có, xác minh OpenRouter rồi nhập token thực và ghi chú; thao tác được audit. Không tự gọi lại hoặc đổi model khi lỗi.

## Kho tri thức và chi phí

`knowledge/documents.json` là nguồn chuẩn duy nhất gồm 1.194 tài liệu. Startup hoặc **Hệ thống → Đồng bộ kho tri thức** cập nhật thêm/sửa/xóa vào DB, giữ trạng thái thu hồi. Không cần NewData/Word/Excel gốc để chạy server. Upload TXT/MD/PDF có text chờ admin duyệt; chỉ nhập lý thuyết được phép chia sẻ.

RAG tìm từ/ký tự và ưu tiên nhóm A–F trên CPU, chọn tối đa 6 đoạn đa dạng, bỏ phần lặp và giới hạn prompt. Thường một API call cho câu có nguồn. Không gửi cả kho hoặc toàn lịch sử. Ngân sách đầu vào 6.000 là ước lượng byte UTF-8 bảo thủ, không phải tokenizer chính xác; số thực lấy từ API. Chưa có embeddings/reranker hoặc cache câu trả lời. Nhãn dự thảo kỹ thuật vẫn được giữ.

## Triển khai và dữ liệu

- [Hướng dẫn triển khai, chuyển DB và backup](docs/DEPLOYMENT.md)
- [Báo cáo thay đổi và kiểm thử](docs/SERVER_REPORT.md)
- `data/app.sqlite3`: DB hiện có trên máy; Docker mới dùng named volume riêng, **không tự chép tài khoản cũ vào image**.
- API key, DB, mật khẩu khởi tạo, log, test và model local không được đưa vào Docker image.
- Một worker / một instance SQLite. Chưa hỗ trợ nhiều replica dùng chung hạn mức và hàng chờ; mở rộng cần thiết kế lại điều phối.

## Kiểm thử và chạy Python

Python 3.14. `requirements-lock.txt` chứa dependency runtime; công cụ kiểm thử nằm riêng ở `requirements-dev.txt`.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
powershell -File Start-App.ps1 -Python .venv\Scripts\python.exe
powershell -File Stop-App.ps1
```

Trên Windows, `Start-App.ps1` chạy nền và trả lại terminal; `Stop-App.ps1` dừng đúng tiến trình đã ghi nhận của dự án. Chờ câu trả lời đang xử lý hoàn tất trước khi dừng. Log nằm ở `data/logs`. Thông tin đăng nhập cũ đã được khôi phục theo yêu cầu vào `data/initial-accounts.json` trên máy phát triển, không đưa vào Git hoặc image Docker.

Phần local cũ nằm riêng tại `D:\CyberAnt-Local-Archive-20260928` trên máy phát triển, không phải dependency của bản server.
