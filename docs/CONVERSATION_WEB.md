# Ngữ cảnh hội thoại và tra cứu Internet

## Bộ nhớ
Hỏi–đáp lưu theo tài khoản và conversation_id. Mở lại chat giữ ngữ cảnh; chat mới
không lấy lịch sử chat khác. Mỗi lượt xét tối đa 80 cặp gần nhất: ưu tiên 6 cặp mới
và cặp cũ liên quan, giữ cặp nguyên vẹn trong tối đa 1/3 ngân sách input.
Không gửi lượt dùng nguồn đã thu hồi/thay đổi hoặc mã nguồn chưa có digest.
Nguồn phụ thuộc qua ngữ cảnh được lưu vào JSON context_sources (không đổi schema),
để câu tóm tắt tiếp nối không vô tình giữ dữ kiện của nguồn đã thu hồi.
Diagnostics packing ghi ID lượt được gửi và số lượt bỏ qua, không phải bộ nhớ vô hạn.

## Chính sách trả lời
Ưu tiên nguồn nội bộ liên quan. Cho phép giải thích kiến thức chung hoặc chỉnh sửa
nội dung trước đó, ghi rõ chưa đối chiếu nguồn khi không có citation. Lịch sử AI
không phải nguồn sự thật. Không bịa giá, SLA, khách hàng, hợp đồng, phiên bản/lệnh.
Thông tin cập nhật không có citation hợp lệ sẽ bị thay bằng thông báo chưa xác minh.
Kiểm mã nguồn/URL không chứng minh rằng từng nhận định được nguồn hỗ trợ.

## Web
OpenRouter web plugin, engine Exa, tối đa một lookup và hai completion mỗi request.
Không thay model/permission; không retry tự động. Khi bật, lookup tự động cho câu
hỏi cập nhật hoặc câu ngoài kho không thuộc định nghĩa, trừ yêu cầu nối tiếp.
Nếu model báo thiếu bằng chứng bằng tín hiệu NEED_WEB sau lượt nội bộ, thực hiện
một lookup rồi tổng hợp lại khi có evidence; không coi đây là retry lỗi provider.
Truy vấn tự động chỉ ghép tên chủ đề công khai nhận diện được và mục đích chung;
không gửi nguyên câu hỏi, lịch sử, tên khách hàng, IP hoặc tài liệu nội bộ vào search.
Điều này giảm rò rỉ nhưng truy vấn có thể thiếu cụ thể. Người dùng có thể nhập truy
vấn công khai riêng trong mục Tra cứu Internet; phải tránh dữ liệu nhạy cảm.
Không tự tạo truy vấn từ toàn bộ chat và không có bộ phân loại DLP tuyệt đối.

Lookup riêng không chứa lịch sử/tri thức. Chỉ dùng đoạn `content` của provider
`url_citation` cùng URL HTTPS hợp lệ làm evidence. Không dùng lời tóm tắt của model
lookup làm bằng chứng. Thiếu extractive content thì báo không có nguồn hợp lệ.
Nguồn web không được nhập vào kho hay nâng thành nguồn đã duyệt. UI hiển thị URL,
tiêu đề và thời điểm tra cứu, không mở qua API tài liệu nội bộ.

`WEB_SEARCH_ENABLED=true`, `WEB_SEARCH_MAX_RESULTS=3` (1–5),
`WEB_SEARCH_OUTPUT_TOKENS=1000` (256–1600). Đặt enabled=false để tắt web.
Trích dẫn `[WEB-ID]` có định danh theo lượt/nguồn, phải nằm trong evidence đã gửi.
Lịch sử chuyển citation web cũ thành URL/thời điểm có nhãn chưa tra cứu lại, không
cho mã WEB-1 cũ trở thành bằng chứng của lượt mới. Snapshot feedback giữ cả nguồn
phụ thuộc và web; thu hồi nguồn phụ thuộc cũng che câu trả lời trong phản hồi.
Packing dành tối đa 1/3 ngân sách cho web trước lịch sử/nguồn nội bộ; không gọi
tổng hợp lần hai nếu mọi web evidence bị loại do ngân sách.
Query tự động giữ mã CVE/phiên bản đúng cấu trúc, không giữ thông báo lỗi tự do.
URL tự sinh ngoài danh sách (hoặc URL thực trong nguồn nội bộ đã trích)
không được chấp nhận. Nội dung web có thể sai hoặc chứa prompt injection; system
prompt yêu cầu coi nó là dữ liệu, không phải chỉ dẫn, nhưng đây không là bảo đảm tuyệt đối.

## Usage và lỗi
Mỗi call dự trữ/ghi ledger riêng, không mất quota khi xóa chat. Tổng usage hiển thị
chỉ cộng trường được provider trả ở mọi call. Plugin tăng input tại OpenRouter:
ngân sách local là byte proxy, không giới hạn token tìm kiếm phát sinh ở provider.
Không có cơ chế cap chi phí tiền tệ; dùng spend controls OpenRouter khi cần.
Web tính phí thêm; xác nhận giá hiện tại tại tài liệu OpenRouter.
Web/provider lỗi trả lỗi rõ, không giả vờ tìm kiếm thành công; call đã gửi có thể
tốn phí, usage không rõ giữ uncertain. Không tự gọi completion tiếp nếu lookup lỗi.

## Kiểm thử
Queue tối đa 180s, cả giai đoạn provider tối đa 240s, mỗi call vẫn timeout 180s.
Timeout tổng trả 504 và bảo toàn usage đã ghi/uncertain; không retry tự động.
Ví dụ Nginx/systemd 480s và graceful shutdown 460s dành chỗ cho local overhead;
Quick Tunnel/client có thể timeout sớm hơn và cần kiểm trên đường truyền thật.

Test dùng cấu hình/DB tạm và mocked OpenRouter, không đọc .env hoặc gọi AI thật.
Chạy suite workspace riêng process. Kiểm tra live có phí cần được thực hiện riêng;
việc API/plugin đang hoạt động trên model cụ thể chưa được chứng minh bằng test offline.