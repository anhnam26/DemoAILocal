# Rà soát kho tri thức và RAG — 30/09/2026

## Phạm vi thực sự hoàn tất

Đây là đợt triển khai nền tảng và bổ sung kiến thức đầu tiên, **không phải chứng nhận đã rà soát kỹ thuật toàn bộ kho**.

- Kiểm kê tự động toàn bộ 1.194 bản ghi ban đầu, lưu hàng đợi theo từng ID trong `D:\TestSystem\docs\knowledge-baseline.json`. Không biến thiếu nguồn hoặc ô khảo sát trống thành dữ kiện thật.
- Đối chiếu báo cáo build và schema glossary trong `D:\CyberAnt-Local-Archive-20260928\NewData\data`; chưa đối chiếu thủ công mọi ô của toàn bộ Word/Excel/PDF gốc.
- Chuẩn hóa `content_kind` cho các bản ghi; giữ ID, quyền và nhãn bản nháp cũ. Tách định nghĩa glossary khỏi phần vận hành khi dựng chỉ mục, không xóa nội dung gốc khỏi corpus.
- Viết lại TCP theo RFC 9293; thêm 5 bài: OSI/TCP-IP, DNS, chẩn đoán DNS, UDP, DHCP IPv4. Đã đọc nguồn RFC 1122/9293/1034/768/2131 và IBM OSI. Trang Cloudflare trả 403 nên không dùng làm nguồn đã kiểm tra.
- Bỏ dòng giá DEMO trong CMP-FW-WAF; không xóa các ví dụ kỹ thuật hoặc tự điền cam kết dịch vụ. Tổng hiện tại 1.199 bản ghi.
- Nâng truy xuất từ/ký tự bằng stopword, tiêu đề, bí danh Việt/Anh và loại câu hỏi; giảm nhiễu biểu mẫu và hướng dẫn cấu hình trong glossary.
- Giữ trọn đơn vị bằng chứng khi đóng gói. Không còn cắt dòng cuối hoặc xóa bước/cảnh báo trùng giữa các nguồn. Tài liệu upload quá dài có thể không vừa ngân sách: cần chia thành bài độc lập, không coi đó là nguồn đã được gửi.
- Thay fallback đổ hai đoạn nguồn bằng thông báo trích dẫn chưa hợp lệ. Cho phép câu từ chối chuẩn không có mã nguồn. Không giữ nguyên tùy ý mọi câu trả lời không có trích dẫn chỉ vì nó chứa từ “thiếu”.
- API trả `citation_status`, `grounding_verified=false`, `finish_reason`, `output_token_limit`, số đoạn truy xuất/giữ/bỏ. UI nói rõ kiểm mã ID không phải kiểm chứng nội dung.

## Ngân sách và chi phí

Không cài thêm tokenizer/model/embedding hoặc thư viện mới. Chưa có dữ liệu đủ lớn để hiệu chỉnh token riêng từng model một cách đáng tin cậy.

| Loại câu hỏi (heuristic) | Trần byte proxy đầu vào | Trần token đầu ra |
|---|---:|---:|
| Khái niệm | 8.000 | 1.000 |
| So sánh / khảo sát | 14.000 | 1.800 |
| Quy trình / chẩn đoán | 18.000 | 2.400 |

Các mức luôn bị chặn bởi cấu hình `.env`. `RAG_INPUT_TOKENS` giữ tên cũ để tương thích nhưng **đơn vị thực tế là byte UTF-8 cộng overhead**, không phải token chính xác, cũng không phải upper bound tuyệt đối của provider. Tăng trần không có nghĩa luôn gửi đầy trần, nhưng có thể tăng chi phí; chưa tuyên bố tiết kiệm tiền sau thay đổi.

Chat yêu cầu giữ đủ ngân sách đầu ra mục tiêu; quota thiếu sẽ chặn trước API thay vì âm thầm rút xuống 64 token. Ledger vẫn ghi usage thực, giữ trạng thái uncertain khi lỗi mạng và không tự retry. Không thay model theo giá. `reasoning.enabled=false` là yêu cầu gửi provider, không bảo đảm mọi model hỗ trợ giống nhau.

Usage đã đọc trước thay đổi: cùng ước lượng 5.888, provider báo prompt 1.408 (NVIDIA), 1.345 (Qwen), 1.907 (DeepSeek), 6.019 (OpenAI). Mẫu nhỏ, không suy ra hệ số hay bảng giá chung. Cần đo thêm tỷ lệ trần đầu ra, chi phí/token thực và tỷ lệ trả lời đạt yêu cầu theo model; không chỉ so giá mỗi lượt.

## Đánh giá

`D:\TestSystem\knowledge\evaluation.json`: 108 câu, gồm 52 câu gốc và biến thể bỏ dấu (104 câu có ID nguồn kỳ vọng), thêm 4 tình huống thiếu căn cứ **chưa chấm tự động**. Bao phủ 13 nhóm chủ đề/mục đích. Đây là smoke test ID nguồn, chưa có đáp án chuyên gia chấm từng nhận định.

Dùng cùng top-k 6 và ngân sách đóng gói 12.000 byte để so sánh offline:

- Trước thay đổi: 74/104 tìm và giữ được nguồn kỳ vọng.
- Sau thay đổi: 102/104 tìm và giữ được nguồn kỳ vọng.
- Hai miss còn lại là câu đổi DNS vẫn nhận địa chỉ cũ (có dấu/không dấu). Nguồn DNS chung có xuất hiện nhưng bài chẩn đoán kỳ vọng chưa lọt top-k.

Không coi 98,1% là độ chính xác trả lời AI. Biến thể bỏ dấu tương quan cao; trường `holdout` chỉ dành phân tách về sau, đã quan sát kết quả nên không còn là đánh giá mù độc lập. Mẫu 4 negative không tính thành pass giả. Cần tập holdout mới do người khác biên soạn trước nghiệm thu.

## Triển khai và an toàn dữ liệu

Chưa khởi động lại ứng dụng, chưa ghi vào database thật, chưa gọi AI thật có phí. Pytest dùng thư mục database tạm. Source JSON vẫn là nguồn chuẩn và sẽ đồng bộ khi startup hoặc admin chọn đồng bộ kho tri thức.

Trước áp dụng: tạo SQLite backup nhất quán bằng chức năng snapshot hiện có, lưu riêng; triển khai source mới, khởi động lại một worker, kiểm tra đồng bộ. Không copy đè database bằng DB test. Cơ chế hiện tại giữ nguồn đã retired. Khi body thay đổi, lịch sử tham chiếu digest cũ có thể hiện thông báo yêu cầu hỏi lại; không tự sửa câu trả lời cũ cho khớp nguồn mới.

## Công việc còn lại, không được đánh dấu hoàn tất

1. Rà soát kỹ thuật hàng đợi ~1.100 bản nháp; hợp nhất thuật ngữ theo ngữ cảnh, không gộp chỉ vì trùng tiêu đề.
2. Đối chiếu đủ nguồn gốc và mở rộng kiến thức nền về VLAN/routing/subnet, firewall/VPN, storage/RAID/ảo hóa, dịch vụ và nghiệm thu theo khoảng thiếu.
3. Bộ đáp án chuẩn có tiêu chí nội dung, câu nhiều ý, thiếu phiên bản, mâu thuẫn và tiếp nối hội thoại; hiện follow-up vẫn chỉ dựa chủ đề trước có giới hạn.
4. Tokenizer/model calibration, kiểm tra context limit chính thức và benchmark AI thật từng model theo ngân sách được duyệt. Không tự thêm model đánh giá cho mọi request.
5. Nếu benchmark độc lập cho thấy còn thiếu recall, thử semantic retrieval/reranker riêng, đo lợi ích trước khi thêm dependency vào runtime.

Chạy lại: `python -B D:\TestSystem\knowledge_quality.py --output D:\TestSystem\docs\knowledge-after.json`. Script không import app, không mở SQLite, không gọi provider.
