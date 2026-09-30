# CyberAnt — OpenRouter Knowledge

Một ứng dụng dùng OpenRouter, kho lý thuyết chung, tài khoản và lịch sử riêng. Không còn model GPU, runtime llama.cpp hoặc chế độ local trong dự án server.

## Chạy trực tiếp với Miniconda trên Linux

```bash
conda create -n cyberant python=3.14 pip -y
conda activate cyberant
cd /duong/dan/TestSystem
python -m pip install -r requirements-lock.txt
# Sau khi cấu hình .env theo hướng dẫn dưới đây:
bash /duong/dan/TestSystem/start.sh
```

Mỗi lần sau chỉ cần `bash /duong/dan/TestSystem/start.sh`: tự activate Conda `cyberant`, chạy UI/API/SQLite/RAG tại `0.0.0.0:8088`. Script không tự cài dependency hoặc sửa dữ liệu.

**Server LAN 192.168.1.50:** giữ API key/model trong `.env`, đặt `APP_ENV=lan`, `APP_HOST=0.0.0.0`, `APP_PORT=8088`, `APP_ORIGINS=http://192.168.1.50:8088,http://127.0.0.1:8088,http://localhost:8088`. Truy cập **http://192.168.1.50:8088/**. HTTP không mã hóa; giới hạn bằng firewall LAN. Cài mới cần mật khẩu admin bootstrap 14–128 ký tự; tài khoản cũ trong DB không đổi.

**HTTPS:** dùng `APP_ENV=production`, origin HTTPS và reverse proxy. `python main.py` đọc host/port từ `.env` (mặc định loopback); script LAN mặc định bind mọi interface. Xem [hướng dẫn đầy đủ](docs/DEPLOYMENT.md).

Để chạy nền và tắt bằng lệnh, cài service theo [hướng dẫn Miniconda/systemd](docs/DEPLOYMENT.md), rồi dùng `sudo systemctl start cyberant` / `sudo systemctl stop cyberant`. Chạy trực tiếp `python main.py` chiếm terminal. Không chạy đồng thời service, Python trực tiếp và Docker với cùng DB.

DB mặc định của bản Conda là `data/app.sqlite3` ngay trong dự án. Để giữ tài khoản cũ, chuyển snapshot SQLite nhất quán vào đó trước lần khởi động đầu tiên. Nếu cài mới, đặt `BOOTSTRAP_ADMIN_PASSWORD` ít nhất 14 ký tự. Không mang file mật khẩu tham khảo `data/initial-accounts.json` lên server.

## Chạy bằng Docker (tùy chọn)

1. Sao chép `.env.example` thành `.env` trên server. Điền key, bốn model, `APP_ORIGINS=https://<tên-miền>` và mật khẩu admin ban đầu ít nhất 14 ký tự. Không ghi đè `.env` đang có nếu chưa lưu lại key/model.
2. Chạy `docker compose up -d --build`. Dừng bằng `docker compose stop`.
3. Cấu hình reverse proxy HTTPS theo `deploy/nginx.conf.example`, thay tên miền và certificate. App chỉ được publish ở `127.0.0.1:8088` của server.
4. Đăng nhập admin. Sau khi DB đã có tài khoản, bỏ `BOOTSTRAP_ADMIN_PASSWORD` khỏi cấu hình và tạo lại container để loại secret khỏi môi trường tiến trình.

Chưa có tên miền thì chuẩn bị cấu hình trước; production không chấp nhận origin HTTP. Để thử trên máy, dùng `APP_ENV=development`, origin `http://127.0.0.1:8088` và chạy Python trực tiếp. Chưa có Docker trên máy làm việc hiện tại nên bản container chưa được build/run tại đây; mã đã kiểm trong môi trường Python sạch.

## Quản trị tài khoản và token

“Tra cứu nội bộ” mô tả nguồn tài liệu và phạm vi tài khoản, không có nghĩa xử lý AI hoàn toàn nội bộ: câu hỏi/ngữ cảnh liên quan vẫn được gửi tới nhà cung cấp AI qua OpenRouter.

**Người dùng → Tạo/Sửa tài khoản**: chọn vai trò, tick một hoặc nhiều model trong `.env`, hạn mức tháng, mật khẩu và trạng thái. Để trống mật khẩu khi tạo: cấp ngẫu nhiên; khi sửa: giữ mật khẩu cũ. Admin có thể nhập mật khẩu mới cho mọi tài khoản hoặc cấp lại ngẫu nhiên. Đổi mật khẩu/khóa/đổi vai trò thu hồi phiên. Model và hạn mức cập nhật ngay, không cần đăng xuất.

**Chọn model:** cả thành viên và admin chọn model được cấp tại thanh công cụ Trợ lý AI. Lựa chọn lưu theo tài khoản, áp dụng cho câu hỏi tiếp theo; đổi model không xóa hội thoại hoặc reset token. Backend kiểm tra quyền khi nhận câu hỏi, giữ token và trước khi gửi API. Khi model bị thu hồi/không còn cấu hình, chọn lại thủ công; không tự chuyển model. Lượt đã gửi tới provider không thể thu hồi, usage vẫn được ghi nhận. Khi nâng cấp, tài khoản cũ chỉ được cấp model cũ; migration không tự mở rộng quyền. Nên sao lưu SQLite trước nâng cấp.

**Giao diện:** cỡ chữ trả lời cố định 18px, không dùng thiết lập cỡ chữ cũ của trình duyệt. Trang đăng nhập dùng nội dung “Tra cứu nội bộ”, có nút hiện/ẩn mật khẩu; bỏ nhãn OpenRouter API không thay đổi nhà cung cấp xử lý phía backend.

**Hạn mức = token đầu vào + đầu ra**, dùng chung cho mọi model được cấp, bao gồm reasoning nếu nhà cung cấp tính trong usage. Tháng tính theo **UTC**, tự chuyển kỳ bằng khóa `YYYY-MM`, không cần cron và không xóa lịch sử sử dụng. Mặc định tài khoản cũ/mới: **1.000.000 token/tháng**; admin cũng chịu hạn mức. `0` chặn gọi AI, vẫn đăng nhập/đọc tài liệu được.

Trước gọi API, SQLite giữ trước ngân sách đầu vào ước lượng + trần đầu ra bằng transaction. Lượt chạy song song dùng chung hạn mức; không cho cùng chi phần còn lại. Sau phản hồi cập nhật theo `usage` thực và trả phần thừa. Mô hình/tokenizer khác nhau có thể vượt ước lượng: số thực vẫn được ghi đầy đủ và chặn lượt sau; đây không phải hạn mức cứng do OpenRouter thực thi.

**Theo dõi token theo tháng**: lọc tài khoản và tháng; xem token vào/ra, tổng đã dùng, đang giữ, chưa rõ, model và chi phí provider báo. Xóa hội thoại/reset mật khẩu/đổi model không reset lượng đã dùng. Hạn mức hiện tại hiển thị cùng thống kê; chưa lưu lịch sử các mức hạn mức theo từng tháng.

Timeout/mất mạng/khởi động lại lúc gọi có thể đã bị provider tính token: hệ thống giữ ngân sách ở trạng thái **Cần đối soát**, không ghi giả là 0. Admin xem mã generation nếu có, xác minh OpenRouter rồi nhập token thực và ghi chú; thao tác được audit. Không tự gọi lại hoặc đổi model khi lỗi.

## Kho tri thức và chi phí

`knowledge/documents.json` là nguồn chuẩn duy nhất gồm 1.200 tài liệu (bao gồm bản nháp kỹ thuật cần rà soát). Startup hoặc **Hệ thống → Đồng bộ kho tri thức** cập nhật thêm/sửa/xóa vào DB, giữ trạng thái thu hồi. Không cần NewData/Word/Excel gốc để chạy server. Upload TXT/MD/PDF có text chờ admin duyệt; chỉ nhập lý thuyết được phép chia sẻ.

RAG tìm từ/ký tự, bí danh Việt/Anh và ưu tiên theo mục đích câu hỏi trên CPU, tối đa 6 đoạn. Tách định nghĩa khỏi hướng dẫn vận hành trong glossary cũ; giữ nguyên từng đoạn, không cắt mất kiểm chứng/rollback hoặc xóa dòng lặp bên trong nguồn. Đoạn quá lớn không vừa ngân sách sẽ bị bỏ và ghi số lượng; upload dài nên chia thành các bài độc lập có đủ ngữ cảnh.

Trần mặc định: đầu vào **18.000 byte UTF-8** (tên cấu hình cũ `RAG_INPUT_TOKENS`, không phải tokenizer), đầu ra **2.400 token**. Theo câu hỏi, giới hạn mục tiêu lần lượt là 8.000/1.000 cho khái niệm, 14.000/1.800 cho so sánh/khảo sát, 18.000/2.400 cho quy trình/chẩn đoán; luôn tôn trọng trần `.env`. Byte chỉ là proxy, không bảo đảm chặn tuyệt đối token provider; usage thực là căn cứ tính hạn mức. Không hạ đầu ra âm thầm khi quota thiếu: chặn trước API và đề nghị thu hẹp câu hỏi. Lưu `finish_reason`, số đoạn bỏ và giới hạn đầu ra để đo chất lượng/chi phí.

Không gọi thêm model phân loại/kiểm tra, không tự retry, không gửi cả kho/lịch sử. Kiểm mã nguồn chỉ xác nhận ID hợp lệ, **không xác minh nhận định được nguồn chứng minh**. Trích dẫn sai không còn bị thay bằng hai đoạn nguồn không liên quan. Chưa có embeddings/reranker, tokenizer riêng từng model hoặc cache câu trả lời. Nhãn dự thảo vẫn được giữ.

Đánh giá offline, không mở database ứng dụng hoặc gọi AI:
```powershell
python -B D:\TestSystem\knowledge_quality.py --output D:\TestSystem\docs\knowledge-after.json
```
Xem `D:\TestSystem\docs\KNOWLEDGE_QUALITY.md` về phạm vi đã sửa, kết quả và phần còn cần rà soát. Bộ 108 câu là smoke test truy xuất, không phải chứng nhận chất lượng trả lời.

## Triển khai và dữ liệu

- [Hướng dẫn triển khai, chuyển DB và backup](docs/DEPLOYMENT.md)
- [Thay đổi Linux/LAN và giới hạn kiểm chứng](docs/LINUX_RELEASE.md)
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
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe -m pytest -q
powershell -File Start-App.ps1 -Python .venv\Scripts\python.exe
powershell -File Stop-App.ps1
```

Trên Windows, `Start-App.ps1` chạy nền và trả lại terminal; `Stop-App.ps1` dừng đúng tiến trình đã ghi nhận của dự án. Chờ câu trả lời đang xử lý hoàn tất trước khi dừng. Log nằm ở `data/logs`. Thông tin đăng nhập cũ đã được khôi phục theo yêu cầu vào `data/initial-accounts.json` trên máy phát triển, không đưa vào Git hoặc image Docker.

Phần local cũ nằm riêng tại `D:\CyberAnt-Local-Archive-20260928` trên máy phát triển, không phải dependency của bản server.
