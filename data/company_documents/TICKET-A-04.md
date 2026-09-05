# An Minh Retail — WAF chặn nhầm upload

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: TICKET-A-04 | Phiên bản: company-demo-2.0 | Vai trò: technical, admin | Khách: A

Ticket giả lập TICKET-A-04, khách An Minh Retail. Sự cố: WAF chặn nhầm upload. Mức độ P3. Mở lúc 2026-09-04 09:00 +07; phản hồi 09:20 +07. Trạng thái Đã đóng. Kỹ sư Hoàng Nam/điều phối Thu Hương. Nguyên nhân đã xác minh trong kịch bản: Rule false positive với multipart request. Khắc phục: Xác minh request hợp lệ, thêm ngoại lệ hẹp theo đường dẫn sau test. Đóng lúc 2026-09-04 16:00 +07; khách xác nhận.