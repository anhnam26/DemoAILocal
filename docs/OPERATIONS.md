# Vận hành

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Restart-App.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Demo.ps1
```

Launcher chỉ khởi động model GPU khi chọn local. Restart chỉ nạp lại backend, giữ model đã chạy. Đổi mode không tự dừng tiến trình GPU đang tồn tại; có thể dừng model trong chế độ local trước khi chuyển API để giải phóng VRAM.

Sửa nguồn chuẩn rồi bấm Đồng bộ kho tri thức. CLI `sync_knowledge.py` tạo bản chuẩn; cần restart để áp dụng vào DB đang chạy. Nút đồng bộ trên web áp dụng ngay.

Sao lưu trong Hệ thống tạo SQLite snapshot và JSON runtime/tri thức, bỏ initial-accounts. Muốn khôi phục đầy đủ cần lưu thêm `data/sources`, NewData và .env ở nơi phù hợp; backup mặc định không đóng gói Word/Excel/nguồn gốc. Không phục hồi backup demo cũ chứa khách hàng vào hệ thống mới.

Logs tại `logs/`, reports tại `artifacts/`. Không đưa key, tài khoản khởi tạo hoặc log câu hỏi nhạy cảm vào Git. Chạy một uvicorn worker. Trước mở LAN cần thiết kế TLS, xác thực và chính sách dữ liệu phù hợp.
