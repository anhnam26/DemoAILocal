# Quản lý secret, token và khóa ứng dụng — kiến thức & tư vấn

## 1. Hiểu đúng
Secret cần có owner, quyền truy cập, vòng đời và khả năng thu hồi. Tránh hardcode trong source hoặc đưa vào log; ưu tiên kho quản lý tập trung và danh tính workload phù hợp.

## 2. Câu hỏi khảo sát đề xuất
Secret đang nằm ở file, CI hay kho mã? Có biết ứng dụng nào dùng khi xoay khóa?

## 3. Bằng chứng nên yêu cầu
Inventory metadata; rotation test; bằng chứng thu hồi.

## 4. Giới hạn
Xóa secret khỏi commit mới không làm secret đã lộ an toàn trở lại.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP Secrets Management Cheat Sheet. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)