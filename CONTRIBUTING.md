# Phát triển và kiểm thử

[Về README](README.md) · [Kiến trúc](docs/ARCHITECTURE.md)

## Chuẩn bị môi trường

Làm theo [SETUP](docs/SETUP.md) đến bước cài dependencies, sinh dữ liệu và `import app`. Dùng `.venv-runtime` thay vì Python bất kỳ trên PATH. Model/runtime chỉ bắt buộc cho kiểm thử GPU; unit test nghiệp vụ/xác thực có thể chạy khi không tải model.

Không dùng nhiều backend worker: hàng chờ, khóa bảo trì và tập conversation đang xử lý hiện là bộ nhớ một process. Chỉnh runtime cần đồng bộ `Start-Demo.ps1`, `system_runtime.py`, `runtime_limits.py`, API quản trị và UI.

## Unit test

```powershell
..venv-runtimeScriptspython.exe -m pytest -q
```

Các fixture dùng DB tạm. Import app vẫn khởi tạo file local nếu thiếu; hãy làm seed đúng thứ tự trước. Các helper đọc mật khẩu khởi tạo local cho test; chúng không in/copy mật khẩu vào báo cáo. Snapshot bộ test hiện có 35 bài đã đạt trên môi trường tham chiếu; số lượng có thể đổi theo phiên bản.

## Kiểm thử giao diện

Cài Google Chrome trên máy, Start-Demo và chờ ready. Gói Playwright đã nằm trong requirements; các script chọn `channel='chrome'`, nên tải Chromium riêng không thay thế Chrome cho các script hiện tại.

Chuẩn bị thư mục bằng chứng nếu chưa có:

```powershell
New-Item -ItemType Directory -Path .artifacts -Force
..venv-runtimeScriptspython.exe -X utf8 .check_workspace_ui.py
..venv-runtimeScriptspython.exe -X utf8 .check_admin_budgets_ui.py
```

Script tạo/đọc hội thoại và có thể đổi trạng thái tài liệu hoặc user trên dữ liệu demo tùy bài. Dùng máy/bộ tài khoản test; không chạy vào dữ liệu thật. Nếu đã đổi mật khẩu ba tài khoản, helper `testing_accounts.py` không còn khớp file khởi tạo; dùng cài đặt test riêng có credential mới, không thay mật khẩu vận hành chỉ để chạy test.

Các bài bổ sung: `check_company_ui.py`, `check_finance_ui.py`, `check_readability.py`. Chạy tuần tự để không tranh cùng user/chủ đề và dễ đọc lỗi. Ảnh/report nằm trong artifacts và không được commit mặc định.

## Kiểm thử GPU và tải đồng thời

```powershell
..venv-runtimeScriptspython.exe -X utf8 .check_concurrent_chat.py
```

Bài này kỳ vọng cấu hình 2 slot × 4.096; phải đặt đúng trước khi chạy. `check_four_slots.py` tự đổi sang 4 × 4.096 bằng API, tạo câu thử rồi phục hồi cấu hình cũ. `check_model_control.py` thực sự dừng/bật model. `benchmark_context.py` tạm dừng toàn demo rồi thử prompt rất dài: chỉ chạy khi chấp nhận gián đoạn, không phải bước cài lần đầu.

## Kiểm tra cách cài từ source

`verify_clean_setup.py` tạo thư mục tạm và môi trường Python mới, lấy source đang được Git theo dõi, cài requirements bằng uv, sinh seed, kiểm đăng nhập/chat quy tắc/lịch sử/admin. Cần Git, uv, Internet nếu cache chưa đủ và thư mục artifacts để ghi report. Chạy bằng Python môi trường hiện tại:

```powershell
..venv-runtimeScriptspython.exe -X utf8 .erify_clean_setup.py
```

Không tải lại GGUF hoặc khởi động GPU trong bài này. Nó không thay thế smoke test model thật hoặc chứng minh cài đúng trên mọi Windows/GPU.

## Khi gửi thay đổi

Mô tả lỗi cụ thể, hành vi trước/sau, cách kiểm và giới hạn còn lại. Thêm test cho kiểm quyền, tiền, migration hoặc xóa transaction; không thêm credential/tài liệu thật vào fixture. UI kiểm hover/focus, desktop/mobile, chữ dài, hủy/xác nhận xóa. Cập nhật docs liên quan khi thay trường config, quyền, API hoặc bước cài; mọi liên kết nội bộ dùng đường dẫn tương đối phù hợp GitHub.
