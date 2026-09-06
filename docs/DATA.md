# Dữ liệu và quyền đọc

Bộ sinh dữ liệu chuẩn tạo 481 tài liệu: 251 công ty, 48 ATTT, 154 tài chính, 28 định mức/đầu vào. Dữ liệu vận hành giả lập gồm 10 khách, 10 hợp đồng, 20 dự án, 20 báo giá, 40 ticket, 16 mã kho và 18 nhân sự. Snapshot nghiệp vụ 05/09/2026 không tự cập nhật theo ngày máy.

| Script | Tác dụng |
|---|---|
| `company_data.py` | Hồ sơ công ty, dịch vụ, runbook, giá/phạm vi |
| `security_data.py` | ATTT có liên kết NIST/CISA/OWASP/MITRE |
| `finance_data.py` | Offer, hóa đơn demo, phiếu thu, công nợ, SLA, P&L |
| `workflow_data.py` | Định mức bổ sung và checklist đầu vào tham khảo |

Các JSON/Markdown được sinh trong data là bản nguồn/đọc; ứng dụng đọc bản SQLite đã duyệt. Restart không ghi đè tài liệu hiện có bằng seed. Script sinh dữ liệu có quy tắc phiên bản riêng; backup trước khi chạy lại.

## Chính sách chia sẻ

Kho tri thức và chat cho mọi tài khoản đọc tất cả nguồn đã duyệt/còn hiệu lực, bao gồm kỹ thuật, hồ sơ khách và giá vốn. Metadata role/customer cũ không giới hạn đọc ở kho chung. Dashboard hồ sơ/tài chính vẫn có bộ lọc phục vụ công việc; đó không phải biện pháp giữ bí mật đối với nguồn đã chia sẻ.

Chỉ quản trị upload/duyệt/thu hồi. Upload TXT/MD UTF-8 hoặc PDF có text, tối đa 2MB, 12.000 ký tự, PDF đọc tối đa 30 trang. Chưa OCR/antivirus. Chỉ đưa tài liệu có thể chia sẻ nội bộ vào kho chung; không đưa mật khẩu, API key hoặc thông tin không muốn toàn bộ user đọc.

Tài liệu mới ở pending, duyệt mới tham gia RAG. Thu hồi/hết hạn làm nguồn bị loại, gồm cả tài liệu dẫn xuất thiếu `requires`. Lịch sử được kiểm lại hiệu lực khi xem. Nội dung đã sao chép/tải xuống không thể thu hồi từ thiết bị người dùng.

Giá và VAT 10% chỉ là tham số demo. Không xem chứng từ giả lập là hóa đơn thương mại hoặc dùng các định mức làm cam kết thật. Không fine-tuning và không tự học từ chat; sửa nguồn là cập nhật dữ liệu truy xuất, không huấn luyện lại trọng số.
