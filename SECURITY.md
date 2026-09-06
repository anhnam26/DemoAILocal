# Bảo mật

## Phạm vi hiện có

Demo local: host/origin allowlist, cookie HttpOnly/SameSite Strict, mật khẩu scrypt, token phiên băm, giới hạn đăng nhập sai, thu hồi phiên, quyền quản trị ở backend, lịch sử theo user và xóa có kiểm chủ sở hữu. Model API có khóa riêng, không gửi khóa xuống JavaScript. AI không có công cụ thực thi lệnh hoặc gọi connector ngoài.

Kho tri thức là **kho chung cho mọi user đã đăng nhập** theo thiết kế. Đừng dùng nhãn customer/role trên tài liệu như biện pháp cách ly bí mật. Quản trị có quyền xem hội thoại toàn hệ thống. Trích dẫn chỉ kiểm ID nguồn, chưa chứng minh nội dung model hoàn toàn đúng.

## Chưa có

HTTPS/SSO/MFA, quản lý secret doanh nghiệp, mã hóa ổ đĩa do app quản lý, audit chống sửa, backup mã hóa/tự động kiểm phục hồi, OCR sandbox, antivirus upload, HA và thẩm định pentest production. Phiên hết hạn sau 12 giờ; không có retention job tự xóa lịch sử theo hạn.

## Báo vấn đề

Không đăng mật khẩu, key, database, hội thoại thật hoặc cách khai thác chứa dữ liệu nhạy cảm trong issue public. Dùng kênh riêng mà chủ repository công bố; tài liệu này không tạo địa chỉ liên hệ hoặc SLA phản hồi giả. Nếu secret đã lộ, thu hồi/đổi secret và kiểm lại nơi đã lưu, không chỉ xóa file khỏi bản mới.
