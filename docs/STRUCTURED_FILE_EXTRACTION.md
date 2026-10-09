# Trích xuất Word/Excel có cấu trúc

Checkpoint 12, extraction JSON v2. Giữ parser thư viện chuẩn OOXML và `pypdf`,
subprocess Python hiện có, không cài Office/dependency hoặc chạy macro/công thức.
Đây là cải thiện đọc bằng chứng, không chứng nhận dữ liệu nghiệp vụ hoặc đáp án AI.

## Định dạng và tương thích

Mỗi phần vẫn có `location` và `body` (text trích xuất). Word/Excel bổ sung
`structure`: dữ liệu có kiểu, vị trí và các dấu hiệu cần kiểm tra. `extraction_version`
là 2. Database attachment schema giữ v1, không cần migration riêng cho thay đổi này.
File đã lưu từ extractor v1 tiếp tục đọc theo cách cũ, không tự trích xuất lại.
Muốn có metadata mới cho file cũ, người dùng tải lại file theo chính sách lưu trữ.
Những bản cài chưa có attachment schema vẫn cần nâng cấp riêng theo CHAT_CAPABILITIES.

Evidence body dùng cho retrieval/model và digest gồm text **cộng metadata cấu trúc**.
Vì vậy trạng thái ẩn, công thức/cache và header không chỉ nằm trong SQLite.
Owner file endpoint `/api/documents/FILE-…` trả `extracted_text`,
`extraction_structure`, body evidence và provenance. Không chia sẻ sang chat/tài
khoản khác. URL công khai trả Office cũng dùng cùng evidence renderer.
Metadata tăng input; RAG budget tính trên body thực, không giả định gửi được hết.
UI có nút **Preview / chọn phạm vi** cho từng file: xem20 phần/trang, text và
metadata, chọn/bỏ từng phần hoặc cả file. Các phần Excel theo hàng/sheet, Word
theo đoạn/hàng bảng. Chọn chỉ giữ trong trình duyệt cho chat hiện tại; đổi chat
reset phạm vi, không lưu database. Chưa có range expression hoặc tự đoán header.

API owner `/api/conversations/{id}/attachments/{file_id}/preview?offset=0`
trả tối đa20 phần. Chat nhận `file_unit_ids`: `null`/không gửi nghĩa tất cả,
`[]` nghĩa không gửi phần file; IDs sai/khác chat bị từ chối trước gọi model.
Server loại lịch sử có dependency ngoài phạm vi chọn trước packing; một phần
vẫn có thể bị budget loại dù đã chọn. Kết quả có `file_scope` và coverage thật.
Đây là phạm vi **file**, không tắt nguồn nội bộ/URL được yêu cầu. Lịch sử cũ chưa
có dependency đầy đủ không thể bảo đảm loại mọi thông tin đã từng dùng.

## Word DOCX

- Thứ tự khối, heading path từ outline level (kể cả style kế thừa).
- Giữ tab/xuống dòng và metadata list `numId`/`ilvl`; chưa render số thứ tự danh sách.
- Đọc text bản hiện hành: gồm insert/moveTo, loại delete/moveFrom. Có warning khi
  tracked changes; không có nghĩa các sửa đổi được duyệt. Không cung cấp diff revisions.
- Mỗi hàng bảng là phần nguồn riêng; cell giữ cột grid, gridSpan và vertical merge.
  Không tự sao chép text/số từ ô merge tiếp nối. Chỉ giữ header được OOXML đánh dấu,
  không đoán hàng đầu là header.
- Footnote/endnote/comment là phần riêng có ID; paragraph giữ note/comment refs.
  Header/footer tách khỏi nội dung chính. Chưa phân giải tham chiếu trong mọi cell bảng.
- Không hứa số trang Word: location theo mục/khối/hàng vì không render font/layout.
- Bảng lồng/khối không hỗ trợ có warning. Ảnh/textbox/objects không được phân tích;
  không coi sự hiện diện của text là đọc toàn bộ hình hay bố cục tài liệu.

## Excel XLSX

- Mỗi hàng giữ sheet/hàng và danh sách ô có địa chỉ; raw OOXML value luôn được giữ.
- Shared/inline string giữ mã text có số 0 đầu. Format `00000` trên số nguyên cung
  cấp display bảo thủ, không biến mã thành quantity.
- Phân biệt ô blank lưu trong XML, số0, boolean, error và text. Ô không tồn tại trong
  XML không tự sinh hoặc điền0. Hàng không có cell có metadata riêng.
- Formula expression/attributes và cached value tách biệt. Shared formula chưa tự
  dịch sang ô khác; missing cache và cache chưa xác minh đều được đánh dấu.
- Diễn giải số bằng Decimal dạng chuỗi, phần trăm ratio/percent_value, currency
  marker trong format. Marker `$` không chứng minh USD hoặc loại tiền giao dịch.
- Ngày theo workbook1900/1904, serial60 của1900 được đánh dấu ngày Excel giả;
  không chuyển thành ngày có thật. ISO/date diễn giải không tự suy timezone.
- Định dạng phức tạp/conditional/duration hoặc format chưa hỗ trợ có status rõ;
  **không phải bộ render số Excel đầy đủ**. Không tự áp locale/làm tròn/thuế/tỷ giá.
- Sheet state/hàng ẩn/cột ẩn/bộ lọc được giữ. Đọc cả dữ liệu đã lưu, không tính là
  chỉ phần hiển thị. Không áp bộ lọc hoặc tự quyết định phạm vi tổng.
- Header/table range/totals row count chỉ lấy từ declared Excel tables, không suy
  diễn cột nghiệp vụ từ dòng đầu. Sheet không có hàng được đánh dấu empty_sheet.
- Merged ranges không tự điền số lượng; external links không được truy cập.
  Không xử lý pivot/charts/embedded objects như bảng dữ kiện hoàn chỉnh.

## Giới hạn an toàn và kiểm thử

Giữ10MB/file,40MB OOXML giải nén,2000units,1triệu ký tự text,30s subprocess và
reject ZIP traversal/macros/XML DTD/entity. JSON kết quả giới hạn8MB, một phần
evidence tối đa100KB; quá giới hạn fail rõ, không lưu bản cắt thiếu. Không sandbox
bộ nhớ cấp OS. Không tự tăng quota/ngân sách vì metadata lớn hơn.

Synthetic tests bao phủ heading/list/revision/notes, merged header/table row,
blank/0/error/formula missing cache/sharedformula, dates1900/1904/serial60,
percentage/currency/leadingzeros,hidden/filter/declaredtable/external,
invalidcell/style/sharedstring,limits,async subprocess và v1/v2 dependency digest.
Owner/backup/history/URL SSRF/package suites vẫn cần chạy tách process.
Chưa live generation hoặc dùng file khách hàng ở checkpoint này.

## Tiếp theo

Checkpoint13: search free-tier có ngân sách/quyền riêng tư, không tự bật paid plugin.
Checkpoint14: corpus nghiệp vụ sales/thuật ngữ có nguồn và quy trình duyệt.
Checkpoint15: range/column mapping nâng cao, phép tính xác định/so sánh file và đối chiếu SOW/BOM.
PDF bảng/multi-column/OCR, PPTX table và CSV locale/delimiter nâng cao còn ở bước
mở rộng; hiện PDF vẫn text theo trang, PPTX text/notes, CSV UTF8/comma. Không công
bố toàn bộ roadmap hoàn thành hoặc khả năng reasoning đã được kiểm chứng.