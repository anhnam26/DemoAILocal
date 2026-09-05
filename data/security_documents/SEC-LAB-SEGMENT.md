# Phân đoạn mạng và hạn chế lan truyền — bài tập & checklist kỹ thuật

## 1. Tình huống DEMO
Bài tập do nhóm biên soạn demo xây dựng cho công ty dưới 20 người; dùng tài khoản, tài sản và dữ liệu lab. Không phải quy trình hãng hoặc sự cố thật.

## 2. Checklist đề xuất
1. Vẽ sơ đồ vùng và luồng nghiệp vụ.
2. Lập bảng nguồn/đích/dịch vụ/owner.
3. Pilot rule trên lab và thử luồng hợp lệ.
4. Kiểm luồng bị chặn, log và rollback trước mở rộng.

## 3. Hồ sơ đầu ra
Ma trận luồng; rule có owner; UAT từng ứng dụng.

## 4. Điều kiện áp dụng
Không đổi rule production dựa trên sơ đồ thiếu phụ thuộc DNS, AD hoặc backup.

## Nguồn và biên soạn
Tham khảo nền tảng: NIST CSF 2.0. Bản diễn giải tiếng Việt và bài tập do demo biên soạn; không phải bản dịch tiêu chuẩn. Kiểm nguồn ngày 2026-09-05. Các câu hỏi, bước lab và đầu ra là đề xuất cho demo, không phải yêu cầu nguyên văn của nguồn.

- [NIST CSF 2.0](https://www.nist.gov/cyberframework/faqs)