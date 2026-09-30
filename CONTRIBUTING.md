# Phát triển

Server dùng OpenRouter, không nhập lại dependency GPU/local. Nguồn chuẩn `knowledge/documents.json`; cấu hình qua `config.py`; ghi usage chỉ qua `token_usage.py`.

Source đã loại bộ kiểm thử tự động và công cụ đánh giá offline theo yêu cầu. Khi chỉnh sửa, kiểm tra cú pháp/import và chạy thử bằng APP_DATA_DIR trỏ tới thư mục tạm trước khi khởi động ứng dụng; tuyệt đối không thử trên DB thật. Các thay đổi quota vẫn cần kiểm cạnh tranh, tháng UTC, lỗi mạng, restart, usage thiếu và lịch sử bị xóa bằng môi trường xác minh riêng. Không để lại file kiểm thử trong source bàn giao; không gọi model có phí nếu chưa được duyệt. Không log .env/key/password.

Docker context chỉ chứa runtime theo allowlist .dockerignore. Không commit DB, mật khẩu khởi tạo hoặc API key. Source tri thức công ty cần được phép chia sẻ trước publish.
