# Phát triển

Server dùng OpenRouter, không nhập lại dependency GPU/local. Nguồn chuẩn `knowledge/documents.json`; cấu hình qua `config.py`; ghi usage chỉ qua `token_usage.py`.

Chạy `python -m pytest -q` với requirements-dev. Test dùng DB/tài khoản tạm, mock API; không gọi model có phí. Các thay đổi quota phải kiểm cạnh tranh, tháng UTC, lỗi mạng, restart, usage thiếu và lịch sử bị xóa. Không log .env/key/password.

Docker context chỉ chứa runtime theo allowlist .dockerignore. Không commit DB, mật khẩu khởi tạo hoặc API key. Source tri thức công ty cần được phép chia sẻ trước publish.
