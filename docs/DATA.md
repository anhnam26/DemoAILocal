# Nguồn dữ liệu duy nhất

Nguồn hoạt động gồm `data/sources/theory.json` (75 tài liệu lý thuyết/ATTT cũ), `data/sources/services.json` (11 đoạn dịch vụ trích từ Word DataReal) và `NewData/data/processed/company_knowledge.jsonl` (1.115 mục mới). Các file Word/Excel/PDF gốc còn để đối chiếu, không được nạp lần hai hay phục vụ qua static.

`sync_knowledge.py` tạo `data/knowledge_documents.json` và manifest, loại trùng nội dung, chuẩn hóa metadata. Startup đồng bộ bản chuẩn vào SQLite; nút **Hệ thống → Đồng bộ kho tri thức** rebuild và áp dụng ngay. Nguồn sửa được cập nhật, nguồn xóa biến mất khỏi DB, tài liệu bị quản trị thu hồi không tự được duyệt lại. Bản upload thủ công giữ riêng trong DB.

Đây là đồng bộ các nguồn chuẩn JSON/JSONL. Thay đổi Excel/Word gốc cần cập nhật bản trích chuẩn trước khi đồng bộ; chưa có bộ biên soạn tự động mọi workbook. `services.json` giữ snapshot đã trích và hash để đối chiếu DataReal.

| Nhóm | Nội dung | Số tài liệu |
|---|---|---:|
| A | Khái niệm, thuật ngữ | 578 |
| B | Cấu hình, xử lý sự cố | 274 |
| C | Khảo sát, phạm vi dịch vụ | 212 |
| D | Quy trình, SOW, triển khai | 68 |
| E | An toàn thông tin | 48 |
| F | Chất lượng dữ liệu, quy tắc | 14 |

Tổng 1.194 sau loại 7 bản trùng. Có 1.100 tài liệu giữ nhãn `draft_engineer_review`, 8 quy trình chép từ nguồn và 86 tài liệu tham khảo. `approved` nghĩa được phép tra cứu, không đồng nghĩa kỹ sư đã phê duyệt nội dung dự thảo. Mốc 2099 chỉ phục vụ khả dụng của tri thức tham khảo, không xác nhận hiệu lực chính sách thương mại.

Đã xóa CRM, hợp đồng, dự án, ticket, chứng từ, bảng giá/tồn kho giả lập và các script sinh lại chúng. Xóa lịch sử/audit cũ, backup, chỉ mục Chroma cũ và sheet/file khách hàng ví dụ; giữ biểu mẫu trống và kiến thức tổng quát. `.local-internal` cùng database/phiếu của phiên bản đó đã được xóa sau khi lấy phần dịch vụ lý thuyết.

Git history có thể vẫn chứa dữ liệu demo của commit cũ; lần thay đổi này không rewrite lịch sử Git hoặc xóa bản sao ngoài workspace.

Upload chỉ nhận TXT/Markdown/PDF có text, tối đa 2 MB và 12.000 ký tự, chờ admin duyệt. Chỉ tải nội dung lý thuyết được phép chia sẻ; không tải hồ sơ khách hàng hoặc secret. Chưa có bộ phát hiện PII tự động đủ tin cậy để thay bước duyệt.
