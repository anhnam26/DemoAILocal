# Chấp nhận tri thức

`status=approved` cho phép truy xuất; `review_status=accepted` ghi quyết định
chấp nhận sử dụng của người dùng, **không** chứng nhận đã triển khai/kiểm chứng
thiết bị, giá/SLA hoặc dữ liệu khách hàng. Ô CHƯA CÓ/CHƯA XÁC NHẬN vẫn chưa có
dữ liệu; body, ID và source location được giữ nguyên.

Đợt 2026-10-05: 1.100 draft được chấp nhận, 92 reference và 8 source_transcribed
không thay đổi. `review_decision` lưu trạng thái cũ, thời điểm, thẩm quyền và lý do.

## Công cụ quản trị offline

Dừng instance đúng project khi không còn request đang xử lý. Dùng Python hiện
có, không tạo environment. Mặc định công cụ chỉ kiểm kê, không ghi:

```powershell
python -B D:\TestSystem\tools\accept_knowledge.py
python -B D:\TestSystem\tools\accept_knowledge.py --apply --backup-dir D:\CyberAnt-private\acceptance-new --reason 'Owner approved knowledge use'
```

Apply bắt buộc runtime lock, kiểm source/runtime/digest; từ chối divergence
ngoại trừ status retired do quản trị. Backup sáu kho bằng SQLite API, restore
kiểm hash mọi bảng trừ sessions (restore thu hồi session), sao chép corpus và
receipt trước ghi. Không xoá upload/runtime-only; không mở lại retired. Cập nhật
source manifest checksum và source_sync để sync lại không đưa draft trở về.
Database và audit ghi trong một transaction; nếu lỗi trước commit thì khôi phục
file corpus. Không có atomic transaction xuyên filesystem/SQLite khi máy mất
điện: giữ backup và receipt để recovery, không chạy sync khi corpus chưa kiểm.

## Rollback

Backup đợt này: `D:\CyberAnt-private\acceptance-20261005` gồm `runtime`,
`restore-check`, `knowledge`, `acceptance.json`. Giữ ACL private, không commit.
Dừng app, restore `runtime` vào thư mục **mới** bằng operations restore, kiểm
integrity; khôi phục corpus từ `knowledge`, kiểm checksum và cấu hình APP_DATA_DIR
trỏ đích đã kiểm trước restart. Restore thu hồi sessions, cần đăng nhập lại.
Rollback toàn bộ snapshot sẽ mất mọi thay đổi sau snapshot; nếu đã có hoạt động
mới, chỉ đảo metadata những ID trong receipt sau đối chiếu, không restore mù.