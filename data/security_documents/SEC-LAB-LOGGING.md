# Log bảo mật: thu thập và bảo vệ dữ liệu — bài tập & checklist kỹ thuật

## 1. Tình huống DEMO
Bài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.

## 2. Checklist đề xuất
1. Thiết kế schema cho đăng nhập và đổi quyền trong app demo.
2. Gửi sự kiện test rồi đối chiếu trên nguồn và nơi nhận.
3. Kiểm log không chứa token/mật khẩu.
4. Thử mất kết nối nơi nhận và ghi cách phục hồi thu thập.

## 3. Hồ sơ đầu ra
Schema; mẫu log đã che; kiểm quyền đọc; báo cáo thất thoát.

## 4. Điều kiện áp dụng
Không tự đặt retention pháp lý hoặc ghi toàn bộ payload khách hàng.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP Logging Cheat Sheet. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)