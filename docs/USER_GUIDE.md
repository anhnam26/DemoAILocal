# Sử dụng

Đăng nhập bằng tài khoản hiện có. Vai trò thành viên dùng chung kho tài liệu; quản trị có thêm Người dùng, Hệ thống và Quản trị tri thức.

Hỏi bằng tiếng Việt, kèm loại thiết bị/dịch vụ và điều cần biết. Mở nguồn ở cạnh câu trả lời để đối chiếu. Nhãn bản nháp kỹ thuật nghĩa cần kỹ sư kiểm tra; trợ lý không tự cam kết giá, SLA hoặc chạy cấu hình. Lịch sử thuộc tài khoản, tiếp tục được sau đăng nhập lại.

Kho tri thức lọc theo nhóm A–F. Quản trị tải tài liệu lý thuyết, đọc rồi duyệt; thu hồi khi không còn đúng. Không đưa dữ liệu khách hàng vào kho chung.

Hệ thống chọn Local GPU/OpenRouter API. API gửi câu hỏi cùng đoạn tài liệu được chọn tới OpenRouter; key/model được quản lý trong .env. Local dùng model trên máy. Khi chuyển sang Local mà model chưa chạy, bấm Khởi động model. Điều khiển GPU bị vô hiệu trong chế độ API.

Token vào/ra và chi phí hiện dưới câu trả lời nếu provider trả usage. “API đã cấu hình” chỉ xác nhận có cấu hình, không có nghĩa đã thử key hoặc số dư. Lỗi API hiện rõ và không tự retry.
