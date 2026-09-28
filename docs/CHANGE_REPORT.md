# Báo cáo hợp nhất hệ thống — 28/09/2026

Ứng dụng duy nhất chạy tại **http://127.0.0.1:8088**, hiện chọn OpenRouter. Local GPU vẫn sử dụng được trong cùng ứng dụng. Đã bỏ trang chọn demo/internal, thư mục `.local-internal`, dashboard khách hàng/tài chính và phân chia quyền Sale/Kỹ thuật. Tài khoản cũ giữ username/mật khẩu, cùng trở thành Thành viên; quản trị giữ quyền quản lý.

## Dữ liệu

Đã kiểm kê/đọc bằng chương trình 946 file nguồn, tài liệu, dữ liệu và bản lưu (khoảng 97 MB), đọc luồng mã chính và đối chiếu mẫu dữ liệu có cấu trúc trước triển khai. Không nạp trọng số model/venv/runtime như tài liệu; giá trị secret không được in ra. Danh mục kiểm kê ở `artifacts/workspace_inventory.json`.

- Hợp nhất 75 tài liệu kỹ thuật/ATTT từ demo, 11 đoạn mô tả dịch vụ từ DataReal và 1.115 mục NewData. Loại 7 bản trùng, còn **1.194 tài liệu**, chia A–F.
- Xóa dữ liệu khách hàng demo, chứng từ/ticket/dự án/CRM, bảng giá/tồn kho giả lập và các trình sinh dữ liệu đó. Xóa DB/phiếu/bản sao của internal, backup và chỉ mục cũ; xóa lịch sử/audit cũ có thể chứa dữ liệu khách hàng. Mật khẩu tài khoản của ứng dụng chính được giữ.
- Xóa file ví dụ khách hàng, yêu cầu/BOM ví dụ, kho legacy/Chroma và **8 sheet ví dụ** trong workbook mới. Giữ biểu mẫu trống, quy trình và lý thuyết.
- Đồng bộ nguồn chuẩn có thêm/sửa/xóa theo hash và giữ trạng thái thu hồi. Lịch sử ẩn câu trả lời nếu nội dung nguồn được sửa, thu hồi hoặc hết hiệu lực.
- Có 1.100 tài liệu được nguồn ghi là bản nháp cần kỹ sư rà soát; đã giữ nhãn trong metadata/giao diện/prompt. Không coi chúng là chính sách kỹ thuật đã được duyệt.

## OpenRouter và token

Đọc `API_KEY`/`MODEL` hiện có trong `.env`, cũng hỗ trợ tên chuẩn `OPENROUTER_API_KEY`/`OPENROUTER_MODEL`. Đã sửa model thành `nvidia/nemotron-3-super-120b-a12b:free` sau đối chiếu catalog; tiền tố `openrouter/` của adapter không phải ID cho API trực tiếp. Không thay key.

Đề xuất gọi API phân loại rồi gửi toàn bộ nhóm hợp lý khi bộ định tuyến cần hiểu ngữ nghĩa khó, nhưng chưa tối ưu cho kho này: thêm lượt phân loại và vẫn có thể gửi nhiều nội dung không liên quan. Bản hiện tại dùng **ưu tiên nhóm mềm + tìm kiếm từ/ký tự cục bộ + chọn đoạn đa dạng + bỏ lặp + giới hạn prompt**. Thường chỉ **một lần gọi API** để tổng hợp; không gửi toàn bộ nhóm hoặc lịch sử chat. Ưu tiên mềm giúp giữ nguồn liên ngành thay vì loại cứng theo một nhóm.

Ngân sách mặc định: đầu vào 6.000 theo ước lượng bảo thủ, đầu ra 1.000 token, tối đa 6 đoạn, 2 lượt API đồng thời. Tắt reasoning khi provider hỗ trợ để tránh tiêu hết trần đầu ra trước khi có câu trả lời. Ghi và hiển thị usage thực tế; không tự retry khi timeout. [Tham số API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request), [reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

## Kết quả kiểm tra

| Kiểm tra | Kết quả |
|---|---|
| Pytest | 21 bài đạt: tài khoản, quyền, lịch sử, đồng bộ, ngân sách, provider, lỗi mạng, trích dẫn |
| Truy xuất 16 câu hỏi mẫu | 16/16 có ít nhất một nhóm nguồn kỳ vọng sau đóng gói |
| OpenRouter thật | HTTP 200, 1.440 token vào, 46 ra, 1 lượt gọi, có nguồn, khoảng 3,89 giây |
| Chi phí lượt OpenRouter mẫu | API báo 0 USD vì dùng model `:free`; không suy ra chi phí model trả phí |
| Local GPU thật | HTTP 200, 699 token vào, 49 ra, có nguồn, khoảng 2,46 giây |
| Giao diện | Đã chạy Edge desktop/mobile; không ghi nhận lỗi JavaScript |
| Dữ liệu | 1.194 tài liệu trong corpus và DB, không có ID hồ sơ khách, SQLite integrity OK |
| Route cũ | `/internal/`, `/demo`, `/api/finance`, `/api/operations` trả 404 |

Bằng chứng trong `artifacts/live_api.json`, `local_smoke.json`, `retrieval_evaluation.json`, `unified_smoke.json`, ảnh desktop/mobile. Số liệu độ trễ/token là một lượt mẫu, không phải benchmark tải hoặc đánh giá độ đúng đầy đủ. Kiểm nhóm truy xuất không chứng minh tất cả bằng chứng cần thiết đã được tìm thấy.

## Cần tối ưu thêm

1. **Chất lượng nội dung:** kỹ sư duyệt 1.100 mục nháp; xác nhận model/firmware và phạm vi áp dụng, tránh hướng dẫn chung được dùng như lệnh triển khai.
2. **Đánh giá RAG:** bổ sung câu hỏi thực, đáp án chuẩn và nguồn bắt buộc, nhất là câu nhiều ý/so sánh. Kiểm tra trích dẫn hiện chỉ xác minh mã nguồn, chưa kiểm chứng từng phát biểu.
3. **Truy xuất ngữ nghĩa:** thêm embeddings/reranker local khi tập câu hỏi chứng minh TF-IDF bỏ sót. Chỉ dùng router LLM khi kết quả cục bộ mơ hồ, đo tổng chi phí và chất lượng trước bật mặc định.
4. **Ngân sách chính xác:** dùng tokenizer đúng model và tự lấy context limit. Hiện đếm byte UTF-8 bảo thủ nên có thể bỏ bớt đoạn vẫn vừa context thực tế. Cần điều chỉnh ngân sách khi đổi model.
5. **Cache:** bổ sung cache câu trả lời có khóa theo câu hỏi, ngữ cảnh, model, prompt và hash kho; hoặc cache provider sau khi đo nhu cầu. Chưa hứa tỷ lệ tiết kiệm với model trả phí. [Tài liệu prompt caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching).
6. **Nhập dữ liệu:** hiện đồng bộ JSON/JSONL chuẩn. Thay Excel/Word gốc cần cập nhật bản trích trước; chưa tự động biên soạn lại toàn bộ workbook, OCR hay theo dõi thay đổi file. Không nên nhập lại các sheet ví dụ khách đã xóa.

Việc xóa áp dụng working tree, DB và bản sao cũ trong workspace. **Không rewrite Git history hoặc xóa bản sao ngoài workspace**. Một số dữ liệu đã được commit trước đó có thể vẫn tồn tại trong lịch sử. Khi muốn chia sẻ repository cần kiểm riêng phạm vi dữ liệu được phép công bố.
