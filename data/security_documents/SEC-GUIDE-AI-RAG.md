# Prompt injection và bảo vệ AI nội bộ RAG — kiến thức & tư vấn

## 1. Hiểu đúng
Prompt injection đưa chỉ dẫn không tin cậy vào câu hỏi hoặc tài liệu. Phân tách chỉ dẫn và dữ liệu giúp giảm rủi ro; kiểm quyền và quyền công cụ phải được thực thi ngoài LLM.

## 2. Câu hỏi khảo sát đề xuất
Tài liệu ai được tải lên? Quyền lọc trước truy xuất? Model có công cụ ghi dữ liệu hoặc gửi email?

## 3. Bằng chứng nên yêu cầu
Bộ câu hỏi adversarial; trace nguồn; kết quả ACL.

## 4. Giới hạn
Không coi system prompt hoặc nhãn DEMO là ranh giới bảo mật đầy đủ.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP LLM Prompt Injection Prevention. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)