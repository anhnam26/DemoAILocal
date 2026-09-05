# Hardening container và kiểm image — bài tập & checklist kỹ thuật

## 1. Tình huống DEMO
Bài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.

## 2. Checklist đề xuất
1. Kiểm manifest và nguồn image trong lab.
2. Thử quyền tối thiểu và filesystem chỉ đọc khi tương thích.
3. Giới hạn tài nguyên, network và quyền mount.
4. Quét image, xử lý phát hiện và kiểm lại ứng dụng.

## 3. Hồ sơ đầu ra
Danh sách image; kết quả scan; manifest đã review.

## 4. Điều kiện áp dụng
Không cung cấp lệnh hardening chung cho mọi workload hoặc coi container là VM cách ly tuyệt đối.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP Docker Security Cheat Sheet. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)