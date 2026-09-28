# Ngân sách và giảm token

Phân loại bằng LLM rồi gửi toàn bộ nhóm thường vẫn dư dữ liệu, thêm một lượt mạng và token cho phân loại. Bản này tìm kiếm ngay trên máy và chỉ gửi đoạn phù hợp. Với câu hỏi có nguồn: thông thường **một lượt API**. Câu hỏi không có nguồn/hồ sơ khách hàng: có thể **không gọi API**.

| Biến .env | Mặc định | Ý nghĩa |
|---|---:|---|
| RAG_INPUT_TOKENS | 6000 | Ngân sách ước lượng gồm system, câu hỏi, nguồn, phần dư template |
| RAG_OUTPUT_TOKENS | 1000 | max_tokens gửi provider |
| RAG_TOP_K | 6 | Số đoạn tối đa trước đóng gói |
| API_PARALLEL | 2 | Số lượt API đồng thời |

Ước lượng đầu vào dùng độ dài UTF-8 byte bảo thủ; không dùng giả định tiếng Việt bằng ký tự/4. Đây không phải tokenizer chính xác cho mọi provider. `usage.prompt_tokens`, `completion_tokens`, `cost` là số thực từ API và hiển thị dưới câu trả lời. Giá trị không có trong phản hồi không được tự suy ra. Chưa tự tải context limit của từng model: khi đổi model cần đặt ngân sách phù hợp.

Local còn giới hạn theo context tiến trình và trần đầu ra của runtime. Ngân sách local = min(ngân sách RAG, context − output − phần dự phòng). Prompt cố định đứng đầu, nguồn và câu hỏi theo sau để thuận lợi cho cache của nhà cung cấp, nhưng chưa bật cache đặc thù hoặc hứa tỷ lệ cache hit.

Không cắt âm thầm câu hỏi quá ngân sách: trả lỗi yêu cầu rút gọn. Nguồn có thể chỉ còn đoạn trích; vẫn dẫn về tài liệu gốc. Không gửi toàn bộ lịch sử. Không tự gọi lại request timeout vì có thể tăng hóa đơn.

Tối ưu tiếp: đánh giá câu trả lời thực trên bộ câu hỏi chuẩn; embeddings/reranker local cho câu diễn đạt khác từ khóa; tokenizer đúng model; cache câu trả lời gắn hash kho/model/prompt; chọn model giá rẻ đã đạt tiêu chí; chỉ dùng API phân loại khi truy xuất cục bộ không rõ.

Tham khảo: [Chat API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request), [prompt caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching), [reasoning tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
