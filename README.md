# CyberAnt AI — demo local

Demo chạy trong **D:\TestSystem**, dành cho sale và kỹ thuật, sử dụng **Qwen3.5-9B Q4_K_M thật trên GPU NVIDIA RTX 4060 Laptop 8GB**.

## Mở demo

Truy cập **http://127.0.0.1:8088**. Chọn một tài khoản giả lập:

- **Sale / Minh Anh**: dịch vụ, giải pháp, chính sách và hồ sơ khách giả lập A.
- **Kỹ thuật / Hoàng Nam**: thêm runbook kỹ thuật, hồ sơ khách giả lập B; không xem khách A.
- **Quản trị**: xem, tải lên, duyệt/thu hồi tri thức và nhật ký demo.

Đăng nhập chọn nhanh là cơ chế mô phỏng vai trò, **không phải xác thực production**. Hệ thống chỉ bind localhost. Không đổi bind thành `0.0.0.0` để dùng chung trước khi bổ sung xác thực thực sự.

## Bật / tắt

Chạy trong PowerShell:

```powershell
cd D:\TestSystem
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

Đợi model sẵn sàng rồi mở trình duyệt. Lần tải vào GPU có thể mất 10–60 giây, lâu hơn khi máy thiếu RAM. `Start-Demo.ps1` kiểm tra cổng và không dừng dịch vụ khác. Model dùng port 1234, web dùng port 8088.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Demo.ps1
```

Lệnh dừng chỉ nhắm tiến trình model/demo thuộc thư mục này; giữ nguyên model, tài liệu và dữ liệu hội thoại. Không tự chạy lúc Windows khởi động. Nếu máy khởi động lại, chạy Start-Demo.ps1.

## Luồng dùng thử trong 10 phút

1. Vào Sale, hỏi **“Firewall mạng và WAF khác nhau như thế nào?”**. AI dùng model local; mở nguồn ở bên phải hoặc các nút mã nguồn dưới câu trả lời.
2. Hỏi **“Cam kết hoàn thành trong 2 ngày được không?”**. Quy tắc nghiệp vụ chặn chốt cam kết, hỏi thêm và chuyển duyệt. Loại câu này được xử lý bằng quy tắc, không cần gọi LLM; UI hiển thị rõ.
3. Vào **Dự toán dịch vụ**, chọn firewall, 1 site, đánh dấu thiết bị/license sẵn sàng: kết quả **12 triệu đồng / 4 ngày công DEMO**, chưa VAT, phần cứng, license. Bỏ điều kiện sẵn sàng hoặc chọn HA/migration phức tạp: yêu cầu khảo sát, không xuất số chắc chắn.
4. Đổi sang Kỹ thuật, hỏi **“VPN gián đoạn sau nâng firmware cần kiểm tra gì?”** hoặc dùng gợi ý MOP. Cần kiểm chứng phiên bản và người có quyền duyệt trước thao tác.
5. So sánh Kho tri thức ở hai vai trò: hồ sơ khách A/B và tài liệu kỹ thuật có phạm vi khác nhau; ACL nằm ở backend, không phải chỉ ẩn trên giao diện.
6. Vào Quản trị, tải một file TXT/MD UTF-8 hoặc PDF có text, đọc trước rồi **Duyệt**. Tài liệu chờ duyệt không tham gia RAG. **Thu hồi** khiến tài liệu không còn được truy xuất; nguồn và lịch sử được kiểm lại khi tải.

## Model và GPU

- Model người dùng yêu cầu: https://lmstudio.ai/models/qwen/qwen3.5-9b
- File đúng từ repository được trang trên liên kết: `lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf`, khoảng 5,63GB. Revision và SHA-256 lưu trong `models/manifest.json`.
- Runtime: **llama.cpp b10816, Vulkan Windows x64**, tải từ release chính thức ggml-org/llama.cpp. Chọn **Vulkan0 = RTX 4060 Laptop**, không dùng iGPU AMD.
- Dịch vụ LM Studio/Bionic đã có trên máy nhưng không khởi động được ở lần khảo sát. Vì vậy demo chạy **cùng model GGUF bằng llama.cpp độc lập**, không phụ thuộc giao diện LM Studio; đây vẫn là inference model thật trên GPU.
- Log đã xác nhận `offloaded 33/33 layers to GPU`; vẫn có một phần buffer CPU/mmap bình thường. Tổng VRAM quan sát khoảng 5,8–6,3GB gồm cả ứng dụng Windows, thay đổi theo tải.
- Context 4.096 token, 1 slot, Q8 KV cache, flash attention; prompt cache RAM 256MiB; không reasoning dài. Giới hạn này phù hợp demo trên máy RAM 16GB/VRAM 8GB, không đại diện hiệu năng server trong bản kế hoạch.
- Hai câu smoke test ban đầu khoảng 6–9 giây end-to-end. Đây là đo hai câu ngắn, không phải benchmark p95 hay cam kết nhiều người dùng.
- Không tải vision projector: demo dùng text; chưa phân tích ảnh hoặc PDF scan bằng model thị giác.

## Kiến trúc hiện thực

```text
Trình duyệt → FastAPI (localhost:8088) → tài khoản / ACL / hiệu lực
  ├─ Chat → tách đoạn + tìm từ khóa/TF-IDF → ngữ cảnh được phép
  │         → llama.cpp Qwen3.5-9B trên GPU → JSON + kiểm mã nguồn → trả lời
  ├─ Dự toán → service_catalog.json → công thức Python → nháp cần duyệt
  └─ Quản trị → tải text → pending → đọc/duyệt → SQLite / audit
```

RAG demo dùng **word + character TF-IDF** trên CPU, không phải neural semantic embeddings/reranker trong kiến trúc production. Tìm kiếm bỏ dấu, chia đoạn tài liệu dài và lọc quyền trước khi xếp hạng. Không fine-tuning và không tự học chat.

Kiểm trích dẫn đảm bảo ID tồn tại trong các nguồn đã gửi và có trong câu trả lời; **chưa tự chứng minh từng nhận định được nguồn hỗ trợ đầy đủ**. Người dùng phải đọc nguồn. Quy tắc chặn giá/SLA/tiến độ theo từ khóa chỉ là demo và không bảo đảm nhận diện mọi cách diễn đạt.

Mỗi lượt hỏi tra cứu độc lập; lịch sử được hiển thị nhưng không tự đưa toàn bộ vào prompt. Hãy nêu lại thiết bị/dịch vụ khi hỏi tiếp. Đầu vào tối đa 1.500 ký tự và câu trả lời giới hạn token; khi nguồn quá dài/context vượt giới hạn, hệ thống báo lỗi thay vì gọi cloud.

## Dữ liệu

18 tài liệu tổng hợp trong `data/demo_documents.json`; 4 định mức trong `data/service_catalog.json`. Các nhóm: firewall/VPN, Wi-Fi, backup/NAS, WAF, PAM, vận hành, SLA, RMA, checklist sale, MOP, VPN, restore, RCA và hai khách hoàn toàn giả lập.

**Tất cả giá, số ngày, SLA và khách hàng đều là DEMO, không phải dữ liệu thật hoặc chính sách CyberAnt.** Danh mục được lấy cảm hứng từ website công khai https://cyberant.vn/; không sao chép tài liệu nội bộ.

- Tài liệu runtime, tài khoản phiên, lịch sử, feedback và audit nằm trong `data/demo.sqlite3`.
- Upload nhận tối đa 2MB, 12.000 ký tự; PDF đọc tối đa 30 trang có text. Không có OCR hoặc antivirus trong demo: chỉ tải tài liệu mẫu tin cậy, không nhập bí mật thật.
- Metadata gồm owner, vai trò, customer, version, trạng thái và hiệu lực. Tài liệu mẫu có hiệu lực giả lập tới 31/12/2027.
- Tải lên/thu hồi thao tác trên SQLite; file seed không tự ghi đè dữ liệu đã có khi restart.
- Tài liệu thiếu OCR, số liệu thiếu thẩm quyền và nguồn mâu thuẫn vẫn cần biên tập/phê duyệt.

## Bảo mật và giới hạn

Backend kiểm session cookie HttpOnly/SameSite, origin, Host; không bật CORS tùy ý trên web app. API model có khóa riêng trong `data/model-api-key.txt`, không đưa khóa vào JavaScript. Không công bố khóa hoặc thư mục dữ liệu lên Git. Model không có shell, công cụ chạy lệnh, gửi email hay connector bên ngoài.

Model/thư viện tải về cần Internet khi setup; inference và tìm kiếm dùng địa chỉ loopback và tài nguyên local. Không có cloud fallback hay CDN frontend. **Chưa thực hiện kiểm toán lưu lượng toàn máy hoặc air-gap vật lý**; chương trình khác trên máy vẫn có thể dùng Internet.

Chưa triển khai SSO/MFA, người dùng thật, semantic embeddings, reranker, OCR, antivirus sandbox, mã hóa/retention doanh nghiệp, HA, CRM/ticket connector, workflow phê duyệt báo giá thật hoặc chịu tải 20 người. Bản demo minh họa quy trình cốt lõi trong kế hoạch; chưa phải hệ thống production.

Hội thoại demo lưu local cho tới khi quản trị xử lý; không có job tự xóa theo hạn. Nội dung đã thấy hoặc chụp màn hình không thể thu hồi từ thiết bị người dùng. Session demo hết hạn sau 12 giờ; đổi vai trò tạo phiên mới.

## Kiểm thử / bằng chứng

```powershell
.\.venv-runtime\Scripts\python.exe -m pytest -q
.\.venv-runtime\Scripts\python.exe .\smoke_demo.py
.\.venv-runtime\Scripts\python.exe .\check_ui.py
```

- `test_app.py`: kiểm ACL theo vai trò/khách, quyền admin, tính giá/effort, điều kiện thiếu, chặn cam kết, duyệt/thu hồi, tách lịch sử/feedback, origin/session. Test DB dùng thư mục tạm, không sửa dữ liệu chạy thật.
- `smoke_demo.py`: gọi model thật cho sale và kỹ thuật, kiểm trả lời có mã nguồn; báo cáo trong `artifacts/smoke-report.json`.
- `check_ui.py`: Chrome headless có sẵn trên máy; kiểm đăng nhập, modal nguồn, dự toán, chặn cam kết và mobile. Ảnh/báo cáo ở `artifacts/`.
- Log runtime/backend ở `logs/`. Log có thể chứa thông tin demo; không chia sẻ nếu sau này dùng dữ liệu thật.

## Sao lưu

```powershell
.\.venv-runtime\Scripts\python.exe .\Backup-Data.py
```

Lệnh tạo SQLite backup nhất quán và sao chép seed/catalog JSON vào `backups/<timestamp>`. Để khôi phục: dừng demo, giữ một bản dữ liệu hiện tại, thay `data/demo.sqlite3` bằng bản backup được chọn, khởi động lại. Khóa API model có thể giữ nguyên hoặc tạo lại; backup mẫu này không sao chép khóa. Chưa phải chính sách backup doanh nghiệp.

## Cấu trúc

```text
D:\TestSystem\
  Start-Demo.ps1 / Stop-Demo.ps1 / README.md
  app.py / seed_data.py / requirements-lock.txt
  static/            giao diện, không CDN
  data/              SQLite, seed, catalog, khóa API local
  models/            GGUF + manifest
  runtime/           llama.cpp Vulkan
  .venv-runtime/     Python và thư viện
  logs/              log và PID chẩn đoán
  artifacts/         bằng chứng kiểm thử và ảnh
  backups/           bản sao dữ liệu
```

Nếu model báo thiếu VRAM: đóng ứng dụng GPU không cần thiết, giảm context hoặc giảm số lớp GPU trong `Start-Demo.ps1`, rồi restart. Không cài/đổi driver NVIDIA tự động trong demo này. Giữ cấu hình đã kiểm thử nếu chưa có vấn đề.

Nếu cổng bị chiếm: kiểm dịch vụ nào đang dùng cổng, không tắt tiến trình không rõ nguồn. Script stop chỉ dừng model/backend của demo trong thư mục này.
