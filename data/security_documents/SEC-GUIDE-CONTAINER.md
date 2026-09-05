# Hardening container và kiểm image — kiến thức & tư vấn

## 1. Hiểu đúng
Container dùng chung một phần nền tảng host nên cần kiểm quyền và cấu hình. Tránh đặc quyền không cần thiết; quản lý image và cập nhật phụ thuộc phải đi cùng vận hành.

## 2. Câu hỏi khảo sát đề xuất
Ai tạo image? Có chạy root/privileged? Volume và secret được cấp thế nào?

## 3. Bằng chứng nên yêu cầu
Danh sách image; kết quả scan; manifest đã review.

## 4. Giới hạn
Không cung cấp lệnh hardening chung cho mọi workload hoặc coi container là VM cách ly tuyệt đối.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP Docker Security Cheat Sheet. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)