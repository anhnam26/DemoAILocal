# Dữ liệu, giao dịch và migration

Layout v1: `layout.json` và sáu kho SQLite dưới APP_DATA_DIR:

| Kho | Bảng |
|---|---|
| auth | accounts, sessions, login_attempts, token_usage, usage_migrations |
| users | profiles |
| conversations | conversations, chats, feedback, quality_reports, quality_migrations |
| knowledge | docs, source_sync |
| audit | audit |
| archive | bảng ngoài phạm vi app cũ, giữ nguyên để không mất dữ liệu |

Tài khoản không chứa tên/hồ sơ; profiles không chứa hash mật khẩu. Liên kết bằng
ID giữ nguyên. `users` chỉ là TEMP VIEW join cùng TEMP triggers cho API tương
thích, không có bảng gộp trên đĩa. Các JSON snapshot/result/allowed_models và
payload tài liệu vẫn giữ định dạng để tránh thay toàn bộ nghiệp vụ một lần.

## Nhất quán

`storage.connect` dùng auth làm DB main trên đĩa, ATTACH các kho còn lại.
Tất cả DELETE rollback journals + synchronous FULL. SQLite super-journal cho
atomic commit trên các attached on-disk DB; không có đảm bảo này nếu chuyển WAL,
dùng main in-memory hoặc filesystem không bảo đảm khóa/flush. Chỉ local disk.
RLock bao phủ lifetime connection, serialize writes và snapshot nhiều kho.
Khóa OS theo thư mục data ngăn process khác; một process/một worker.

Giao dịch tạo/cập nhật tài khoản qua TEMP triggers cập nhật cả accounts/profiles
hoặc rollback cả hai. Đây là thay thế cho saga trong thiết kế kho cùng host.
Audit hiện vẫn ghi sau transaction nghiệp vụ như phiên bản cũ, **chưa có outbox**;
lỗi giữa hai bước có thể thiếu audit. Không tuyên bố audit đầy đủ theo chuẩn compliance.
Các liên kết xuyên DB chưa có native FOREIGN KEY; quyền sở hữu kiểm ở nghiệp vụ.

## Migration

`operations migrate --source <legacy.sqlite3> --target <NEW directory>`:
1. Khóa instance thư mục nguồn, snapshot bằng SQLite backup API.
2. Kiểm integrity/tài khoản; nâng schema trên snapshot, không đọc file mật khẩu.
3. Tách accounts/profiles, copy các bảng/index theo kho; bảng không biết vào archive.
4. Đối chiếu số lượng và hash theo cột trước/sau, không in giá trị nhạy cảm.
5. Thu hồi phiên cũ, ghi migration-report/layout/schema version.
6. Kiểm integrity mọi kho, rename staging sang đích mới.

Nguồn không bị ghi đè; lần chạy lại cùng đích bị từ chối thay vì nhân đôi. Không
khởi tạo account khi source rỗng, không tự sync corpus mới trên dữ liệu migrated.
Không merge hai hệ thống đã phát sinh dữ liệu. Nếu staging lỗi không công bố đích.

Server import không ghi DB. Lifespan kiểm layout/integrity, giữ khóa và recovery
usage một lần: in_flight → uncertain, reserved → cancelled. Không chạy CREATE/ALTER
runtime; schema version khác bị chặn. Schema v1 chưa có framework nâng cấp v2:
phải thêm migration có kiểm thử khi có thay đổi tiếp theo.

## Backup/restore

Backup gồm mọi kho + layout + manifest SHA-256. Gate giữ toàn bộ thời gian backup
để login/admin/chat không ghi giữa các snapshot. Không restore từng DB hoặc dùng
copy riêng file đang mở. CLI backup/check cần app dừng; backup admin dùng gate nội bộ.
Restore kiểm danh sách file/checksum/integrity, đích mới, thu hồi phiên.
Code, corpus source, config bí mật lưu riêng; backup có dữ liệu riêng tư.

## Nguồn tri thức

`knowledge/manifest.json` tham chiếu `documents/<A…F>/<ID>.json`, checksum bytes.
1.200 tài liệu giữ ID/nội dung/metadata; A=583, B=275, C=212, D=68, E=48, F=14.
1.100 draft_engineer_review, 92 reference, 8 source_transcribed. Chia file không
xác minh kỹ thuật. Loader chặn đường dẫn ngoài corpus, thiếu/extra/trùng/checksum
lỗi trước sync. Danh mục manifest quyết định xóa có chủ đích, giữ upload riêng và
status retired khi nguồn đổi. Startup không tự sync.

Liên kết dịch vụ/loại bằng chứng được dựng trong chỉ mục, không thêm bảng hoặc
sửa payload nguồn. Chat lưu coverage/packing/audience trong JSON diagnostics.
Coverage không xác minh ngữ nghĩa hoặc thay nhãn duyệt kỹ thuật. Audit nguồn và
DB read-only có chọn đường dẫn rõ ràng: xem `docs/SERVICE_RAG.md`.

## Phần chưa thực hiện

Không tự đổi chính sách mật khẩu/member, thêm hồ sơ mới/CRM, chuẩn hóa toàn bộ
JSON thành bảng quan hệ, outbox audit, MFA/SSO, distributed queue/multiple replica,
cache static hoặc viết lại CSS. Đây là các thay đổi nghiệp vụ/kiến trúc tiếp theo,
không điều kiện để dùng bộ DB tách và triển khai trực tiếp hiện tại.