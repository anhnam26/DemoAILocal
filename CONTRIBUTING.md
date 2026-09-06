# Hướng dẫn đóng góp

Đọc README, kiến trúc và chính sách kho tri thức chung trước khi thay đổi. Dùng dữ liệu tổng hợp, không thêm credential hoặc tài liệu khách thật vào fixture.

## Quy trình

1. Nêu hành vi trước/sau và phạm vi API/UI liên quan.
2. Dùng DB tạm để kiểm quyền, dữ liệu, phép tính và transaction. Không chạy unit test lên DB thật.
3. Chạy `python -m pytest -q` bằng môi trường dự án. UI dùng Playwright/Chrome với app đang chạy.
4. Với token/runtime, đối chiếu backend, giao diện và Start-Demo; số context hiển thị phải phân biệt mỗi slot/tổng và saved/running.
5. Ghi rõ cấu hình và phép đo khi báo hiệu năng. Nạp model thành công không đồng nghĩa prompt dài đã được xử lý hoặc câu trả lời đúng.
6. Cập nhật docs khi thay quyền, schema, API hoặc giới hạn. Chạy export_public để kiểm bộ source phát hành.

Không chạy nhiều backend worker khi khóa sinh câu trả lời và trạng thái bảo trì còn ở bộ nhớ tiến trình. Không bỏ kiểm quyền DELETE theo user, không xóa conversation đang xử lý và không ghi secret trong log/test output.

UI cần kiểm desktop/mobile, thao tác bàn phím, focus, hover, hội thoại dài và xóa hủy/xác nhận. Kiểm thử model thật có thể chậm, cần chạy trong thời gian phù hợp với người dùng demo.
