# Bảo mật API và kiểm quyền trên đối tượng — bài tập & checklist kỹ thuật

## 1. Tình huống DEMO
Bài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.

## 2. Checklist đề xuất
1. Tạo hai tenant và dữ liệu giả lập riêng.
2. Kiểm user chỉ đọc/sửa đối tượng được cấp.
3. Kiểm endpoint quản trị bằng user thường.
4. Đánh giá giới hạn tài nguyên và inventory API.

## 3. Hồ sơ đầu ra
Ma trận vai trò/endpoint; kết quả positive/negative test.

## 4. Điều kiện áp dụng
Chỉ kiểm môi trường và tài khoản được phép; WAF không thay kiểm quyền trong backend.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP API Security Top 10:2023. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP API Security Top 10:2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)