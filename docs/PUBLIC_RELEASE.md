# Làm việc với repository GitHub

[Về README](../README.md)

## Người tải repo để chạy

Clone hoặc Download ZIP trực tiếp từ GitHub rồi làm theo [SETUP](SETUP.md). **Không cần thư mục exports hoặc gói cyberant-ai-source.zip.** Những file runtime/model/Python/credential bị bỏ khỏi Git sẽ được tải hoặc tạo local trong các bước cài.

## Chủ repo cập nhật mã nguồn

Commit source, giao diện, tài liệu, test và dữ liệu mẫu tổng hợp đã rà soát. Trước commit, kiểm:

```powershell
git status --short
git diff --check
git ls-files --cached --ignored --exclude-standard
git check-ignore data/initial-accounts.json data/model-api-key.txt data/demo.sqlite3 data/runtime-config.json
```

Dòng liệt kê tracked-but-ignored nên trống. Nếu có kết quả, `.gitignore` không tự bỏ theo dõi file đó; cần xử lý từng file, giữ bản local cần thiết và kiểm lịch sử trước khi public. Đừng dùng lệnh xóa hàng loạt thư mục đang hoạt động để “làm sạch repo”.

Giữ ngoài Git: mật khẩu, API key, SQLite cùng WAL/SHM, config thật, log, backup, artifact có thông tin riêng, môi trường Python, runtime và trọng số. `.gitignore` không xóa bí mật từng commit khỏi lịch sử. Nếu secret đã lộ cần đổi/thu hồi secret, không chỉ thêm pattern ignore.

Không có thao tác commit/push/tạo repository/public tự động khi Start-Demo chạy. Việc phát hành source do chủ repo thực hiện.

## Công cụ export tùy chọn

`export_public.py` là tiện ích đóng gói source có chọn lọc, chỉ dùng khi muốn gửi một bản source tách khỏi lịch sử Git. Nó không phải bước cài đặt hoặc chạy hằng ngày. Chạy tiện ích sẽ **tạo lại exports/** và ZIP; không chạy nếu chỉ muốn làm việc với repo hiện tại.

`validate_public_export.py` kiểm gói ZIP nếu đã tạo. Nó không thay thế kiểm cài từ clone. `audit_public_secrets.py` là công cụ riêng của máy đang có file credential local, chỉ kiểm giá trị secret hiện biết; không phải quét mọi loại bí mật. Không công bố report/log nội bộ chỉ để chứng minh đã test.

## Nhận diện và giấy phép

Tên trong demo không tự chứng minh đây là bản phát hành thương mại chính thức. Chủ repo quyết định giấy phép source và quyền dùng tên/thương hiệu. Model, llama.cpp, thư viện và nguồn tài liệu có điều kiện sử dụng riêng; không tự gán một giấy phép chung cho tất cả thành phần.
