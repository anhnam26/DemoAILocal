# Prompt injection và bảo vệ AI nội bộ RAG — bài tập & checklist kỹ thuật

## 1. Tình huống DEMO
Bài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.

## 2. Checklist đề xuất
1. Tạo tài liệu lab chứa yêu cầu bỏ qua quy tắc.
2. Kiểm tài liệu chưa duyệt không được truy xuất.
3. Dùng hai vai trò để kiểm nguồn ngoài quyền không vào prompt.
4. Kiểm đầu ra và xác nhận không có hành động bên ngoài.

## 3. Hồ sơ đầu ra
Bộ câu hỏi adversarial; trace nguồn; kết quả ACL.

## 4. Điều kiện áp dụng
Không coi system prompt hoặc nhãn DEMO là ranh giới bảo mật đầy đủ.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP LLM Prompt Injection Prevention. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)