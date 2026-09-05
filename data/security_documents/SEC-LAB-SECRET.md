# Quản lý secret, token và khóa ứng dụng — bài tập & checklist kỹ thuật

## 1. Tình huống DEMO
Bài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.

## 2. Checklist đề xuất
1. Lập inventory bằng tên và owner, không chép giá trị.
2. Dùng secret giả trong lab để kiểm cấp quyền.
3. Xoay khóa thử và xác minh ứng dụng vẫn hoạt động.
4. Thu hồi khóa cũ rồi kiểm audit truy cập.

## 3. Hồ sơ đầu ra
Inventory metadata; rotation test; bằng chứng thu hồi.

## 4. Điều kiện áp dụng
Xóa secret khỏi commit mới không làm secret đã lộ an toàn trở lại.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP Secrets Management Cheat Sheet. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)