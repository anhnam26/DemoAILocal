# Vận hành và xử lý sự cố

## Tài khoản và lịch sử

Quản trị tạo/sửa/khóa user, đặt lại mật khẩu, phân role và nhóm khách dashboard. Thay đổi quyền hoặc mật khẩu thu hồi phiên. Không cho vô hiệu hóa quản trị hoạt động cuối cùng. Online là heartbeat/hoạt động trong 75 giây, không phải bằng chứng đang gõ.

Trong Lịch sử trò chuyện, mỗi thẻ có nút **Xóa cuộc trò chuyện**. Xác nhận xóa sẽ xóa cả câu hỏi, câu trả lời và feedback trong DB hiện tại. Không xóa tài liệu nguồn, tài khoản hay bản sao lưu trước đó. Chặn xóa khi conversation đang sinh/chờ câu trả lời; thử lại sau. Không có nút hoàn tác. Một user không thể xóa cuộc trò chuyện người khác bằng cách đổi ID.

## Cấu hình model

Quản trị chọn số lượt, context mỗi lượt, trần đầu ra, temperature, lớp GPU và cache. Bảng xem trước cập nhật ngay theo lựa chọn; bảng đang chạy lấy context/số slot từ tiến trình, dùng trần đầu ra phần mềm hiện hành. Lưu cấu hình chưa làm thay context/số slot đang chạy. Nhấn **Khởi động lại model** để áp dụng những trường đó. Temperature và trần đầu ra áp dụng lượt mới.

Không cho dừng/restart/thay config khi đang có lượt model xử lý hoặc chờ. GPU layers = 99 là yêu cầu offload tối đa, không nói model có 99 lớp. Log runtime mới xác nhận số lớp thực sự đã offload.

## Lệnh

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Restart-App.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Demo.ps1
.\.venv-runtime\Scripts\python.exe Backup-Data.py
```

Restart-App chỉ cập nhật backend, giữ model nếu đang chạy. Start kiểm cổng; không chiếm cổng bằng cách dừng dịch vụ không rõ nguồn. Tiến trình nền khởi động ẩn.

## Backup và khôi phục

Nút backup/lệnh Backup-Data tạo bản SQLite nhất quán và JSON seed/cấu hình trong `backups/`. Không chép API key hoặc mật khẩu khởi tạo. DB vẫn chứa tài khoản băm, hội thoại và thông tin phiên, cần giữ nội bộ. Khôi phục: dừng app, sao lưu hiện trạng, thay DB bằng bản đã chọn, khôi phục runtime config nếu muốn, bật lại. Hội thoại đã xóa có thể xuất hiện lại nếu khôi phục backup cũ.

## Lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Web chưa kết nối sau restart | Đợi import thư viện; xem `logs/app.stderr.log` và cổng 8088 |
| Model 401 | Backend/model có đang dùng cùng `model-api-key.txt`; restart model sau đổi key |
| Model không nạp / thiếu VRAM | Giảm context/số lượt, đóng phần mềm GPU không cần thiết; đọc log |
| Câu trả lời bị cắt / schema lỗi | Tăng trần đầu ra trong ngân sách, hỏi ngắn hơn; trần là tối đa chứ không ép model viết đủ |
| Hàng chờ đầy / hết 180 giây | Giảm tải, giảm context/output; thêm slot chưa chắc làm mỗi câu nhanh hơn |
| Không thấy nguồn | Nguồn hết hiệu lực/chưa duyệt/thu hồi hoặc thiếu tài liệu phụ thuộc |
| Giao diện vẫn cũ | Ctrl+F5 |

RAM/VRAM hiển thị toàn máy gồm cả phần mềm khác. RSS các tiến trình có trang chia sẻ, không cộng thẳng để suy ra RAM vật lý. Chỉ số thiếu được đánh dấu không có dữ liệu, không giả lập số đo.
