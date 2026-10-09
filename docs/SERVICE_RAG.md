# SOW/BOM và bằng chứng theo dịch vụ

> Cập nhật 2026-10-05: nội dung baseline/chi phí dưới đây ghi kết quả phiên cũ.
> Runtime hiện là layout split `D:\TestSystem\data`; 1.100 draft đã accepted theo
> quyết định user. Ngân sách mới và retrieval cấu hình xem CONFIGURATION_GUIDES.md;
> acceptance/backup xem KNOWLEDGE_ACCEPTANCE.md. Các số 18.000/2.400 và trạng thái
> draft trong báo cáo cũ không còn là cấu hình hiện hành.

## Phạm vi triển khai

- Liên kết dịch vụ trong chỉ mục bằng `cyberant/service_evidence.py`: service ID
  có sẵn, tên DOCX cũ và ID workflow được ánh xạ rõ ràng. Không sửa 1.200 bản ghi,
  checksum, body hoặc trạng thái duyệt; không tự ghi/sync database.
- Intent `sow`, `bom`, `sow_bom`, giữ câu định nghĩa chung ở ngân sách khái niệm.
- Retrieval ưu tiên bao phủ loại bằng chứng cùng dịch vụ, trong `RAG_TOP_K` hiện
  hữu; không mở rộng ngoài danh sách tài liệu caller được phép dùng.
- Phân loại `evidence_origin` transcribed/calculated/authored/mixed/reference và
  giữ source location khi có trong metadata; không tự tạo revision chưa có.
- Packing ưu tiên phần chưa có bằng chứng, giữ nguyên đoạn, ghi lý do bỏ nguồn.
- API chat nhận `audience`: `auto` (mặc định), `sales`, `engineering`. Đây là lựa
  chọn trình bày, không phải vai trò phân quyền. UI luôn auto theo nhiệm vụ hiện tại;
  ngữ cảnh nối tiếp hợp lệ dùng routing hiện có, không lấy profession từ tài khoản.
- Prompt theo đối tượng, giữ cảnh báo draft, SKU/giá/SLA chưa xác nhận, man-hour
  khác downtime, dấu X khác số lượng và nguồn mâu thuẫn cần chốt phạm vi.

`coverage`/`packed_coverage` chỉ đo **loại bằng chứng** theo data_type và marker,
không chứng nhận đủ từng công việc hay ngữ nghĩa. `grounding_verified` vẫn false.
Có marker nghiệm thu không chứng minh toàn bộ tiêu chí đã được duyệt. Nhãn
`status=approved` cho phép truy xuất, không nâng `draft_engineer_review`.

## Chi phí

Không tăng trần cấu hình toàn cục. SOW/SOW+BOM dùng tối đa 18.000 byte proxy /
2.400 token ra; BOM 14.000 / 1.800; luôn bị chặn bởi cấu hình. Chọn ít nguồn hơn
nếu không đủ căn cứ, không lấp bằng dịch vụ khác. Một lần gọi model, không retry
hay model chấm điểm. Usage provider mới là token thực và chi phí thực; chưa có
benchmark trả lời thật hoặc kết luận tiết kiệm tiền. Prompt hash ghi prompt thực
theo đối tượng, không chỉ hash prompt nền.

## Kiểm tra read-only

Ví dụ Windows dùng Python đã cài trên máy, không cần venv (thay đường dẫn
tương ứng trên Linux). Không tự cài/nâng cấp thư viện nếu thiếu dependency:

```powershell
& 'C:\Users\anhna\AppData\Local\Microsoft\WindowsApps\python3.13.exe' -B 'D:\TestSystem\tools\audit_service_sources.py' --source-dir 'D:\TestSystem\data'
& 'C:\Users\anhna\AppData\Local\Microsoft\WindowsApps\python3.13.exe' -B 'D:\TestSystem\tools\audit_service_sources.py' --runtime-db 'D:\TestSystem\data\app.sqlite3'
& 'C:\Users\anhna\AppData\Local\Microsoft\WindowsApps\python3.13.exe' -B 'D:\TestSystem\tools\audit_service_sources.py' --evaluate
```

Công cụ in JSON ra stdout, không ghi file, không import app, không init/migrate/
sync, chỉ mở DB rõ đường dẫn với `mode=ro` và `query_only`. Không xuất nội dung
chat/tài khoản hay API key. So sánh ID/body/payload, nhận diện retired được giữ;
runtime-only có thể là upload hoặc nguồn cũ, không mặc định là lỗi/xóa.

Nguồn DOCX: kiểm sự hiện diện text phần thân, không chứng minh bảng đúng quan hệ.
Excel: kiểm sheet, merged cell, công thức và cached value; không thực thi công
thức hoặc chứng nhận cache cập nhật. Bảng migration nhân duration × engineers
và cộng bằng Python; không suy ra thời gian thực/downtime. PDF: đếm trang/text,
chưa chứng minh mũi tên/nhánh. PNG vẫn cần người kiểm/OCR, không dùng như SLA.

## Baseline/runtime chưa triển khai

Thư mục phát triển `D:\TestSystem\data` còn DB legacy; code hiện tại yêu cầu
layout tách riêng. Báo cáo một file DB không xác định cấu hình tiến trình đang
phục vụ. Không tự restart, migration hoặc triển khai live. Cần người vận hành
xác nhận env file/data dir/version của instance, backup nhất quán, migration vào
đích mới nếu cần, rồi sync nguồn bằng thao tác quản trị đã có.

## Đánh giá

`knowledge/evaluation_services.json`: 12 câu offline có ID/type kỳ vọng và 28 câu
chấm tay với tiêu chí. Đây là tập development, **không phải holdout mù**. Offline
chỉ chứng minh intent/truy xuất/packing, không chứng minh đáp án AI hoặc citation
entailment. Tập chấm tay chưa tự tính pass. Chạy unittest trước; đánh giá model
thật cần ngân sách duyệt riêng, sales/kỹ sư chấm nhận định và usefulness.

Mục tiêu nghiệm thu sau khi có gold review: ≥90% bằng chứng bắt buộc có sẵn được
giữ; không bịa giá/SKU/SLA/số lượng/downtime; ≥95% nhận định có nguồn hỗ trợ;
usefulness ≥4/5. Đo token p50/p95 và chi phí trên câu trả lời đạt, không chỉ lượt.

## Công việc cần kỹ sư/owner thực hiện

1. Đối chiếu đủ ô/bảng/nhánh gốc, duyệt ba bộ Managed Service/FortiGate/migration.
2. Bổ sung quy tắc BOM đã duyệt, catalog SKU/license/đơn vị và điều kiện effort.
3. Bổ sung owner/revision/hash nguồn và trách nhiệm, exclusions, acceptance còn thiếu.
4. Xử lý thuật ngữ trùng theo ngữ cảnh, không gộp chỉ theo tiêu đề.
5. Chốt thẩm quyền duyệt thương mại/kỹ thuật, holdout độc lập và benchmark có phí.

Không dùng công cụ audit hoặc thay đổi routing để tự đánh dấu các việc này hoàn tất.

## Kết quả kiểm tra bản triển khai trong repository

- 28 test đạt, gồm 12 test service mới và 16 test storage/HTTP/share/API/browser.
  Các suite chạy process riêng theo yêu cầu isolation của test UI; provider giả lập.
- 12/12 câu offline đạt intent, service, ID/type kỳ vọng. Giữ 100% **loại bằng
  chứng bắt buộc có sẵn** trong từng ca; đây không phải 100% chi tiết SOW hay
  accuracy của đáp án. Context khoảng 10.830–12.330 byte proxy, không token thật.
- Audit 17 file nguồn không có lỗi đọc. Sáu DOCX không thiếu text run phần thân
  theo kiểm tra hiện diện; bảng/ảnh/header/footer vẫn chưa được xác minh.
- Bảng migration tính lại 27,5 man-hour và 25,75 tổng giờ công việc. Không phải
  downtime/thời gian dự án; cache Excel và tính áp dụng dự án chưa được duyệt.
- File legacy `D:\TestSystem\data\app.sqlite3` có 1.200 ID, body, payload và
  digest `source_sync` khớp repository. Layout split chưa có ở thư mục local này;
  chưa xác nhận version/env của process live, không migration/sync/restart.
- Syntax Python/JavaScript, `git diff --check` và gói release allowlist đạt;
  gói thử ở thư mục tạm đã xóa, không chứa `.env`, DB hoặc dữ liệu runtime.

Không gọi provider thật. 28 câu chấm tay chưa chạy; chưa đo claim support,
usefulness, chi phí thực hoặc p50/p95. Không tuyên bố đạt các mục tiêu đó.