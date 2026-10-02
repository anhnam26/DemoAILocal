# Phát triển

Python 3.14, FastAPI/Uvicorn, SQLite, OpenRouter, JS/CSS thuần.
Không thêm GPU runtime hoặc framework frontend trong đợt chuẩn hóa.

- Backend dưới `cyberant/`, import không ghi dữ liệu.
- Init/migrate rõ ràng qua `cyberant.operations`, schema cũ chỉ nâng trên snapshot.
- Tất cả truy cập runtime qua `cyberant.storage.connect`; không bypass khóa ghi,
  không bật WAL trên các DB attached. Dùng local filesystem, một process.
- `users` là TEMP VIEW tương thích join auth.accounts/users.profiles, không có
  bảng gộp tài khoản/hồ sơ trên đĩa. Trigger tạm cập nhật hai kho trong transaction.
- Giữ ID, password hash, quyền sở hữu, trạng thái nguồn, usage và dữ liệu cũ.
- Test dữ liệu tạm, không log secret hoặc gọi OpenRouter thật.

```bash
python -m unittest discover -s /absolute/path/TestSystem/tests -v
```

Browser cần Playwright/Chromium trong môi trường test, không dependency runtime.
Tests không phải file thừa; gói server loại bằng allowlist.
Nguồn tri thức: một JSON/tài liệu. Khi sửa/thêm/xóa, cập nhật SHA-256 bytes/danh mục
trong manifest. Loader kiểm toàn bộ trước transaction; không nâng nhãn draft thành
verified chỉ vì dữ liệu hợp lệ về cấu trúc.