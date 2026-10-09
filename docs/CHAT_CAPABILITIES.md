# Chat: file riêng, đọc URL và SOW/BOM đầy đủ

Phiên bản code `2026.10.09-chat-tools-1`. Giữ FastAPI/SQLite/JS/OpenRouter.
Code được kiểm thử offline; chưa triển khai/migrate/restart dữ liệu đang chạy.

## SOW/BOM và trả lời chi tiết

- Migration/quy trình/giờ công route dịch vụ, không route cấu hình firewall.
- SOW/BOM dùng danh mục record trong corpus được phép: dịch vụ đơn, nhiều dịch vụ,
  hoặc toàn công ty khi hỏi “tất cả SOW và BOM của công ty”. Không áp top-k cho
  phần danh mục. Giữ từng ID, phiên bản, vị trí nguồn, body; không tự gộp gói khác nhau.
- UI có bảng danh mục xác định bằng code và toàn văn mỗi record, độc lập với câu
  tổng hợp của model. Diagnostics ghi available/displayed/sent IDs/digests/version.
  Type marker và tên nguồn **không xác minh nội dung hoặc cam kết**.
- Chưa có bộ SKU/số lượng/giá có thẩm quyền trong corpus. BOM rules không phải
  BOM thương mại đầy đủ; không tự điền phần thiếu. Đây là danh mục nguồn đầy đủ,
  chưa phải bảng thương mại chuẩn hóa tự động theo schema line-item.

## Ngân sách và reasoning

Mặc định mới: `RAG_INPUT_BYTES=192000`, `RAG_OUTPUT_TOKENS=16000`, `RAG_TOP_K=48`.
Không ép thấp câu chuyên môn; concept tối đa 32000 byte/4000 output/6 nguồn,
file/URL dùng configured cap. Giá trị `.env` cũ vẫn giữ nguyên: **cập nhật code
không tự tăng ngân sách runtime**. Admin chọn giá trị phù hợp quota/timeout/model;
không chép `.env.example` đè `.env` đang dùng.

`RAG_MODEL_LIMITS` JSON model -> context_tokens/output_tokens clamp output
và input theo context - output - 1024. Input vẫn **UTF-8 byte proxy bảo thủ, không
tokenizer chính xác**. Provider usage settle số token thật; chưa có tokenizer
model-aware mọi model. Plugin search thêm input phía provider ngoài proxy local.

`RAG_REASONING=auto` không ép tắt reasoning và loại trace khỏi đáp án; enabled/
disabled override. `RAG_REASONING_EFFORT` trống hoặc minimal/low/medium/high cần
model hỗ trợ. Không ép temperature. **Chưa kiểm live endpoint reasoning**; nếu
không tương thích chọn disabled, không tự retry call tính phí. Dùng OpenRouter
spend limit; reasoning có thể tiêu thụ output/chi phí.

## File đính kèm theo hội thoại

TXT/Markdown/CSV UTF-8; PDF text; DOCX/XLSX/PPTX OOXML. Tối đa 10 MB/file,
10 file/50 MB mỗi chat, 200 MB mỗi tài khoản; 1 triệu ký tự/2000 phần trích xuất,
PDF tối đa 500 trang, ZIP tối đa 40 MB giải nén. Vượt giới hạn fail, không lưu
bản cắt thiếu. Parser chạy subprocess Python hiện có, timeout 30s và kill khi cancel.
Không tạo environment/dependency mới.

- DOCX: đoạn/bảng theo thứ tự, header/footer/footnotes có vị trí.
- Excel: sheet/hàng/ô, merged ranges, formula/cached value có nhãn; **không tính
  lại formula**, không gọi external relationships, không biến X thành quantity.
- PPTX: slide/notes; PDF từng trang, không còn giới hạn 30 trang như upload admin.
- Không OCR/vision ảnh/sơ đồ; scan không text cần OCR bên ngoài. Legacy
  DOC/XLS/PPT, encrypted files/macros không nhận. Tài liệu phức tạp có warning.
- Unit citations FILE-ID, modal chỉ owner được đọc; tài khoản admin khác không
  được API file. Không nhập corpus/chia sẻ chat khác. File ngắn gửi nguyên đơn vị;
  file dài retrieval theo phần, luôn báo available/sent khi không đủ context.
- Nội dung file **gửi tới model provider** khi hỏi. Chỉ tải dữ liệu được phép.
  Raw/extracted lưu SQLite; backup chứa dữ liệu riêng. Xóa file làm câu trả lời
  phụ thuộc không còn hợp lệ; xóa chat xóa file. Backup cũ không bị xóa theo.
  SQLite delete không bảo đảm forensic erase; bảo vệ storage/backup theo chính sách.
  Feedback/admin history có thể redact file evidence vì không thuộc corpus chung.

### Nâng cấp dữ liệu cũ (operator, không chạy tự động)

Attachment schema v1 bổ sung trong conversations DB; layout sáu kho v1 giữ nguyên.
Init/migrate đích mới có tables. Runtime cũ vẫn chạy nhưng upload trả 409 hướng
dẫn upgrade. **Không ALTER/CREATE attachment schema ở startup**.

1. Dừng instance, xác định `.env`/APP_DATA_DIR thật, giữ backup nguồn ngoài project.
2. Interpreter/environment hiện có, từ root project:

```bash
python -B -m cyberant.operations backup --target /srv/cyberant-backups/pre-chat-files
python -B -m cyberant.operations upgrade-attachments --target /srv/cyberant-data-chat-files
```

Đích phải mới/chưa tồn tại, thay absolute paths theo máy thật. Windows có thể dùng
`D:\CyberAnt-private\backups\pre-chat-files` và `D:\CyberAnt-private\runtime-chat-files`.
Upgrade snapshot nhất quán, thêm schema trên **đích**, không đổi nguồn. Trỏ
APP_DATA_DIR sang đích sau xác minh, `operations check`, restart và kiểm owner/
API/browser/backup. Không init/legacy migrate/restore mù đè data đang chạy. Rollback
giữ code/data pair cũ; dữ liệu phát sinh sau chuyển đích cần bảo toàn riêng.

## Đọc URL và search Internet

URL trong câu hỏi hoặc trường URL công khai (tối đa 3/lượt). Chỉ HTTPS cổng 443
không userinfo. DNS-check **mọi** IP; từ chối private/loopback/link-local/metadata/
multicast/reserved/IPv4-mapped; ghim TCP vào IP đã kiểm, TLS/Host giữ hostname gốc.
Mỗi redirect kiểm lại với pool mới, tối đa 5 hops/tổng 90s; không proxy/env/cookie/
auth/JS. Adapter dùng httpx 0.28.1/httpcore 1.0.9 trong lockfile; upgrade thư viện
phải rerun SSRF tests.

HTML tĩnh/text/PDF/Office qua extractor, 10 MB body; không nhận gzip bất chấp
Accept-Encoding identity để tránh decompression bomb. Paywall/login/JS/format lỗi
báo unreadable. WEB-ID, URL/thời điểm/units sent rõ; không tuyên bố đã đọc hết nếu
thiếu context. Không vào corpus. **URL có secret query token vẫn có thể bí mật
dù hostname public: không cung cấp những link đó**.

Search chỉ truy vấn public identifiers, không gửi file/lịch sử/source text vào
search. Default 5 kết quả (1–10), 1600 output (256–4000), nguồn tối đa 12000 ký tự.
Vẫn tối đa một lookup + hai completion, chưa multi-step autonomous search. Direct
URL không tự thêm paid search trừ query explicit. Fetch URL không gọi model,
nhưng synthesis vẫn tính phí.

## Tiến trình, dừng và lịch sử

UI `/api/chat/stream` SSE các bước thật: file, URL/search, tổng hợp, kiểm citation/
lưu. Kết quả chỉ phát sau validation, **không stream token model chưa kiểm chứng**.
`/api/chat` JSON vẫn tương thích. Dừng/disconnect cancel task và parser/provider
đang chờ; call đã gửi có thể tính phí, usage giữ uncertain nếu thiếu actual usage.
Không retry; kiểm lịch sử/usage trước gửi lại. Nếu đã lưu ngay trước disconnect,
mở lại chat để đọc. Tiếp tục dùng call/quota riêng. Proxy cần body limit >10 MB và
không buffering SSE (nginx example cập nhật).

## Kiểm chứng và phần còn lại

Offline tests API/browser/extractors/owner/revoke/backup/schema upgrade/URL/stream
cancellation. Public HTTPS smoke example.com đọc được; không generation paid.
Live server/Linux/proxy/provider/quota/cost và chất lượng đáp án chưa nghiệm thu.
OCR/vision, exact tokenizer, model-token streaming, multi-step search và commercial
normalized BOM là bước tiếp theo riêng.