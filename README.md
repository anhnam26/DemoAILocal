# CyberAnt AI — demo local

Demo chạy trong **D:\TestSystem**, dành cho sale và kỹ thuật, sử dụng **Qwen3.5-9B Q4_K_M thật trên GPU NVIDIA RTX 4060 Laptop 8GB**.

Bộ dữ liệu hiện tại: **453 tài liệu** = 251 tài liệu/hồ sơ công ty + 48 tri thức ATTT + 154 hồ sơ tài chính. Mở **Tài chính demo** để xem dự toán trọn gói, thanh toán và công nợ; dùng **Quản trị** để xem đủ khách và giá vốn/lợi nhuận.

## Mở demo

Truy cập **http://127.0.0.1:8088**. Chọn một tài khoản giả lập:

- **Sale / Minh Anh**: dịch vụ, giải pháp, chính sách và hồ sơ 5 khách giả lập A/C/E/G/I.
- **Kỹ thuật / Hoàng Nam**: thêm runbook kỹ thuật, hồ sơ 5 khách giả lập B/D/F/H/J; không xem nhóm khách của sale.
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

1. Vào Sale, hỏi **“Firewall mạng và WAF khác nhau như thế nào?”**. Bảng so sánh lấy từ tài liệu đã duyệt; hỏi tiếp “Tạo bảng so sánh hai cái đó”. Mở nguồn ở bên phải hoặc các nút mã nguồn dưới câu trả lời.
2. Hỏi **“Cam kết hoàn thành trong 2 ngày được không?”**. Trợ lý đưa dữ liệu gói chuẩn để đối chiếu và chuyển duyệt cam kết cụ thể. Loại câu này được xử lý bằng quy tắc, không cần gọi LLM; UI hiển thị rõ.
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
  ├─ Nghiệp vụ / Dự toán → tài liệu có cấu trúc đã duyệt → công thức Python → nháp cần duyệt
  ├─ Hồ sơ công ty → 134 hồ sơ giả lập → lọc quyền / tìm kiếm / đọc nguồn
  └─ Quản trị → tải text → pending → đọc/duyệt → SQLite / audit
```

RAG demo dùng **word + character TF-IDF** trên CPU, không phải neural semantic embeddings/reranker trong kiến trúc production. Tìm kiếm bỏ dấu, chia đoạn tài liệu dài và lọc quyền trước khi xếp hạng. Cache tối đa 3 bộ chỉ mục float32 trên CPU, làm mới theo nội dung và quyền; không nạp thêm LLM hay tăng context GPU. Không fine-tuning và không tự học chat.

Kiểm trích dẫn đảm bảo ID tồn tại trong các nguồn đã gửi và có trong câu trả lời; **chưa tự chứng minh từng nhận định được nguồn hỗ trợ đầy đủ**. Người dùng phải đọc nguồn. Giá, ngày công, gói SLA và hồ sơ có cấu trúc được trả bằng quy tắc Python từ tài liệu được phép xem. Qwen giải thích và tổng hợp các câu hỏi khác. Bộ nhận diện ý định còn dựa trên từ khóa; câu hỏi nhiều ý hoặc tên viết tắt lạ có thể cần nêu rõ hơn.

Câu hỏi tiếp nối ngắn có thể dùng chủ đề lượt trước trong cùng phiên, sau khi kiểm lại quyền và hiệu lực nguồn. Không đưa toàn bộ lịch sử vào prompt. Nút “Cuộc trò chuyện mới” ngắt chủ đề và ẩn lịch sử cũ khỏi phiên xem; bản ghi audit/chat vẫn lưu local. Đầu vào tối đa 1.500 ký tự và câu trả lời giới hạn token; khi nguồn quá dài/context vượt giới hạn, hệ thống báo lỗi thay vì gọi cloud.

## Dữ liệu

251 tài liệu trong `data/demo_documents.json`; 12 định mức dịch vụ. Snapshot giả lập ngày 05/09/2026 gồm 10 khách, 10 hợp đồng, 20 dự án, 20 báo giá, 40 ticket, 16 mã kho hàng và 18 nhân sự (134 hồ sơ vận hành). Có bảng giá/scope/tiến độ/runbook/FAQ cho từng dịch vụ, 3 gói SLA, bảng so sánh và chính sách thanh toán, chiết khấu, bảo hành, phát sinh. `data/company_documents/` chứa bản Markdown từng tài liệu để đọc và sửa có kiểm soát. `data/company_operations.json` là bản xuất hồ sơ; ứng dụng dùng bản ghi SQLite đã lọc quyền và hiệu lực.

**Tất cả giá, số ngày, SLA và khách hàng đều là DEMO, không phải dữ liệu thật hoặc chính sách CyberAnt.** Danh mục được lấy cảm hứng từ website công khai https://cyberant.vn/; không sao chép tài liệu nội bộ.

- Tài liệu runtime, tài khoản phiên, lịch sử, feedback và audit nằm trong `data/demo.sqlite3`.
- Upload nhận tối đa 2MB, 12.000 ký tự; PDF đọc tối đa 30 trang có text. Không có OCR hoặc antivirus trong demo: chỉ tải tài liệu mẫu tin cậy, không nhập bí mật thật.
- Metadata gồm owner, vai trò, customer, version, trạng thái và hiệu lực. Đa số tài liệu mẫu có hiệu lực giả lập tới 31/12/2027; báo giá mẫu tới 30/09/2026. Các ngày đã qua trong snapshot là dữ liệu lịch sử, không tự trở thành lịch hiện tại.
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
  app.py / business.py / company_data.py / seed_data.py / requirements-lock.txt
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


## Bộ dữ liệu công ty mở rộng — cách test

Vào **Hồ sơ công ty** để lọc loại hồ sơ, tìm tên hoặc mã và bấm **Hỏi trợ lý**. Admin thấy toàn bộ 134 hồ sơ; sale và kỹ thuật thấy các nhóm khách được phân công, sale không xem ticket/runbook chi tiết. Chọn Admin nếu muốn thử tất cả khách hàng trong cùng phiên demo.

| Vai trò | Câu hỏi thử | Kết quả có nguồn |
|---|---|---|
| Sale | Triển khai firewall bao lâu và mất bao nhiêu tiền? | 12 triệu, 4 ngày công, lịch mẫu 4–6 ngày làm việc / site |
| Sale | Báo giá firewall cho 2 site | 24 triệu, 8 ngày công; PM xếp lịch |
| Sale | So sánh BASIC PLUS PREMIUM về SLA, giá, bảo trì | Bảng 3 gói; phân biệt phản hồi với khôi phục |
| Sale | Hợp đồng bảo trì của An Minh Retail có gì? | CONTRACT-A, BASIC, 3 triệu/tháng |
| Sale | Cho tôi thông tin QUOTE-A-01 | Báo giá dịch vụ và dự án liên kết |
| Sale | Firewall mạng và WAF khác nhau thế nào? → Tạo bảng so sánh hai cái đó | Bảng so sánh giữ chủ đề |
| Sale | Tồn kho firewall còn bao nhiêu? | Hàng DEMO, đơn giá, tồn/giữ/khả dụng |
| Kỹ thuật | Tóm tắt TICKET-B-02 | Sự cố backup, nguyên nhân và xử lý trong kịch bản |
| Kỹ thuật | Checklist MOP triển khai firewall gồm những bước nào? | Qwen + runbook có dẫn nguồn |
| Admin | Cho tôi thông tin PROJECT-C-01 | Phạm vi, lịch, PM, kỹ sư, giá dự án mẫu |

Trợ lý chỉ đọc hồ sơ và soạn dự toán. Nút hỏi không tạo ticket, đặt lịch, giữ kho hay gửi báo giá. Lịch nhân sự và dự án là các tình huống demo, chưa có bộ máy tối ưu và kiểm xung đột phân công.

Muốn tái tạo bộ dữ liệu mẫu: chạy `Backup-Data.py` trước, sau đó `.venv-runtime\Scripts\python.exe company_data.py`. Lệnh này cập nhật tài liệu mẫu theo ID; giữ tài liệu upload và trạng thái thu hồi của bản mẫu đã mở rộng. Không chạy nếu đã thay nội dung mẫu bằng dữ liệu thật mà chưa sao lưu. Khởi động lại app bằng `Restart-App.ps1` để giữ model đang nạp trên GPU.

Kiểm tra bổ sung: `python -m pytest test_app.py test_company.py -q` và `python check_company_ui.py` bằng Python trong `.venv-runtime`. Báo cáo/screenshot trong `artifacts/company-ui-report.json`, `06-company-comparison.png` đến `09-company-tickets.png`.


## Giao diện dễ đọc và tri thức ATTT — cập nhật 05/09/2026

- Cỡ chữ trả lời mặc định **18px**, nút **A− / A+** chọn 16–22px và lưu tùy chọn trên trình duyệt.
- Câu trả lời mới được yêu cầu chia thành 2–4 mục, gạch đầu dòng/checklist. Bộ hiển thị hỗ trợ tiêu đề, danh sách đánh số, bảng và code; không thực thi HTML do model sinh.
- Mỗi câu trả lời có **Sao chép**, **Lưu .md**, **Thu gọn / Mở câu trả lời**. Lưu chỉ tải nội dung về máy, không gửi đi.
- Kho tri thức có bộ lọc chủ đề. Tài liệu ATTT có liên kết nguồn chính thức và ngày kiểm nguồn trong cửa sổ đọc; đọc nội dung local không cần Internet, mở website tham khảo cần Internet.
- Thêm **48 tài liệu / 24 chủ đề** từ `security_data.py`, đưa tổng bộ mặc định lên **299 tài liệu**: 251 hồ sơ/tài liệu công ty + 48 tài liệu ATTT. Sale thấy 24 bản kiến thức và tư vấn; kỹ thuật/admin có thêm 24 bài tập lab.
- Chủ đề: NIST CSF 2.0, rủi ro, MFA, IAM, PAM, Zero Trust, phân đoạn mạng, ransomware, backup an toàn, ứng cứu, chứng cứ, phishing/BEC, KEV, bản vá, SOC/SIEM/EDR, detection, logging, OWASP web/API, secret, container, AI RAG, nhà cung cấp và tabletop.
- Nguồn nền tảng: NIST, CISA, OWASP và MITRE. Nội dung là diễn giải tiếng Việt do demo biên soạn; câu hỏi khảo sát, checklist và bài tập là đề xuất của demo, không phải bản dịch tiêu chuẩn hay quy trình được hãng chứng nhận. Metadata `references`, `reviewed_at`, `knowledge_type` phân biệt với hồ sơ công ty giả lập.
- Dữ liệu ở `data/security_documents.json`, bản Markdown trong `data/security_documents/`, danh sách nguồn trong `data/security_manifest.json`. Chạy `security_data.py` để nạp lại riêng bộ ATTT sau sao lưu; không ghi đè upload hoặc trạng thái thu hồi. Bộ này không chứa threat feed/CVE realtime, không tự cập nhật tiêu chuẩn hoặc thông số thiết bị.
- Tài liệu ngắn được giữ nguyên khi truy xuất để không mất checklist. Chỉ mục TF-IDF vẫn giới hạn 3 cache, context GPU 4096 và một model như trước.

Thử: **“MFA chống phishing là gì?”**, **“Zero Trust có phải chỉ mua một thiết bị?”**, **“Ưu tiên lỗ hổng theo KEV thế nào?”**; vai trò kỹ thuật hỏi **“Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì?”**. Mở nguồn để đọc hướng dẫn đầy đủ; chat chỉ tổng hợp trong giới hạn token.

Kiểm trích dẫn chỉ kiểm mã tài liệu thuộc nguồn được phép, không chứng minh mọi nhận định đúng. Nếu model khai báo nguồn trong JSON nhưng không gắn vào từng ý, ứng dụng hiển thị mục **Nguồn model sử dụng** để người đọc đối chiếu; không tự gắn một nguồn vào một nhận định cụ thể. Nguồn không hợp lệ vẫn chuyển sang trích đoạn tài liệu.

Kiểm tra bổ sung: `test_security.py` kiểm quyền, nguồn, thu hồi và độ liên quan của truy xuất; `check_readability.py` kiểm câu trả lời ATTT trên GPU, tiêu đề/danh sách, cỡ chữ/lưu lựa chọn, clipboard, tải Markdown, thu gọn, bộ lọc, liên kết nguồn và màn hình 390/768/1440px. Báo cáo tại `artifacts/readability-report.json`.

## Giá, tiến độ, SLA và tài chính — bộ dữ liệu mở rộng

`finance_data.py` tạo **154 tài liệu có trường dữ liệu và bản đọc được**, không lấy giá thương mại thật:

| Nhóm | Số lượng | Nội dung |
|---|---:|---|
| Gói trọn bộ | 20 | 12 gói hạ tầng + 8 gói ATTT; dòng thiết bị/license/công, thuế mô phỏng, duy trì và TCO |
| Lịch định mức | 12 | Ngày công từng công đoạn, ngày đệm, chờ hàng/duyệt và điều kiện |
| SLA chi tiết | 3 | P1–P4, cập nhật, mục tiêu khôi phục/onsite, bảo trì và tín dụng dịch vụ |
| Tài chính báo giá | 20 | Liên kết QUOTE/PROJECT, VAT mô phỏng, tổng trả và các đợt 40/40/20 |
| Chứng từ yêu cầu thu | 40 | Số phát hành, hạn thu, đã thu, còn nợ, ngày quá hạn |
| Phiếu thu | 27 | Phân bổ duy nhất vào chứng từ, có ngày và số tiền đối soát |
| Công nợ khách | 10 | Tổng và chi tiết dư nợ theo snapshot |
| Giá vốn nội bộ | 20 | Công nội bộ, đi lại, presales, lãi gộp và biên; chỉ admin |
| Báo cáo quản trị / quy ước | 2 | Danh mục đã nghiệm thu và công thức tài chính |

8 gói ATTT bổ sung: MFA, pilot Zero Trust/ZTNA, đánh giá lỗ hổng, pentest web được cấp quyền, khởi tạo SOC, retainer ứng cứu, pilot DLP và đào tạo nhận thức. Giá mới nằm ở **Tài chính demo / Gói trọn bộ**, còn tab **Dự toán dịch vụ** cũ giữ 12 định mức phí công ban đầu.

**VAT 10% là tham số giả lập để trình diễn công thức, không phải kết luận thuế suất hiện hành.** Tổng năm đầu/TCO trước thuế; giả định giá không đổi, không phát sinh quy mô. Chiết khấu chỉ áp vào phí công dịch vụ, luôn là đề xuất cần duyệt. Hệ thống tính bằng số nguyên VND trên backend; model không tự tính tiền.

### Các câu hỏi mẫu có số cụ thể

| Câu hỏi | Kết quả chính |
|---|---|
| Báo giá trọn gói firewall gồm thiết bị, license và VAT | 39.000.000 trước thuế, 3.900.000 VAT mô phỏng, 42.900.000 tổng; 4 ngày công, lịch 4–6 ngày làm việc/site |
| Firewall 2 site trọn gói chiết khấu 5% gồm VAT | Giảm 1.200.000 trên công, tổng 84.480.000; 8 ngày công |
| TCO 3 năm trọn gói firewall | 165.000.000 trước thuế cho 1 site, gồm 36 tháng BASIC và 2 lần gia hạn license |
| Triển khai MFA giá bao nhiêu và mất mấy ngày? | 10 triệu công + 5 triệu license lab, 16,5 triệu gồm thuế mô phỏng; 4 ngày công |
| Chi tiết thanh toán QUOTE-A-01 gồm VAT | 13,2 triệu tổng, các đợt 5,28 / 5,28 / 2,64 triệu |
| Công nợ An Minh Retail còn bao nhiêu? | Tổng đã phát hành 14,08 triệu, thu 8,8 triệu, dư 5,28 triệu tại snapshot |
| SLA PLUS chi tiết về khôi phục và bồi hoàn | P1 phản hồi 1 giờ; mục tiêu khôi phục 8 giờ có điều kiện; 130.000 tín dụng cho 1 vi phạm phản hồi P1 được xác nhận/site, trần 650.000/tháng/site |
| Phân bổ ngày công chi tiết firewall | 1 ngày khảo sát/thiết kế + 2 triển khai + 1 kiểm thử/bàn giao |
| Lợi nhuận danh mục đã nghiệm thu là bao nhiêu? (admin) | Doanh thu trước thuế 255 triệu, giá vốn 125,15 triệu, lãi gộp 129,85 triệu; sau phân bổ quản lý 94,85 triệu trước thuế mô phỏng |

Sổ thu tiền toàn bộ 10 khách trong snapshot: phát hành **347.820.000**, đã thu **179.190.000**, còn phải thu **168.630.000 VND**. Các đợt còn dư đều quá hạn tại ngày 05/09/2026 trong kịch bản này. Sale/kỹ thuật chỉ thấy nhóm khách được phân công. Sổ này chưa gồm thu định kỳ bảo trì, mua hàng nhà cung cấp, tồn quỹ, tài khoản ngân hàng hay sổ cái kế toán đầy đủ.

Phí công trong QUOTE cũ và OFFER trọn bộ là hai phạm vi khác nhau; không tự cộng OFFER vào báo giá đã ký. Chứng từ thu không phải hóa đơn điện tử và không phát sinh giao dịch. P&L là danh mục 10 dự án đã nghiệm thu, không phải báo cáo toàn công ty. Các ngày là snapshot, không phải lịch nhân sự tự cập nhật.

Nguồn dẫn xuất có `requires`: nếu tài liệu giá/thiết bị/báo giá gốc bị thu hồi hoặc hết hiệu lực, gói và hồ sơ phụ thuộc ngừng được tra cứu/tính. Bản lưu JSON/Markdown vẫn ở máy; quản trị có thể đọc tài liệu thu hồi để kiểm tra. Tổng dashboard cộng các chứng từ hiện được phép xem.

### Vị trí dữ liệu và kiểm thử

- `data/finance_documents.json`: toàn bộ 154 tài liệu và các trường số; `data/finance_documents/`: từng bản Markdown; `data/finance_manifest.json`: số lượng và quy ước.
- `finance_data.py`: tái tạo bộ giả lập (sao lưu trước); giữ upload và trạng thái thu hồi của bản đã tạo. Nếu đổi dữ liệu công ty nền, cần rà soát và tái tạo bộ tài chính để giữ liên kết, không chỉ sửa một tổng tiền ở file JSON.
- `finance_logic.py`: tính dự toán, TCO, tổng thu/nợ và định tuyến câu hỏi; `static/finance.js`: bảng điều khiển.
- `test_finance.py`: đối soát từng chứng từ/phiếu thu, mốc 40/40/20, giá, thuế mô phỏng, TCO, ACL và thu hồi nguồn.
- `check_finance_ui.py`: kiểm giao diện ở 390/768/1440px, 20 gói, 5/10 khách, giá vốn chỉ admin, tính 2 site và hỏi công nợ/SLA.
- Bằng chứng: `artifacts/finance-report.json`, `14-finance-dashboard.png`, `15-finance-mobile.png`, `16-finance-admin.png`.
