# Vận hành, cập nhật và sao lưu

[Về README](../README.md) · [Xử lý lỗi](TROUBLESHOOTING.md)

## Bật và tắt hằng ngày

Mở PowerShell tại repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .Start-Demo.ps1
```

Đợi `/api/health` báo ready, mở `http://127.0.0.1:8088`. Tiến trình chạy nền ẩn; đóng tab không giải phóng model. Ứng dụng chưa tự khởi động cùng Windows.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .Stop-Demo.ps1
```

Dừng script không xóa model hoặc dữ liệu. Các script nhận thư mục theo vị trí của chính script, không yêu cầu đường dẫn máy tác giả. Chỉ chạy một bản demo trên hai cổng mặc định.

## Thay đổi cấu hình

Trong Hệ thống local, chỉnh số slot/context/trần, đọc bảng xem trước, nhấn Lưu. Context, parallel, GPU layers, cache cần restart model; temperature và trần đầu ra áp dụng lượt mới. Bảng đang chạy tách khỏi cấu hình dự kiến. Không đổi trong lúc có câu hỏi model đang xử lý hoặc chờ.

`gpu_layers = 99` nghĩa yêu cầu offload tối đa, không có nghĩa model có 99 lớp. Log xác nhận số lớp thực. RAM/VRAM toàn máy gồm ứng dụng khác; chỉ số không đo được sẽ không giả lập số liệu.

## Sao lưu

Sau khi đã cài DB, chạy:

```powershell
..venv-runtimeScriptspython.exe .Backup-Data.py
```

Hoặc bấm Sao lưu trong trang admin. Bản sao SQLite nhất quán và JSON seed/cấu hình nằm ở `backups/<thời điểm>`. Không sao chép file API key hoặc mật khẩu khởi tạo. DB backup vẫn có mật khẩu băm, phiên, lịch sử và tài liệu nên phải giữ nội bộ. Backup không nằm trên GitHub và không phải cơ chế backup doanh nghiệp tự động.

## Cập nhật repo đã cài

1. Sao lưu DB/config bằng bước trên.
2. Dừng demo bằng Stop-Demo; xem `git status` để biết thay đổi local. Không ghi đè các chỉnh sửa hoặc xóa dữ liệu để kéo code.
3. Với clone Git không có xung đột, dùng `git pull --ff-only`. Với bản tải ZIP GitHub, giải nén bản mới ở thư mục riêng, đối chiếu source trước khi thay file; không chép đè credential/database.
4. Nếu requirements đổi, cài lại bằng Python môi trường hoặc uv như trong SETUP.
5. Chạy Start-Demo, kiểm health và thử đăng nhập/hỏi đáp. Ctrl+F5 trình duyệt.

Không chạy lại script tạo seed sau mọi `git pull`: chúng cập nhật dữ liệu theo quy tắc phiên bản, không chỉ đọc code. Chỉ chạy khi chủ động nâng bộ mẫu sau backup. `import app` tự bổ sung bảng/cột theo migration hiện có; không có hệ thống rollback schema tổng quát.

Khi chỉ sửa backend và không thay thư viện/schema cần bảo trì, có thể dùng:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .Restart-App.ps1
```

Restart-App dừng backend đúng thư mục rồi chạy Start-Demo, giữ model nếu đang chạy. Đợi người dùng hoàn tất câu hỏi trước thao tác script này vì script không đi qua cơ chế khóa bảo trì trên web.

## Khôi phục

1. Dừng demo. Sao lưu hiện trạng trước khi thay file.
2. Chọn đúng bản `backups/<thời điểm>/demo.sqlite3` và chép thay `data/demo.sqlite3` khi không có app đang mở DB.
3. Khôi phục `runtime-config.json` cùng thời điểm nếu cần; key model có thể giữ local hiện tại.
4. Chạy Start-Demo, dùng mật khẩu đúng với tài khoản trong DB được khôi phục; mật khẩu file khởi tạo có thể khác.
5. Kiểm tài liệu, hội thoại và cấu hình. Backup cũ có thể làm xuất hiện lại cuộc trò chuyện từng xóa.

Đây là hướng dẫn khôi phục thủ công, chưa có kiểm phục hồi định kỳ hoặc backup mã hóa. Khi di chuyển sang máy khác, cài runtime/Python/GPU mới theo SETUP, rồi khôi phục dữ liệu riêng bằng kênh nội bộ; không vận chuyển DB qua repo public.

## Theo dõi và lưu dữ liệu

Admin xem online khi có hoạt động trong 75 giây; heartbeat mỗi 25 giây. Xóa conversation xóa dữ liệu hiện tại và feedback, không xóa backup hoặc bản tải xuống. Audit không chống sửa và không có retention tự động. Thời hạn phiên là 12 giờ.

Log gần đây nằm ở `logs/app.stderr.log`, `logs/model.stderr.log`; giao diện có nút đọc log. `artifacts/` là kết quả test tại máy, không phải điều kiện để ứng dụng khởi động. `exports/` không cần tồn tại; chỉ được tạo nếu chủ động chạy công cụ export tùy chọn.
