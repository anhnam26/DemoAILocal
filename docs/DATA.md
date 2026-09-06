# Dữ liệu demo, upload và quyền đọc

[Về README](../README.md) · [Cài mới](SETUP.md)

## Bộ dữ liệu chuẩn

| Bộ | Script | Số tài liệu |
|---|---|---:|
| Công ty, dịch vụ và vận hành | `company_data.py` | 251 |
| Kiến thức ATTT và bài tập | `security_data.py` | 48 |
| Gói, SLA và tài chính | `finance_data.py` | 154 |
| Định mức và đầu vào tham khảo | `workflow_data.py` | 28 |
| Tổng | | **481** |

Có 10 khách, 10 hợp đồng, 20 dự án, 20 báo giá, 40 ticket, 16 mã kho và 18 nhân sự giả lập. Dữ liệu công ty/tài chính là snapshot ngày 05/09/2026; không phải khách hoặc sổ kế toán thật. Giá, thuế VAT 10%, SLA và lịch là số mô phỏng để trình diễn phép tính. Nguồn ATTT có liên kết NIST/CISA/OWASP/MITRE và ngày kiểm nguồn trong metadata, không tự cập nhật feed/CVE realtime.

## Cài mới và cập nhật mẫu

Trên lần cài mới, chạy đúng thứ tự bốn script ở [SETUP](SETUP.md), sau đó import app để tạo bảng ứng dụng/user. `company_data.py` tạo bảng docs trước; các bộ sau bổ sung nguồn và liên kết. Không chạy riêng workflow_data trước khi có nền dữ liệu.

Repo có thể kèm JSON/Markdown tổng hợp; SQLite local không được commit. Ứng dụng dùng **bản trong SQLite**, không đọc Markdown xuất ra làm dữ liệu đang hoạt động. Sửa một file JSON có sẵn không tự thay bản ghi SQLite vì startup dùng insert-if-missing.

Khi cập nhật dữ liệu mẫu, backup trước, đọc quy tắc phiên bản trong từng `install()`, chạy các script phụ thuộc theo thứ tự rồi restart backend. Các script cố giữ trạng thái thu hồi/bản upload theo quy tắc hiện tại nhưng không thay cho đối chiếu dữ liệu thực. Không sửa một tổng tiền mà bỏ qua chứng từ/offer/định mức liên quan.

## Hiệu lực tài liệu

Mỗi nguồn có ID, body, category, version, owner, status, valid_from/valid_to; có thể có customer/roles, references, fields hoặc requires. Chỉ approved và trong thời hạn mới được dùng. Nguồn dẫn xuất thiếu bất kỳ requires hợp lệ cũng bị loại.

Số **481 trong DB** không luôn bằng số nhìn thấy trên web: khi ngày máy vượt hiệu lực hoặc nguồn bị thu hồi, số khả dụng giảm. Muốn dùng demo trong tương lai cần biên tập lại ngày phù hợp, không tắt kiểm hiệu lực để che nguyên nhân. Dashboard snapshot không tự đổi thành ngày hiện tại.

## Quyền đọc chung

Cả ba vai trò đọc và hỏi AI từ mọi tài liệu đã duyệt/còn hiệu lực, kể cả kỹ thuật, hồ sơ khách và giá vốn. Metadata role/customer cũ còn để quản lý nhưng không hạn chế đọc ở kho chung. Dashboard vẫn có bộ lọc khách phân công; đó không phải hàng rào giữ bí mật đối với nguồn đã chia sẻ.

Chỉ quản trị thêm/duyệt/thu hồi. Không tải secret hoặc nội dung không muốn toàn bộ tài khoản đọc vào kho chung.

## Tải tài liệu mới bằng web

1. Đăng nhập admin → Quản trị tri thức.
2. Chọn TXT/MD UTF-8 hoặc PDF có text. Tối đa 2 MB, 12.000 ký tự; PDF đọc tối đa 30 trang. Chưa OCR cho ảnh/PDF scan và chưa có antivirus sandbox.
3. Tải lên: tài liệu ở trạng thái pending, chưa dùng cho RAG.
4. Đọc trước, kiểm nội dung và quyền chia sẻ rồi Duyệt.
5. Vào Kho tri thức, tìm mã/tên mới và thử một câu hỏi liên quan.

Muốn ngừng dùng nguồn: Thu hồi trong admin. Khi mở lịch sử có nguồn hết hiệu lực/thu hồi, nội dung cũ có thể bị che để hỏi lại từ nguồn hiện tại. Bản sao đã tải về hoặc screenshot không thể thu hồi từ máy người dùng.

## Có fine-tuning không?

Không. Đây là RAG: TF-IDF tìm đoạn liên quan rồi đưa vào prompt model. Thêm tài liệu làm đổi dữ liệu truy xuất; không thay trọng số GGUF. Feedback không tự trở thành dữ liệu huấn luyện. Model không tự học nội dung user vừa nhập để đưa vào kho chung.
