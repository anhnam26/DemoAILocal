# CyberAnt — kho tri thức dùng chung

Một ứng dụng tại http://127.0.0.1:8088, một cơ sở dữ liệu, hai chế độ sinh câu trả lời: **OpenRouter API** hoặc **local llama.cpp**. Không còn trang chọn Demo/Internal hoặc phân chia Sale/Kỹ thuật. Thành viên đọc cùng kho tri thức; quản trị quản lý tài liệu, tài khoản và model.

## Chạy trên máy hiện tại

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

API key và model được đọc từ `.env`: hỗ trợ `API_KEY`/`MODEL` đang có hoặc `OPENROUTER_API_KEY`/`OPENROUTER_MODEL`. Key không được gửi tới trình duyệt. Model dùng ID gốc của OpenRouter, ví dụ `nvidia/nemotron-3-super-120b-a12b:free`, không thêm tiền tố adapter `openrouter/`.

Chọn **Hệ thống → Chế độ trả lời** hoặc đặt `LLM_MODE=openrouter` / `LLM_MODE=local` trong `.env`. Chế độ API khởi động được khi không có GPU, GGUF hay llama-server. Chọn local khi model chưa chạy thì bấm Khởi động model. Không tự chuyển sang nhà cung cấp khác khi gặp lỗi.

Tài khoản hiện có được giữ mật khẩu, chuyển vai trò Sale/Kỹ thuật thành Thành viên. Tên đăng nhập cũ vẫn sử dụng được. Khi cài mới, tạo member/admin với mật khẩu ngẫu nhiên trong `data/initial-accounts.json`.

## Dữ liệu và RAG

Kho hiện có 1.194 tài liệu sau loại trùng: thuật ngữ, cấu hình, khảo sát, quy trình/SOW, ATTT và quy tắc chất lượng dữ liệu. Không có CRM, hợp đồng khách, công nợ, ticket hay hồ sơ khách hàng ví dụ. Hướng dẫn bổ sung chưa được kỹ sư duyệt vẫn mang nhãn `draft_engineer_review`, không trở thành cam kết thực tế.

Luồng: câu hỏi → tìm kiếm từ/ký tự và ưu tiên nhóm trên CPU → chọn tối đa 6 đoạn đa dạng, bỏ phần lặp → giới hạn prompt → một lượt gọi model → kiểm tra mã trích dẫn → lưu lịch sử theo tài khoản. Câu hỏi hồ sơ khách hàng hoặc không tìm thấy nguồn có thể trả lời mà không gọi model.

Không gọi thêm API phân loại cho mọi câu hỏi. Không gửi nguyên nhóm tài liệu. Ngân sách mặc định: `RAG_INPUT_TOKENS=6000`, `RAG_OUTPUT_TOKENS=1000`, `RAG_TOP_K=6`, `API_PARALLEL=2`. Đếm đầu vào theo byte UTF-8 bảo thủ, không phải tokenizer chính xác của mọi model; token thực tế và chi phí lấy từ `usage` của API. Xem [ngân sách](docs/TOKEN_LIMITS.md).

## Tài liệu và kiểm tra

- [Cài đặt](docs/SETUP.md), [sử dụng](docs/USER_GUIDE.md), [dữ liệu](docs/DATA.md).
- [Kiến trúc](docs/ARCHITECTURE.md), [vận hành](docs/OPERATIONS.md), [xử lý lỗi](docs/TROUBLESHOOTING.md).
- [Báo cáo thay đổi và giới hạn](docs/CHANGE_REPORT.md).

```powershell
.venv-runtime\Scripts\python.exe -X utf8 -m pytest -q
.venv-runtime\Scripts\python.exe -X utf8 evaluate_rag.py
.venv-runtime\Scripts\python.exe -X utf8 check_unified.py
# Có gọi OpenRouter thật; có thể tính phí tùy model:
.venv-runtime\Scripts\python.exe -X utf8 check_unified.py --live
```
