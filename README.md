# CyberAnt AI — demo trợ lý nội bộ chạy local

Ứng dụng hỏi đáp tiếng Việt cho Sales, Kỹ thuật và Quản trị, chạy bằng **Qwen3.5-9B trên GPU local**. Người dùng tìm tài liệu, hỏi về dịch vụ/ATTT, xem hồ sơ và tài chính demo, quản lý lịch sử trò chuyện. Quản trị quản lý tài khoản, tài liệu và thông số model ngay trên web.

**Người mới bắt đầu tại [Cài đặt từng bước](docs/SETUP.md).** Hướng dẫn dành cho người vừa clone hoặc tải repository từ GitHub, chưa có Python, runtime, trọng số hay tài khoản của hệ thống.

## Môi trường đã kiểm thử

| Thành phần | Cấu hình tham chiếu |
|---|---|
| Hệ điều hành | Windows 11 x64 |
| GPU | NVIDIA RTX 4060 Laptop, VRAM 8 GB, hỗ trợ Vulkan |
| RAM | 16 GB; cần còn bộ nhớ khả dụng khi chạy |
| Python | CPython 3.14.0 x64, bản thông thường |
| Runtime | llama.cpp b10816, Windows x64 Vulkan |
| Model | Qwen3.5-9B-Q4_K_M.gguf, khoảng 5,63 GB |
| Mặc định | 2 lượt đồng thời × 4.096 context, trần đầu ra 800 token/lượt |

Đây là cấu hình đã thử, không phải cam kết mọi máy 8 GB VRAM đều chạy tốt. Cách chạy Windows hiện dùng `Vulkan0`. Máy khác cần kiểm tra GPU tại bước cài runtime. Linux/macOS, CPU-only, CUDA và LM Studio server chưa có quy trình cài tương đương được kiểm thử trong repo này.

## Cài mới gồm những bước nào?

1. Tải repo và mở PowerShell tại thư mục có `app.py`.
2. Cài Python 3.14 x64, tạo `.venv-runtime`, cài `requirements-lock.txt`.
3. Sinh dữ liệu demo bằng bốn script theo đúng thứ tự.
4. Tải trọng số Qwen và runtime llama.cpp Vulkan.
5. Khởi tạo tài khoản local, chạy `Start-Demo.ps1` và kiểm tra `ready: true`.
6. Mở **http://127.0.0.1:8088** và đăng nhập.

Các lệnh đầy đủ và kết quả mong đợi nằm trong [SETUP.md](docs/SETUP.md). Không cần file `cyberant-ai-source.zip`, tài khoản OpenAI hoặc API key dịch vụ trả phí. Không cần cài giao diện LM Studio; demo dùng GGUF bằng llama.cpp độc lập.

## Những gì được tạo riêng trên máy cài đặt

Repo có code, tài liệu và dữ liệu mẫu tổng hợp; **không chứa môi trường Python, model, runtime, database đang sử dụng, mật khẩu hoặc API key local**. Cài mới sẽ tạo lại chúng.

| File local | Công dụng |
|---|---|
| `data/initial-accounts.json` | Mật khẩu khởi tạo ngẫu nhiên cho `sales`, `kythuat`, `admin` |
| `data/model-api-key.txt` | Khóa backend gọi model; Start-Demo tạo nếu chưa có |
| `data/demo.sqlite3` | Tài liệu, user, phiên, lịch sử và audit |
| `data/runtime-config.json` | Cấu hình quản trị đã lưu; thiếu file thì dùng mặc định |

Mật khẩu không giống giữa các máy. File khởi tạo không cập nhật theo lần đổi mật khẩu sau đó. Không đưa các file riêng này lên GitHub hoặc vào kho tri thức.

## Các chức năng hiện có

- Kho tri thức chung cho cả ba vai trò, chỉ dùng nguồn đã duyệt/còn hiệu lực.
- Chat có dẫn nguồn, tiêu đề/danh sách/bảng, cỡ chữ, sao chép và tải Markdown.
- Lịch sử theo tài khoản: tìm, xem lại, hỏi tiếp, xóa từng cuộc trò chuyện.
- Hồ sơ công ty và tài chính tổng hợp: dịch vụ, hợp đồng, ticket, SLA, công nợ.
- Quản trị user/phiên online; upload, duyệt và thu hồi tài liệu.
- Thông số CPU/RAM/VRAM; chọn 1–4 lượt đồng thời, xem context/trần trả lời từng lượt; bật/tắt/restart model và backup.
- Giao diện responsive, hover/focus và nút ☰ mở/đóng thanh bên.

Module **Dự toán dịch vụ đã được gỡ**; dữ liệu định mức vẫn dùng để tra cứu, tab Tài chính demo vẫn có chức năng riêng. AI không tự gửi báo giá, mở ticket, đặt lịch hay thực thi lệnh.

## Đọc tài liệu theo nhu cầu

| Tài liệu | Đọc khi |
|---|---|
| [SETUP](docs/SETUP.md) | Cài lần đầu từ repo mới |
| [USER_GUIDE](docs/USER_GUIDE.md) | Đã đăng nhập và muốn thử các chức năng |
| [OPERATIONS](docs/OPERATIONS.md) | Khởi động/dừng, cập nhật repo, backup/khôi phục |
| [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) | Cài hoặc chạy gặp lỗi |
| [TOKEN_LIMITS](docs/TOKEN_LIMITS.md) | Điều chỉnh context, trần đầu ra và số lượt |
| [DATA](docs/DATA.md) | Hiểu/tái tạo/bổ sung dữ liệu |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Hiểu code, API và luồng xử lý |
| [CONTRIBUTING](CONTRIBUTING.md) | Phát triển và kiểm thử |
| [PUBLIC_RELEASE](docs/PUBLIC_RELEASE.md) | Quản lý source trên GitHub |
| [SECURITY](SECURITY.md) | Hiểu quyền truy cập và giới hạn bảo mật |
| [LUONG_HOAT_DONG.txt](LUONG_HOAT_DONG.txt) | Đọc giải thích bằng ngôn ngữ thông thường |

## Giới hạn và phạm vi demo

Giá, VAT mô phỏng, SLA, lịch, khách hàng, hợp đồng và chứng từ đều là dữ liệu giả lập, không phải chính sách hay cam kết thương mại của CyberAnt. Tri thức ATTT có nguồn tham khảo; AI vẫn có thể tổng hợp sai.

Hiện chạy localhost với một backend process, chưa triển khai HTTPS/SSO/MFA, HA, OCR, semantic embeddings/reranker, connector CRM hoặc kiểm thử phục vụ toàn công ty. Không đổi thành nhiều uvicorn worker: bộ điều phối lượt đang nằm trong bộ nhớ một tiến trình. Các thành phần model/runtime/thư viện có giấy phép riêng; repository chưa tự cấp một giấy phép mã nguồn mới thay chủ dự án.
