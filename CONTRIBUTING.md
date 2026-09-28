# Phát triển

Đọc README và docs/ARCHITECTURE.md. Một app, hai provider, một kho lý thuyết. Không thêm lại CRM/finance hoặc ứng dụng internal riêng.

Chạy `.venv-runtime\Scripts\python.exe -X utf8 -m pytest -q`. Test tạo DB và tài khoản biệt lập, mock provider để không gọi API. `evaluate_rag.py` kiểm truy xuất 16 câu hỏi, chưa chấm độ đúng câu trả lời. `check_unified.py --live` gọi model thật theo .env và có thể tính phí.

Không commit .env, DB, tài khoản, NewData hoặc nội dung công ty khi chưa có quyền chia sẻ. Khi đổi adapter nguồn phải giữ provenance, trạng thái review và kiểm loại dữ liệu khách hàng. Khi đổi prompt/provider phải kiểm budget, lỗi mạng, token usage và mã nguồn giả.
