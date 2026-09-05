# Phân đoạn mạng và hạn chế lan truyền — kiến thức & tư vấn

## 1. Hiểu đúng
Phân đoạn chia vùng theo mức tin cậy và nhu cầu giao tiếp. VLAN tạo phân tách logic; cần kiểm soát lưu lượng giữa vùng và quyền quản trị để giảm di chuyển ngang.

## 2. Câu hỏi khảo sát đề xuất
Mạng khách, camera, server và quản trị đang dùng chung? Ứng dụng cần cổng nào?

## 3. Bằng chứng nên yêu cầu
Ma trận luồng; rule có owner; UAT từng ứng dụng.

## 4. Giới hạn
Không đổi rule production dựa trên sơ đồ thiếu phụ thuộc DNS, AD hoặc backup.

## Nguồn và biên soạn
Tham khảo nền tảng: NIST CSF 2.0. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [NIST CSF 2.0](https://www.nist.gov/cyberframework/faqs)