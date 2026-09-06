# CyberAnt AI — workspace local

Đang chạy tại **D:\TestSystem**, dùng **Qwen3.5-9B Q4_K_M** trên RTX 4060 Laptop GPU 8 GB. Giao diện chỉ dùng chữ CyberAnt AI, có hover rõ, cỡ chữ trả lời 16–22px và nút **☰** ở góc trên trái để mở/đóng thanh bên. Trạng thái thanh bên được lưu trên trình duyệt; điện thoại có menu mở phủ, đóng lại khi chọn mục.

## Đăng nhập

Mở **http://127.0.0.1:8088**; Ctrl+F5 nếu đang mở bản cũ.

| Tên đăng nhập | Vai trò |
|---|---|
| `sales` | Sales |
| `kythuat` | Kỹ thuật |
| `admin` | Quản trị |

Mật khẩu khởi tạo ngẫu nhiên nằm trong **`data/initial-accounts.json`**. Mở file tại máy để xem; không đưa mật khẩu vào kho tri thức hoặc Git. File không cập nhật theo mật khẩu thay đổi sau này. Đổi mật khẩu tại **Tài khoản**; quản trị có thể đặt lại trong **Người dùng**.

Mật khẩu băm scrypt có salt; phiên cookie HttpOnly/SameSite Strict hết hạn sau 12 giờ, token lưu dạng băm trong SQLite. Có giới hạn đăng nhập sai, khóa tài khoản và thu hồi phiên khi đổi quyền/mật khẩu. Hệ thống bind localhost, chưa triển khai HTTPS/SSO/MFA hoặc truy cập từ nhiều máy LAN.

## Kho tri thức chung

**Mọi tài khoản đã đăng nhập đều đọc và hỏi AI từ cùng một kho gồm 481 tài liệu**, kể cả runbook kỹ thuật, hồ sơ khách và các tài liệu tài chính đã duyệt. Không lọc vai trò/khách hàng trong Kho tri thức, cửa sổ đọc nguồn hoặc RAG/chat. Đây là quyền đọc chung theo yêu cầu demo.

Tài liệu chờ duyệt, đã thu hồi, hết hiệu lực và nguồn dẫn xuất thiếu tài liệu gốc không được dùng để trả lời. **Chỉ quản trị** tải lên, duyệt/thu hồi tài liệu, quản lý tài khoản và điều khiển hệ thống. Metadata vai trò/khách cũ còn được giữ để quản lý hồ sơ; không hạn chế đọc trong kho chung.

Các dashboard **Hồ sơ công ty / Tài chính demo** vẫn dùng nhóm khách được phân công và quyền quản trị vốn có; tài liệu nguồn của chúng đã được mở đọc trong kho chung. Do vậy phân nhóm dashboard không phải hàng rào bảo mật cho tài liệu đã chia sẻ.

Data gồm 251 hồ sơ/tài liệu công ty, 48 tri thức ATTT, 154 hồ sơ tài chính và 28 định mức/đầu vào bổ sung. Có 10 khách, 10 hợp đồng, 20 dự án, 20 báo giá, 40 ticket, 16 mã kho, 18 nhân sự; gói hạ tầng/ATTT, phí công, license, tiến độ, SLA, thu tiền và công nợ. **Giá, ngày công, SLA, khách hàng và chứng từ đều giả lập**, không phải chính sách CyberAnt. VAT 10% là tham số demo công thức. Tri thức ATTT có nguồn NIST/CISA/OWASP/MITRE đã ghi trong metadata; không phải feed realtime.

## Lịch sử trò chuyện

- Mục **Lịch sử trò chuyện** liệt kê các cuộc trò chuyện riêng của tài khoản: tiêu đề, thời gian cập nhật, số lượt hỏi, tìm theo tiêu đề và xem thêm.
- Bấm một cuộc trò chuyện để xem lại và **hỏi tiếp đúng chủ đề**, kể cả sau đăng xuất/đăng nhập lại. Mỗi cuộc trò chuyện có mã riêng; dữ liệu không phụ thuộc cookie phiên.
- **Cuộc trò chuyện mới** mở chủ đề riêng, không xóa lịch sử cũ. Một cửa sổ trình duyệt gửi một câu tại một thời điểm để giữ thứ tự; nhiều người hoặc các cuộc trò chuyện khác nhau có thể gửi đồng thời.
- Trang lịch sử chỉ trả cuộc trò chuyện của chính tài khoản; không nhận ID của người khác. Quản trị vẫn có màn hình xem hội thoại toàn hệ thống theo quyền quản trị đã có, tách khỏi lịch sử cá nhân.
- Mỗi lần mở tải 100 lượt gần nhất, có nút xem lượt cũ hơn. Nguồn bị thu hồi/hết hạn khiến câu trả lời cũ được che nội dung và yêu cầu hỏi lại.
- Hội thoại cũ được chuyển sang mô hình mới khi còn xác định được chủ tài khoản. Dữ liệu từ cơ chế chọn vai trò cũ không xác định được tác giả không tự gán cho một người dùng; chỉ quản trị xem bản ghi cũ.

## Xử lý đồng thời trên GPU

Cấu hình hiện tại: **2 slot model**, **4.096 token mỗi slot**, tổng context **8.192 token**, một model dùng chung trên GPU. Không nạp hai bản trọng số. Model runtime là llama.cpp b10816 Vulkan; log xác nhận offload 33/33 lớp, `n_slots = 2`, `n_ctx_slot = 4096`.

Backend tiếp nhận tối đa 2 lượt cần LLM cùng lúc, tối đa 16 yêu cầu đang chờ, thời gian chờ tối đa 180 giây. Khi hết slot, yêu cầu chờ trước khi gửi vào model. Câu hỏi nghiệp vụ có cấu trúc xử lý bằng Python không chiếm slot LLM. Cùng một cuộc trò chuyện đang sinh câu trả lời sẽ từ chối gửi chồng; các cuộc trò chuyện khác độc lập.

**Đã thử 3 câu từ 3 tài khoản:** model `/slots` ghi nhận 2 slot cùng `is_processing`, backend ghi nhận 2 đang xử lý và 1 đang chờ; cả 3 hoàn tất khoảng **32 giây** trong một lần đo. Đây là bằng chứng hoạt động đồng thời, không phải benchmark p95 hay cam kết tải 20 người. GPU chia sẻ tài nguyên nên từng câu có thể chậm hơn khi chỉ có một người hỏi.

Quản trị xem số đang sinh/đang chờ tại **Hệ thống local**, đổi số lượt đồng thời **1 hoặc 2**, lưu rồi khởi động lại model. Trường context là **mỗi lượt**, lệnh runtime dùng tổng `context × parallel`. Mặc định đã thử 2 × 4.096; giới hạn nhập 8.192 mỗi lượt không có nghĩa GPU chắc chắn đủ bộ nhớ. Có thể hạ về 1 lượt khi cần giảm dùng bộ nhớ hoặc ưu tiên tốc độ từng câu.

## Nghiệp vụ và quản trị hệ thống

Mục **Dự toán dịch vụ** đã gỡ khỏi giao diện và ngừng đăng ký API tính/lưu/gửi/duyệt dự toán dịch vụ (`/api/estimate`, `/api/estimates`, `/api/estimate/templates`). Hồ sơ đã lưu vẫn nằm trong SQLite/backup để tham khảo khi thiết kế lại nghiệp vụ. Bộ dữ liệu định mức tiếp tục làm nguồn tra cứu. **Tài chính demo** là màn hình riêng đang hoạt động, gồm giá trọn gói, TCO, công nợ và chi tiết SLA; không gửi báo giá hoặc giao dịch thật.

**Người dùng:** tạo/sửa/khóa, phân vai trò và nhóm khách A–J, đặt lại mật khẩu, xem online/phiên và thu hồi phiên. Online là có hoạt động/heartbeat trong 75 giây, heartbeat mỗi 25 giây; không đồng nghĩa người dùng đang gõ. Giữ ít nhất một quản trị hoạt động.

**Hệ thống local:** CPU, RAM dùng/khả dụng, pagefile, ổ đĩa, GPU/VRAM/nhiệt độ, tiến trình app/model, kết nối, context thực tế, số slot, hàng chờ, số bản ghi, log và sao lưu. Các số đo được lấy từ psutil/NVIDIA, không tạo giả. RAM/VRAM toàn máy gồm các phần mềm khác; RSS tiến trình có thể chứa trang chia sẻ.

`data/runtime-config.json` lưu context, parallel, GPU layers, cache RAM, temperature và trần token trả lời. Context/parallel/GPU/cache cần restart model; temperature/token áp dụng lượt mới. Không cho đổi cấu hình hoặc dừng model trong lúc đang sinh/chờ câu trả lời. Nút điều khiển chỉ tác động đúng executable/alias model thuộc thư mục này.

## Khởi động, dừng và sao lưu

```powershell
cd D:\TestSystem
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

Web dùng port 8088, model dùng 1234. Lần nạp có thể mất 10–60 giây hoặc hơn khi thiếu RAM. Các tiến trình khởi động ẩn, không tự chạy theo Windows. `Restart-App.ps1` cập nhật backend và giữ model đang nạp; `Stop-Demo.ps1` dừng app/model thuộc thư mục này, không xóa dữ liệu.

```powershell
.\.venv-runtime\Scripts\python.exe .\Backup-Data.py
```

Hoặc bấm Sao lưu trong quản trị. Backup SQLite nhất quán và seed/cấu hình JSON nằm ở `backups/<timestamp>`; không chép mật khẩu khởi tạo hoặc khóa model. Backup chứa tài khoản băm, phiên và hội thoại nên cần bảo quản nội bộ. Khôi phục bằng cách dừng app, sao lưu hiện trạng, thay `data/demo.sqlite3` bằng bản chọn, phục hồi cấu hình nếu cần rồi khởi động.

## Kiến trúc và giới hạn

FastAPI → xác thực → kho chung còn hiệu lực → tìm kiếm word/character TF-IDF trên CPU → ngữ cảnh giới hạn → llama.cpp Qwen trên GPU. Không fine-tuning, không tự học từ chat, không cloud fallback/CDN. Tìm kiếm chuyển sang worker thread để không chặn các request khác khi xây chỉ mục. Cache tối đa 3 chỉ mục float32.

Giá và hồ sơ có cấu trúc lấy bằng quy tắc Python; model tổng hợp/giải thích các câu khác. Trích dẫn kiểm được mã nguồn thuộc ngữ cảnh, **chưa chứng minh từng nhận định hoàn toàn đúng**. Người dùng đọc nguồn trước khi áp dụng. Chat không thực thi lệnh, gửi email, tạo ticket, đặt nguồn lực hay ký/gửi báo giá.

Upload TXT/MD UTF-8 hoặc PDF có text, tối đa 2MB/12.000 ký tự/30 trang; chưa OCR/antivirus. Chưa có HTTPS/SSO/MFA, HA, mã hóa/retention doanh nghiệp, semantic embeddings/reranker, connector CRM/ticket hoặc kiểm thử tải 20 người. Đây là demo local; chưa triển khai production. Dữ liệu hội thoại không tự xóa theo hạn.

## Kiểm thử và file chính

```powershell
.\.venv-runtime\Scripts\python.exe -m pytest -q
.\.venv-runtime\Scripts\python.exe .\check_workspace_ui.py
.\.venv-runtime\Scripts\python.exe .\check_concurrent_chat.py
```

- Suite backend: xác thực/ACL quản trị, kho chung, nguồn hiệu lực, công thức tài chính, lịch sử riêng qua đăng nhập, migration, phân trang, slot/hàng chờ/maintenance và chủ đề tiếp nối.
- `check_workspace_ui.py`: kho chung, bỏ dự toán dịch vụ, hover, sidebar, lịch sử/đăng nhập lại/hỏi tiếp, mobile và quản trị. `check_ui.py`/`check_management_ui.py` gọi suite giao diện mới.
- `check_concurrent_chat.py`: 3 tài khoản gọi model thật, đo 2 slot xử lý cùng lúc/1 hàng chờ và chặn dừng model khi bận. Báo cáo `artifacts/concurrent-chat-report.json`.
- `check_readability.py`, `check_finance_ui.py`, `check_company_ui.py`: hồi quy ATTT, tài chính và hồ sơ công ty. Test UI/model tạo hội thoại DEMO trong DB đang chạy; unit test dùng DB tạm.
- Bằng chứng mới: `artifacts/workspace-ui-report.json`, ảnh `22-user-history.png`–`25-two-slot-system.png`. Báo cáo cũ trong artifacts có thể mô tả phiên bản trước.
- `app.py`: API/RAG; `accounts.py`: xác thực; `conversations.py`: lịch sử; `generation.py`: điều phối đồng thời; `system_runtime.py`/`admin_system.py`: máy/model; `static/conversations.js`/`workspace.css`: giao diện mới.
- `data/demo.sqlite3`: dữ liệu hoạt động; các JSON/Markdown trong data là seed/bản đọc. Seed không ghi đè tài liệu có sẵn khi restart. Sao lưu trước khi chạy lại các script sinh dữ liệu.
