# CyberAnt AI — trợ lý nội bộ chạy local

Ứng dụng demo tiếng Việt cho Sales, Kỹ thuật và Quản trị: hỏi đáp từ tài liệu, tìm hồ sơ công ty, xem tài chính giả lập và quản lý model trên máy Windows. Sử dụng Qwen3.5-9B GGUF qua llama.cpp; không yêu cầu OpenAI API.

**Đây là bộ mã nguồn demo, không phải sản phẩm hoặc chính sách dịch vụ chính thức của CyberAnt.** Giá, SLA, lịch, khách hàng và chứng từ trong bộ sinh dữ liệu là giả lập. Nội dung ATTT là tài liệu biên soạn có nguồn tham khảo.

## Chức năng

- Tài khoản local, mật khẩu băm scrypt, ba vai trò và quản lý phiên online.
- Kho tri thức chung cho mọi tài khoản đã đăng nhập; chỉ tài liệu đã duyệt và còn hiệu lực được dùng. Quản trị giữ quyền sửa/duyệt/thu hồi.
- Chat có nguồn, Markdown, bảng, cỡ chữ, sao chép và tải câu trả lời.
- Lịch sử theo tài khoản: xem, tìm, hỏi tiếp và **xóa từng cuộc trò chuyện**.
- Quản trị CPU/RAM/VRAM, model, log, sao lưu; chọn **1–4 lượt đồng thời**, xem context và trần trả lời cho từng lượt.
- Hồ sơ và tài chính demo có phép tính Python xác định; module Dự toán dịch vụ đã ngừng cung cấp.
- Giao diện responsive, hover/focus và thanh bên thu gọn.

## Bắt đầu

Đọc [hướng dẫn cài đặt](docs/SETUP.md), sau đó chạy tại thư mục dự án:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

Mở **http://127.0.0.1:8088**. Tên tài khoản mặc định là `sales`, `kythuat`, `admin`; mật khẩu ngẫu nhiên được tạo **riêng trên máy cài đặt**, trong `data/initial-accounts.json`. Không có mật khẩu mặc định công khai. `data/model-api-key.txt` là khóa giữa backend và model, không phải mật khẩu người dùng hay dịch vụ API có tính phí.

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [SETUP](docs/SETUP.md) | Cài đặt từ bộ source sạch, GPU, model, dữ liệu |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Thành phần, API, database và luồng RAG |
| [OPERATIONS](docs/OPERATIONS.md) | Tài khoản, xóa lịch sử, runtime, backup, xử lý lỗi |
| [TOKEN_LIMITS](docs/TOKEN_LIMITS.md) | Context, đầu ra, đồng thời và phép đo trên GPU |
| [DATA](docs/DATA.md) | Dữ liệu demo, quyền đọc chung, tài liệu tự thêm |
| [PUBLIC_RELEASE](docs/PUBLIC_RELEASE.md) | Chuẩn bị bộ source để đưa lên GitHub |
| [SECURITY](SECURITY.md) | Ranh giới bảo mật và cách báo vấn đề |
| [CONTRIBUTING](CONTRIBUTING.md) | Kiểm thử, quy ước thay đổi |
| [LUONG_HOAT_DONG.txt](LUONG_HOAT_DONG.txt) | Giải thích toàn bộ hệ thống bằng ngôn ngữ thông thường |

## Kiểm thử

```powershell
.\.venv-runtime\Scripts\python.exe -m pytest -q
.\.venv-runtime\Scripts\python.exe check_workspace_ui.py
```

Unit test dùng database tạm. Kiểm thử UI/model cần ứng dụng đang chạy và Chrome; chúng có thể tạo hội thoại demo. Phép đo `benchmark_context.py` tạm dừng app/model rồi khôi phục cấu hình đã lưu, cần chạy trong thời gian bảo trì.

## Giới hạn

Thiết kế hiện tại dùng Windows, một tiến trình backend và một model GPU; không phải dịch vụ HA hoặc hệ thống đã kiểm thử cho 20 người đồng thời. Bind localhost, chưa HTTPS/SSO/MFA, OCR, connector CRM, vector embeddings/reranker hoặc kiểm toán bảo mật production. Không tự chạy lệnh từ câu trả lời AI và không gửi báo giá/giao dịch bên ngoài.

Bộ public không chứa trọng số, runtime, database, tài khoản, khóa, log hoặc bản sao lưu. Các thành phần bên thứ ba có giấy phép riêng. Chủ dự án cần công bố giấy phép mã nguồn của dự án nếu muốn cấp quyền tái sử dụng; bộ tài liệu này không tự thay chủ sở hữu lựa chọn giấy phép.
