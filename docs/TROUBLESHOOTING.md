# Xử lý lỗi cài đặt và chạy

[Về SETUP](SETUP.md) · [Vận hành](OPERATIONS.md)

Các lệnh chạy từ thư mục có `app.py`. Trước khi sửa, xác định lỗi thuộc Python, backend hay model; không xóa database để thử sửa lỗi model.

## Python hoặc thư viện

| Lỗi | Cách xử lý |
|---|---|
| Không nhận lệnh `py` | Cài Python x64 và launcher; mở terminal mới. Hoặc dùng nhánh uv trong SETUP |
| Không tìm `.venv-runtimeScriptspython.exe` | Đang sai thư mục hoặc chưa tạo môi trường đúng tên |
| `No module named pip` trong môi trường uv | Dùng `uv pip install --python ..venv-runtimeScriptspython.exe -r requirements-lock.txt` |
| `No matching distribution found` | Kiểm Python 3.14 x64 bản thường, kết nối/index PyPI; không tự bỏ pin phiên bản để vượt lỗi |
| `ModuleNotFoundError` | Cài requirements bằng đúng Python `.venv-runtime`, tránh pip của môi trường khác |
| Lỗi SSL/proxy khi tải | Dùng proxy/chứng chỉ do quản trị mạng cung cấp; không tắt xác minh TLS |

Kiểm:

```powershell
..venv-runtimeScriptspython.exe --version
..venv-runtimeScriptspython.exe -c "import struct; print(struct.calcsize('P')*8)"
```

Mong đợi Python 3.14.x và `64`. Nếu dùng pip, chạy `python -m pip check` bằng đường dẫn môi trường; nếu dùng uv, chạy `uv pip check --python ...`.

## Tải model lỗi hoặc hash không khớp

`download_model.py` tải GGUF khoảng 5,63 GB; kiểm ổ đĩa, mạng và quyền ghi `models/`. File `.partial` chưa phải model hoàn chỉnh, lần chạy lại có thể tải từ đầu. Nếu báo checksum mismatch với GGUF đã tồn tại, giữ bản đó ngoài tên file đích để đối chiếu, rồi tải bản đúng; đừng sửa checksum để bỏ qua kiểm tra. Manifest ghi revision tải được, không tự bảo đảm một file bất kỳ cùng tên là đúng.

## Runtime thiếu DLL hoặc không thấy GPU

Kiểm `runtime/llama-server.exe` đúng vị trí, gói tải là Windows x64 Vulkan và có toàn bộ DLL đi cùng. Nếu executable báo thiếu runtime Microsoft, cài runtime C++ theo hướng dẫn nhà cung cấp phù hợp; không tải DLL lẻ từ trang không rõ nguồn.

```powershell
.
untimellama-server.exe --version
.
untimellama-server.exe --list-devices
```

Nếu không có Vulkan GPU, kiểm driver/hỗ trợ Vulkan. Nếu GPU mong muốn không là Vulkan0, chỉnh cả Start-Demo.ps1 và system_runtime.py theo SETUP. `nvidia-smi` không có trên GPU hãng khác; UI hiện chưa có đo VRAM tương đương cho mọi hãng.

## Web chưa mở được

```powershell
Get-Content -LiteralPath .logsapp.stderr.log -Tail 60 -Encoding UTF8
Get-NetTCPConnection -LocalPort 8088,1234 -State Listen -ErrorAction SilentlyContinue
```

Ngay sau Start có thể phải đợi backend import thư viện. Nếu có traceback, sửa lỗi đầu tiên theo log. Nếu port bị ứng dụng khác giữ, xác định ứng dụng đó trước; Stop-Demo chỉ dừng tiến trình demo đúng thư mục. Không chạy nhiều bản repo trên cùng cổng mặc định.

Để nhìn lỗi backend trực tiếp, dừng demo trước rồi chạy ở foreground:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .Stop-Demo.ps1
..venv-runtimeScriptspython.exe -m uvicorn app:app --host 127.0.0.1 --port 8088
```

Nhấn Ctrl+C để dừng foreground; sau đó chạy Start-Demo lại. Cách này chỉ mở backend, không tự nạp model.

## Web mở nhưng model chưa sẵn sàng

```powershell
Invoke-RestMethod http://127.0.0.1:8088/api/health
Get-Content -LiteralPath .logsmodel.stderr.log -Tail 80 -Encoding UTF8
```

`ready: false` nghĩa model chưa phản hồi với model ID mong đợi. Chờ nạp, kiểm file GGUF, GPU, cổng 1234 và bộ nhớ. Model API dùng key nên gọi trực tiếp `/v1/models` bằng trình duyệt không kèm key có thể báo 401; endpoint `/api/health` của app tự gửi key đúng cách.

Nếu mới đổi `model-api-key.txt`, restart model để model/backend dùng cùng khóa. Đây không phải mật khẩu user và không cần OpenAI key.

## Thiếu RAM/VRAM hoặc quá chậm

Đóng phần mềm dùng GPU không cần thiết; giảm slot/context trong Hệ thống local rồi lưu/restart. Máy yếu có thể thử 1 slot, context 4.096 hoặc 2.048. Nếu cần sửa file khi web không chạy, dừng demo rồi mở `data/runtime-config.json`, giữ đầy đủ các trường và cú pháp JSON, không dùng dấu phẩy cuối. Bản ví dụ ở `examples/` là cấu hình mặc định, ghi đè sẽ mất lựa chọn cũ.

RAM/VRAM hiển thị là tổng toàn máy. Nạp được context lớn không bảo đảm prompt gần đầy hoàn tất nhanh. [TOKEN_LIMITS](TOKEN_LIMITS.md) ghi rõ phép đo 32.768 và timeout ở 65.536. Không cài lại model mỗi khi trả lời chậm.

## Đăng nhập hoặc dữ liệu

| Hiện tượng | Cách xử lý |
|---|---|
| Chưa có `initial-accounts.json` | Hoàn tất bước sinh seed và `python -c "import app"`; kiểm log/quyền ghi data |
| Mật khẩu file không đăng nhập được | Mật khẩu có thể đã đổi; dùng mật khẩu hiện tại hoặc admin reset |
| Sai nhiều lần | Chờ giới hạn 5 phút sau nhiều lần sai rồi thử lại |
| Chỉ vài chục tài liệu | Chưa chạy đủ bốn script seed; trên cài mới chạy đúng thứ tự |
| DB có 481 nhưng UI ít hơn | Kiểm trạng thái/hiệu lực/requires; dữ liệu snapshot không có hiệu lực vĩnh viễn |
| Hỏi thiếu dữ liệu | Bổ sung tên dịch vụ/chủ đề, đọc nguồn, admin duyệt tài liệu liên quan |

Nếu mất mật khẩu của quản trị duy nhất, chưa có CLI phục hồi chính thức trong bản này. Không chỉnh `initial-accounts.json` hoặc xóa DB chứa dữ liệu cần giữ; nhờ người bảo trì xử lý bản sao lưu.

## Chat, lịch sử và giao diện

Hàng chờ tối đa 16, thời gian chờ 180 giây; request model có timeout riêng 180 giây. Khi quá tải, hỏi lại sau hoặc giảm độ dài/tải. Trần đầu ra là tối đa, không ép model viết đủ; trần quá thấp có thể làm JSON bị cắt. Xem bảng trần **hiệu lực**, không chỉ trường mong muốn.

Không xóa được conversation đang sinh là hành vi dự kiến; đợi hoàn tất. Không tìm thấy ID người khác là kiểm quyền. Nguồn cũ bị thu hồi có thể làm lịch sử che nội dung. Ctrl+F5 giải quyết tài nguyên web cũ; nút ☰ mở lại sidebar đã thu gọn.

Khi nhờ hỗ trợ, gửi phiên bản Python/runtime, trạng thái health và đoạn lỗi đã che thông tin riêng. Không gửi API key, mật khẩu, nguyên DB hoặc toàn bộ logs lên issue public.
