# Bảo mật và phạm vi sử dụng

[Về README](README.md) · [Dữ liệu](docs/DATA.md)

## Quyền và dữ liệu

Kho tri thức là **kho chung cho mọi tài khoản đã đăng nhập**. Không dùng nhãn role/customer để giữ bí mật trong kho này. Quản trị có quyền quản lý hệ thống và xem hội thoại toàn hệ thống. Lịch sử cá nhân và DELETE conversation kiểm user sở hữu ở backend.

Có mật khẩu scrypt/salt, cookie HttpOnly/SameSite Strict, token phiên băm, giới hạn đăng nhập sai, thu hồi phiên, host/origin allowlist, kiểm duyệt/hiệu lực nguồn. API model dùng key local, không gửi key xuống JavaScript. Model không có shell, gửi email hoặc connector bên ngoài. Những cơ chế này không phải chứng nhận đã kiểm toán production.

## File riêng trên máy

Không commit `data/initial-accounts.json`, `data/model-api-key.txt`, DB, cấu hình runtime, log, backup hoặc nội dung khách thật. Mật khẩu được sinh ngẫu nhiên riêng khi cài mới; không có mật khẩu dùng chung công khai. Đổi mật khẩu trong web, không sửa file khởi tạo để thay DB. Khi đổi key model phải restart model để thống nhất với backend.

Xóa hội thoại làm mất dữ liệu trong DB hiện tại và feedback, không xóa backup cũ/bản tải xuống. Dữ liệu không có retention job tự xóa theo hạn. Audit local chưa chống sửa; backup chưa mã hóa tự động.

## Giới hạn triển khai

App/model bind loopback; chưa HTTPS/SSO/MFA, HA, OCR sandbox, antivirus upload, quản trị secret doanh nghiệp hoặc pentest production. Chỉ sử dụng upload đáng tin cậy phù hợp kho chung. Chưa có tự động kiểm soát lưu lượng toàn máy hoặc chứng minh cách ly Internet vật lý.

Không đổi `0.0.0.0`, bật CORS tùy ý hoặc nhiều worker để dùng cho cả công ty mà bỏ qua thiết kế triển khai. Source hiện hướng dẫn Windows local; phương án mạng cần HTTPS, kiểm quyền và kiểm tải tương ứng.

## Báo lỗi an toàn

Issue thông thường nên mô tả bước tái hiện bằng dữ liệu mẫu, phiên bản và lỗi đã che thông tin. Không đăng mật khẩu, API key, database hoặc hội thoại riêng trong issue public. Vấn đề nhạy cảm cần gửi qua kênh riêng do chủ repository công bố; tài liệu không tự tạo địa chỉ hỗ trợ/SLA không có thật. Secret đã lộ cần thu hồi/đổi và kiểm nơi lưu trước đó.
