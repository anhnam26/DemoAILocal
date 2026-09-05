# Bảo mật API và kiểm quyền trên đối tượng — kiến thức & tư vấn

## 1. Hiểu đúng
API có rủi ro phân quyền đối tượng, xác thực và quản lý tài nguyên. Mỗi yêu cầu phải được kiểm quyền phù hợp; biết hoặc đổi một ID không đồng nghĩa được quyền xem đối tượng.

## 2. Câu hỏi khảo sát đề xuất
API có nhiều tenant? Có tài khoản test từng vai trò? Endpoint cũ còn hoạt động?

## 3. Bằng chứng nên yêu cầu
Ma trận vai trò/endpoint; kết quả positive/negative test.

## 4. Giới hạn
Chỉ kiểm môi trường và tài khoản được phép; WAF không thay kiểm quyền trong backend.

## Nguồn và biên soạn
Tham khảo nền tảng: OWASP API Security Top 10:2023. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [OWASP API Security Top 10:2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)