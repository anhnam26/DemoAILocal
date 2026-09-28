# Xử lý lỗi

- API 401: kiểm API key trong .env. 402: kiểm số dư. 429: chờ hạn mức nhà cung cấp phục hồi; ứng dụng không tự gọi lại.
- Model không hợp lệ: lấy ID gốc ở catalog OpenRouter, không thêm `openrouter/` trước `nvidia/...`. Key/model không hợp lệ vẫn có thể hiện “API đã cấu hình”, vì health không gọi API có phí.
- Phản hồi rỗng: có thể model chỉ sinh reasoning hoặc hết max_tokens; mặc định API yêu cầu tắt reasoning. Một số provider không hỗ trợ tắt, cần kiểm model hoặc tăng trần phù hợp.
- Không có nguồn: nêu rõ thiết bị/dịch vụ; kiểm tài liệu đã duyệt, còn hiệu lực và đã đồng bộ. Câu hỏi khách hàng không có dữ liệu để trả lời.
- Quá ngân sách: rút gọn câu hỏi hoặc tăng RAG_INPUT_TOKENS vừa đủ trong .env.
- Local không chạy: kiểm GGUF, llama-server, Vulkan và cổng 1234. API mode không cần các file này.
- Đăng nhập cũ: username/mật khẩu được giữ, nhưng vai trò sale/technical đã đổi thành member. File mật khẩu khởi tạo không được cập nhật khi đổi mật khẩu trong web.
- UI test: `check_unified.py` dùng Microsoft Edge. Kiểm `artifacts/unified_smoke.json` và ảnh desktop/mobile. Test không có --live không gọi model thật.
