# Phát triển

FastAPI/Uvicorn, SQLite, OpenRouter, JS/CSS thuần. Windows hiện tại dùng Python
3.13 có sẵn; triển khai Linux có hướng dẫn Python 3.14 riêng.
Không tạo venv, tải Python hoặc tự cài/nâng cấp dependency trên máy Windows này.
Không thêm GPU runtime hoặc framework frontend trong đợt chuẩn hóa.

- Backend dưới `cyberant/`, import không ghi dữ liệu.
- Init/migrate rõ ràng qua `cyberant.operations`, schema cũ chỉ nâng trên snapshot.
- Tất cả truy cập runtime qua `cyberant.storage.connect`; không bypass khóa ghi,
  không bật WAL trên các DB attached. Dùng local filesystem, một process.
- `users` là TEMP VIEW tương thích join auth.accounts/users.profiles, không có
  bảng gộp tài khoản/hồ sơ trên đĩa. Trigger tạm cập nhật hai kho trong transaction.
- Giữ ID, password hash, quyền sở hữu, trạng thái nguồn, usage và dữ liệu cũ.
- Test dữ liệu tạm, không log secret hoặc gọi OpenRouter thật.

Chạy từng suite ở process riêng để giữ isolation của API/UI, không sinh cache:

```powershell
$python = 'C:\Users\anhna\AppData\Local\Microsoft\WindowsApps\python3.13.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
Get-ChildItem 'D:\TestSystem\tests\test_*.py' | ForEach-Object {
    & $python -B -m unittest discover -s 'D:\TestSystem\tests' -p $_.Name -v
    if ($LASTEXITCODE -ne 0) { throw "Suite failed: $($_.Name)" }
}
```

Browser cần Playwright/Chromium trong môi trường test, không dependency runtime.
Nếu chưa có, báo thiếu và bỏ qua browser; không tự tải/cài. Ảnh kiểm thử UI lưu
trong thư mục tạm và tự xóa sau suite, không để artifacts trong source tree.
Tests không phải file thừa; gói server loại bằng allowlist.
Nguồn tri thức: một JSON/tài liệu. Khi sửa/thêm/xóa, cập nhật SHA-256 bytes/danh mục
trong manifest. Loader kiểm toàn bộ trước transaction; không nâng nhãn draft thành
verified chỉ vì dữ liệu hợp lệ về cấu trúc.