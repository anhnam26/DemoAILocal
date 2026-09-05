# Log bảo mật: thu thập và bảo vệ dữ liệu — kiến thức & tư vấn

## 1. Hiểu đúng
Log ứng dụng bổ sung bối cảnh mà log hạ tầng có thể thiếu. Nên ghi ai làm gì, khi nào, ở đâu và kết quả; tránh ghi mật khẩu, token và dữ liệu nhạy cảm không cần thiết.

## 2. Câu hỏi khảo sát đề xuất
Log có request ID và múi giờ? Ai được đọc? Có lọc thông tin nhạy cảm?

## 3. Bằng chứng nên yêu cầu
Schema; mẫu log đã che; kiểm quyền đọc; báo cáo thất thoát.

## 4. Giới hạn
Không tự đặt retention pháp lý hoặc ghi toàn bộ payload khách hàng.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP Logging Cheat Sheet. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)