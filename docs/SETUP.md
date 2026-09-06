# Cài mới từ GitHub trên Windows

[Về README](../README.md) · [Gặp lỗi?](TROUBLESHOOTING.md)

Làm lần lượt từ bước 1 đến 9. Tất cả khối lệnh dưới đây chạy trong **Windows PowerShell**, tại thư mục repo có `app.py`, trừ khi ghi khác. Khi một lệnh báo lỗi, xử lý lỗi trước khi chạy bước sau. Không cần quyền Administrator để chạy ứng dụng hoặc kích hoạt virtualenv.

## 1. Chuẩn bị máy

Chuẩn bị Windows x64, GPU có Vulkan và bộ nhớ phù hợp. Máy tham chiếu dùng Windows 11, RTX 4060 Laptop 8 GB VRAM, RAM 16 GB. Dự trù khoảng 15–20 GB trống để chứa môi trường, runtime, model và cache tải; đó là dung lượng dự phòng, không phải kích thước repo.

Cần Internet để tải repo, Python, gói thư viện, runtime và trọng số. Sau khi cài đủ, tìm kiếm và inference dùng tài nguyên local. Không có cloud fallback. Muốn chạy bài test giao diện cần Google Chrome; sử dụng ứng dụng bình thường có thể mở bằng Chrome/Edge.

## 2. Lấy repository

**Cách A — có Git:** trên GitHub, chọn **Code → HTTPS → Copy URL**. Chạy lệnh sau, thay chuỗi URL bằng URL vừa sao chép:

```powershell
git clone "URL_HTTPS_CUA_REPOSITORY" CyberAntAI
cd .CyberAntAI
```

**Cách B — không có Git:** chọn **Code → Download ZIP** của GitHub, giải nén, mở thư mục có `app.py`; nhấp thanh địa chỉ Explorer, gõ `powershell` rồi Enter. Đây là ZIP tải repo do GitHub cung cấp, không cần tạo gói export riêng của ứng dụng.

Tên và vị trí thư mục có thể khác máy tác giả; **không bắt buộc dùng ổ D hoặc tên TestSystem**. Chọn đường dẫn ngắn, dễ thao tác như `C:ProjectsCyberAntAI`. Xác nhận đang đứng đúng thư mục:

```powershell
Get-Location
Test-Path .app.py
Test-Path .
equirements-lock.txt
```

Hai dòng cuối cần trả `True`. Đừng chạy từ thư mục cha còn chứa thêm một thư mục repo lồng bên trong.

## 3. Cài Python và thư viện

### Cách chính: CPython và pip

Cài **Python 3.14 x64, bản thông thường** từ [python.org](https://www.python.org/downloads/windows/); bản tham chiếu là [3.14.0](https://www.python.org/downloads/release/python-3140/). Không chọn bản ARM64, 32-bit hoặc free-threaded cho lần cài theo hướng dẫn này. Mở PowerShell mới sau khi cài.

```powershell
py -3.14 --version
py -3.14 -m venv .venv-runtime
..venv-runtimeScriptspython.exe -m pip install -r .
equirements-lock.txt
..venv-runtimeScriptspython.exe -m pip check
```

Kết quả cuối cần là `No broken requirements found.`. Lệnh dùng đường dẫn Python rõ ràng nên không cần `Activate.ps1` hoặc thay ExecutionPolicy toàn máy. Tên `.venv-runtime` phải giữ đúng vì Start-Demo sử dụng tên này.

### Cách thay thế: uv

Nếu đã có uv theo [hướng dẫn chính thức](https://docs.astral.sh/uv/getting-started/installation/), có thể dùng nhóm lệnh dưới đây **thay cho** nhóm CPython/pip phía trên, trong thư mục cài mới:

```powershell
uv python install 3.14.0
uv venv --python 3.14.0 .venv-runtime
uv pip install --python ..venv-runtimeScriptspython.exe -r .
equirements-lock.txt
uv pip check --python ..venv-runtimeScriptspython.exe
```

Môi trường uv có thể không chứa module pip; khi đó dùng `uv pip`, không coi `No module named pip` là thư viện ứng dụng bị lỗi. Chỉ chọn một cách để tạo môi trường, không tạo lại đè lên môi trường đang sử dụng.

## 4. Tạo đủ dữ liệu demo

Trên lần cài mới, chạy theo thứ tự:

```powershell
..venv-runtimeScriptspython.exe -X utf8 .company_data.py
..venv-runtimeScriptspython.exe -X utf8 .security_data.py
..venv-runtimeScriptspython.exe -X utf8 .inance_data.py
..venv-runtimeScriptspython.exe -X utf8 .workflow_data.py
..venv-runtimeScriptspython.exe -X utf8 -c "import app; print('Khoi tao ung dung thanh cong')"
```

Bốn script tạo DB và tài liệu mẫu; import app tạo các bảng ứng dụng và ba tài khoản nếu chưa có. Làm cả bước này dù repo đã kèm JSON/Markdown mẫu để có DB đầy đủ trên máy mới. Không chạy lại để “reset” một hệ thống đang có dữ liệu thật; xem [DATA](DATA.md) trước khi cập nhật seed.

Kiểm số bản ghi trên máy cài mới:

```powershell
..venv-runtimeScriptspython.exe -c "import sqlite3; c=sqlite3.connect('data/demo.sqlite3'); print('Tai lieu:',c.execute('SELECT COUNT(*) FROM docs').fetchone()[0]); print('Tai khoan:',c.execute('SELECT COUNT(*) FROM users').fetchone()[0]); c.close()"
```

Mong đợi **481 tài liệu và 3 tài khoản**. Tài liệu đã upload thêm có thể làm số lượng lớn hơn. Metadata có thời hạn; số tài liệu *được hiển thị* có thể ít hơn nếu ngày sử dụng đã qua hiệu lực của bộ demo.

## 5. Tải đúng model

```powershell
..venv-runtimeScriptspython.exe -X utf8 .download_model.py
```

Script tải từ Hugging Face repository `lmstudio-community/Qwen3.5-9B-GGUF`, chọn `Qwen3.5-9B-Q4_K_M.gguf`. Cần chờ tải khoảng 5,63 GB và kiểm SHA-256; thành công in `Model verified`. Không đổi tên file. Script ghi revision/checksum vào `models/manifest.json`; thông tin này xác định bản trọng số đã tải.

```powershell
Test-Path .modelsQwen3.5-9B-Q4_K_M.gguf
Get-Item .modelsQwen3.5-9B-Q4_K_M.gguf | Select-Object Name,Length
```

Lệnh đầu cần `True`. Script không hỗ trợ tiếp tục tải một phần; chạy lại sau lỗi mạng có thể tải lại từ đầu. Nếu đã có GGUF đúng tên, script vẫn kiểm hash; file tồn tại nhưng sai hash cần thay bằng bản đúng. Xem [xử lý lỗi tải model](TROUBLESHOOTING.md).

## 6. Cài llama.cpp và kiểm GPU

Mở [release chính thức llama.cpp b10816](https://github.com/ggml-org/llama.cpp/releases/tag/b10816), tải **Windows x64 (Vulkan)**. Giải nén tất cả file trong gói vào thư mục `runtime` của repo. Giữ executable, DLL và giấy phép đi kèm. Nếu ZIP có thư mục con, chuyển nội dung sao cho đường dẫn cuối là:

```text
CyberAntAI/
  app.py
  runtime/
    llama-server.exe
    ... các DLL/file đi kèm bản Vulkan
  models/
    Qwen3.5-9B-Q4_K_M.gguf
```

Kiểm tra:

```powershell
Test-Path .
untimellama-server.exe
.
untimellama-server.exe --version
.
untimellama-server.exe --list-devices
```

Ứng dụng hiện chỉ định `Vulkan0`. **Đọc tên GPU cạnh Vulkan0**: trên máy tham chiếu đó là RTX 4060 Laptop. Nếu Vulkan0 là iGPU và GPU mong muốn là Vulkan1, thay đúng giá trị `Vulkan0` ở **cả hai** nơi trước khi khởi động:

- `Start-Demo.ps1`: phần `$modelArgs`, cặp `'--device','Vulkan0'`.
- `system_runtime.py`: hàm `model_args`, cặp `'--device','Vulkan0'`.

Hai nơi tương ứng với khởi động bằng script và khởi động từ web. Hiện chưa có bộ chọn GPU trên web. Nếu không có Vulkan device hoặc thiếu DLL, xem [TROUBLESHOOTING](TROUBLESHOOTING.md). Không cần cài CUDA Toolkit hoặc giao diện LM Studio cho bản Vulkan này.

## 7. Khởi động dịch vụ

Kiểm đầu vào cần thiết:

```powershell
Test-Path ..venv-runtimeScriptspython.exe
Test-Path .datademo.sqlite3
Test-Path .modelsQwen3.5-9B-Q4_K_M.gguf
Test-Path .
untimellama-server.exe
```

Cả bốn cần `True`. Có thể giữ cấu hình mặc định mà không tạo `runtime-config.json`. Nếu muốn có file để xem, **chỉ trên lần cài mới chưa có cấu hình**, dùng:

```powershell
Copy-Item -LiteralPath .examples
untime-config.example.json -Destination .data
untime-config.json
```

Khởi động:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .Start-Demo.ps1
```

Script tạo khóa model nếu thiếu, mở model/backend dưới dạng tiến trình nền ẩn. Dòng thông báo URL chỉ nói script đã khởi chạy, không bảo đảm model nạp xong. Chờ khoảng 10–60 giây hoặc lâu hơn khi thiếu bộ nhớ, rồi kiểm:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8088/api/health | Select-Object ready,model,context,parallel
```

Mong đợi `ready = True`, `context = 4096`, `parallel = 2` nếu chưa thay cấu hình. Nếu chưa kết nối được, đợi backend import thư viện rồi thử lại. Nếu `ready = False`, đọc log theo hướng dẫn xử lý lỗi. Không chạy thêm một model khác để “thử” trong lúc model đang nạp.

## 8. Đăng nhập

Mở **http://127.0.0.1:8088**. Đọc file mật khẩu **trên máy của bạn**:

```powershell
notepad .datainitial-accounts.json
```

| Username | Vai trò |
|---|---|
| `sales` | Sales |
| `kythuat` | Kỹ thuật |
| `admin` | Quản trị |

Tìm đúng username và password trong file rồi nhập trên web. Không dùng mật khẩu của tác giả hoặc người khác. Đổi mật khẩu ở Tài khoản; mật khẩu trong file khởi tạo sẽ không tự đổi theo. Admin có thể đặt lại mật khẩu cho user.

## 9. Kiểm tra đã chạy thành công

1. Đăng nhập `sales`, mở Kho tri thức và đọc một tài liệu ATTT.
2. Hỏi “Firewall mạng và WAF khác nhau như thế nào?” — kiểm luồng tra cứu có nguồn bằng quy tắc.
3. Hỏi “Cần hỏi khách những gì trước khi triển khai Wi-Fi?” — kiểm câu tổng hợp; nhãn câu trả lời cần thể hiện `Qwen3.5-9B + RAG` để xác nhận đã gọi LLM, không chỉ hiển thị số liệu Python.
4. Mở Lịch sử trò chuyện, đăng xuất/đăng nhập lại, mở cuộc cũ và hỏi tiếp.
5. Đăng nhập `admin`, mở Hệ thống local: có GPU, RAM và context/số lượt đang chạy. Đọc log để đối chiếu model offload.

Xem [USER_GUIDE](USER_GUIDE.md) để thử hết các mục. Cài đặt xong không cần chạy lại bước tải model/sinh seed mỗi ngày; chỉ chạy Start-Demo sau khi máy khởi động lại.

## Các lệnh thường dùng sau khi cài

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .Start-Demo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .Stop-Demo.ps1
```

Đóng tab trình duyệt không tắt model. Dừng ứng dụng không xóa model, tài khoản hay hội thoại. App/model chỉ lắng nghe localhost, nên người ở máy khác không thể mở URL trên để dùng chung; triển khai LAN là bước thiết kế riêng.
