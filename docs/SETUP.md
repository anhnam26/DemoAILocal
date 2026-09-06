# Cài đặt trên Windows

## 1. Chuẩn bị

Máy đã kiểm thử: Windows 11, NVIDIA RTX 4060 Laptop 8 GB, RAM 16 GB, Python 3.14.0, llama.cpp b10816 Vulkan. Đây là cấu hình tham chiếu; RAM/VRAM khả dụng còn phụ thuộc ứng dụng khác. Chuẩn bị dung lượng cho model khoảng 5,63 GB, thư viện/runtime và dữ liệu.

Cài Python tương thích và trình điều khiển GPU có Vulkan. Script hiện chỉ định `Vulkan0`; trên máy khác cần kiểm tra `runtime/llama-server.exe --list-devices` và điều chỉnh `Start-Demo.ps1` cùng `system_runtime.model_args` nếu GPU mong muốn ở vị trí khác. Không tự thay driver từ ứng dụng.

## 2. Python và dữ liệu

Tại thư mục source đã giải nén:

```powershell
py -3.14 -m venv .venv-runtime
.\.venv-runtime\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv-runtime\Scripts\python.exe company_data.py
.\.venv-runtime\Scripts\python.exe security_data.py
.\.venv-runtime\Scripts\python.exe finance_data.py
.\.venv-runtime\Scripts\python.exe workflow_data.py
```

Các script tạo thư mục data, tài liệu tổng hợp và SQLite demo. `workflow_data.py` chỉ bổ sung định mức/nguồn tham khảo, không bật lại module Dự toán dịch vụ. Trên máy đã có dữ liệu, sao lưu trước khi chạy lại script sinh dữ liệu. Lần import/chạy app đầu tiên tạo bảng tài khoản và mật khẩu ngẫu nhiên nếu chưa có người dùng.

## 3. Trọng số và runtime

```powershell
.\.venv-runtime\Scripts\python.exe download_model.py
```

Script tải `lmstudio-community/Qwen3.5-9B-GGUF`, file `Qwen3.5-9B-Q4_K_M.gguf`, kiểm SHA-256 theo metadata và ghi `models/manifest.json`. Cần Internet khi tải. Bản tải được gắn revision trong manifest; không đưa trọng số vào Git.

Tải gói **Windows x64 Vulkan** tại [release chính thức llama.cpp b10816](https://github.com/ggml-org/llama.cpp/releases/tag/b10816). Giải nén executable và DLL đi cùng vào `runtime/`, sao cho có `runtime/llama-server.exe`. Giữ nguyên các file giấy phép đi kèm. Không chỉ chép riêng executable mà bỏ DLL.

## 4. Khởi động

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

Đợi model nạp, mở `http://127.0.0.1:8088`. Backend dùng port 8088, model 1234; khóa model được tạo tự động. Mật khẩu đăng nhập nằm trong `data/initial-accounts.json`. Đổi mật khẩu sau lần đăng nhập đầu theo nhu cầu. Hai file bí mật không nằm trong bộ public.

Mặc định là 2 lượt × 4.096 context, trần đầu ra 800 token/lượt. Có thể sao chép `examples/runtime-config.example.json` thành `data/runtime-config.json` trước khi khởi động. Thay đổi trong trang quản trị sẽ được ghi vào file local này.

Ứng dụng chỉ bind localhost. Truy cập qua nhiều máy cần một thiết kế HTTPS, mạng và xác thực phù hợp; không đơn giản đổi host sang mọi giao diện mạng rồi coi như đã triển khai an toàn.
