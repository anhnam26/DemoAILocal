# Sử dụng ứng dụng sau khi cài

[Về README](../README.md) · [Cài đặt](SETUP.md)

## 1. Đăng nhập và giao diện

Mở `http://127.0.0.1:8088`, nhập username/mật khẩu local. Mật khẩu lần đầu nằm trong `data/initial-accounts.json`. Dùng nút ☰ góc trên để mở/đóng thanh bên; lựa chọn được lưu trong trình duyệt. Ctrl+F5 nếu giao diện vẫn là bản cũ sau cập nhật.

## 2. Hỏi trợ lý

Nhập một câu rõ dịch vụ/chủ đề. Ví dụ:

| Câu thử | Mục đích |
|---|---|
| Firewall mạng và WAF khác nhau như thế nào? | So sánh có bảng và nguồn |
| Triển khai firewall bao lâu và mất bao nhiêu tiền? | Giá/ngày demo từ dữ liệu có cấu trúc |
| Cần hỏi khách những gì trước khi triển khai Wi-Fi? | Qwen tổng hợp từ tài liệu |
| Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì? | Kiến thức ATTT và checklist |
| Công nợ An Minh Retail còn bao nhiêu? | Tra cứu sổ demo |

Nguồn nằm dưới câu trả lời và ở bảng bên phải trên màn hình lớn. Bấm mã tài liệu để đọc. Dùng A−/A+ chỉnh chữ, Sao chép, Lưu .md, Thu gọn hoặc phản hồi Hữu ích/Báo sai. Phản hồi không tự huấn luyện lại model.

Câu tiếp nối như “Tạo bảng so sánh hai cái đó” có thể dùng chủ đề trước trong cùng cuộc trò chuyện. Một cửa sổ đang trả lời sẽ chờ hoàn tất trước khi gửi tiếp. Những user/conversation khác vẫn có thể xử lý đồng thời theo số slot.

## 3. Kho tri thức

Cả ba vai trò đọc cùng kho đã duyệt và còn hiệu lực, kể cả runbook, hồ sơ khách và nguồn tài chính. Lọc theo chủ đề, tìm tên/mã để mở tài liệu. Tài liệu pending/thu hồi/hết hạn không tham gia hỏi đáp. Chỉ admin được upload/duyệt/thu hồi.

## 4. Lịch sử trò chuyện

Mỗi tài khoản có danh sách riêng, tìm theo tiêu đề, mở lại để xem hoặc hỏi tiếp sau đăng nhập lại. Cuộc trò chuyện mới bắt đầu chủ đề khác, không xóa cuộc cũ. Một lần tải tối đa 100 lượt gần nhất; dùng nút xem tin cũ nếu có.

Nút **Xóa cuộc trò chuyện** nằm trên từng thẻ. Hủy xác nhận thì không xóa. Đồng ý sẽ xóa câu hỏi, câu trả lời, feedback và liên kết phiên trong database hiện tại; không có hoàn tác. Không được xóa của người khác hoặc khi cuộc đó đang xử lý. Backup cũ và nội dung đã tải xuống không bị xóa theo.

## 5. Hồ sơ công ty và tài chính

Lọc hồ sơ theo loại, tìm mã/tên khách, đọc nguồn hoặc chọn Hỏi trợ lý. Dashboard vẫn lọc nhóm khách phục vụ công việc; tài liệu tương ứng trong kho chung đã được mở đọc cho tất cả.

Tài chính demo có 20 gói, phép tính trọn gói, SLA, chứng từ và công nợ. Giá và VAT đều mô phỏng. Admin có bảng quản trị tài chính rộng hơn. Module Dự toán dịch vụ không còn; không tìm nút gửi/duyệt dự toán dịch vụ trong bản hiện tại.

## 6. Tài khoản

Đổi mật khẩu tại Tài khoản bằng mật khẩu hiện tại. Thay đổi làm đăng xuất các phiên của tài khoản, cần đăng nhập lại. Nếu quên, nhờ admin đặt lại; không sửa tay `initial-accounts.json` để thay mật khẩu trong DB.

## 7. Chức năng admin

| Mục | Tác dụng |
|---|---|
| Người dùng | Tạo/sửa/khóa, role, nhóm khách dashboard, đặt lại mật khẩu |
| Phiên online | Xem hoạt động gần đây, thu hồi từng phiên |
| Quản trị tri thức | Tải tài liệu, đọc trước, duyệt/thu hồi, xem audit/hội thoại |
| Hệ thống local | CPU/RAM/VRAM, context/slot, log, backup, điều khiển model |

Online là hoạt động trong 75 giây gần nhất, không đồng nghĩa đang gõ. Admin có trang hội thoại toàn hệ thống; lịch sử cá nhân admin vẫn riêng theo tài khoản.

Để chỉnh model: nhập số lượt/context/trần trả lời, xem bảng dự kiến, Lưu, sau đó Khởi động lại model để áp dụng context/số slot. Trần đầu ra và temperature dùng ở lượt mới; xem [TOKEN_LIMITS](TOKEN_LIMITS.md). Không tắt model khi người khác đang dùng.
