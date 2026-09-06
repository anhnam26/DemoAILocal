# Chuẩn bị mã nguồn để public GitHub

## Bộ export có chọn lọc

```powershell
.\.venv-runtime\Scripts\python.exe export_public.py
```

Kết quả `exports/cyberant-ai-source.zip` chỉ gồm danh sách source, static, docs, tests và cấu hình ví dụ được cho phép. Loại toàn bộ data, model, runtime, môi trường Python, logs, artifacts, backups và **lịch sử .git**. Bộ dữ liệu mẫu được tái tạo bằng script trên máy cài đặt mới.

Script kiểm tra các file xuất có chứa giá trị API key/mật khẩu khởi tạo hiện tại hay không; không in các giá trị bí mật. Báo cáo có số file và SHA-256. Kiểm tra này chỉ nhận diện những secret hiện biết, không thay cho rà soát nội dung hoặc secret scanning của GitHub.

## Cách sử dụng

Giải nén bộ source vào một thư mục mới, đọc README và thử quy trình cài đặt. Khi chủ dự án quyết định công bố, dùng thư mục sạch này để tạo repository. Script export **không tự tạo repo, commit, push hoặc đổi quyền public**.

Không upload nguyên thư mục đang vận hành. `.gitignore` không loại được file từng commit khỏi lịch sử. Nếu dùng repository làm việc có sẵn, cần rà soát cả lịch sử; bộ ZIP sạch tránh mang theo lịch sử đó.

Không đưa lên GitHub: `initial-accounts.json`, `model-api-key.txt`, SQLite/WAL/SHM, runtime config thật, logs, ảnh chụp có thông tin nội bộ, backup, dữ liệu khách hàng thật hoặc credential mới tạo. Cấu hình ví dụ không có khóa/mật khẩu.

## Nhận diện và giấy phép

Tên CyberAnt trong demo không tự chứng minh đây là bản phát hành chính thức. Chủ dự án quyết định quyền dùng tên/thương hiệu và giấy phép mã nguồn trước khi công bố. Không tự gán giấy phép cho dữ liệu hoặc thành phần bên thứ ba; xem giấy phép riêng của model, runtime, thư viện và nguồn tham khảo.
