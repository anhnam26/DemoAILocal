# Login và chat — giao diện ocean

## Thay đổi

- Logo gốc được sao chép nguyên vẹn sang `static/Logo.png`, phục vụ qua `/static/Logo.png`; không mở truy cập thư mục gốc.
- Thành viên dùng thanh bên gồm logo, Chat mới, tìm kiếm, lịch sử nhóm theo thời gian và menu đăng xuất. Không còn nút × cạnh logo; dùng nút ☰, Escape hoặc chạm nền ngoài drawer để đóng. Mục hồ sơ/đổi mật khẩu và điều hướng quản trị chỉ hiện với admin. API tự đổi mật khẩu từ chối thành viên (403); quản trị vẫn đặt lại mật khẩu cho nhân viên.
- Model chuyển lên thanh trên; composer cố định dưới vùng cuộn hội thoại. Bỏ cột nguồn riêng; giữ mã trích dẫn, nút đọc tài liệu, sao chép, tải Markdown và phản hồi.
- Lịch sử có phân trang, trạng thái đang chọn, xác nhận xóa, trạng thái lỗi mạng và chặn chuyển/xóa khi đang xử lý. Giữ API và kiểm tra quyền sở hữu hiện có.
- Theme mặc định theo hệ điều hành, lưu lựa chọn trong localStorage; vẫn hoạt động khi storage bị chặn. Nút theme nằm góc trên bên phải ở login và workspace, hiển thị cả trên mobile và khi sidebar thu gọn.
- Login có nền Aurora bằng CSS gradient: xanh ngọc/lam và cam nhạt ở theme sáng, cyan/lam ở theme tối. Hai lớp nền theo chuột với độ trễ và tốc độ khác nhau; form và chữ đứng yên. Tiêu đề viết hoa “TRA CỨU / NỘI BỘ.”, bỏ đoạn mô tả bên dưới.
- Script `D:\TestSystem\static\login-aurora.js` chỉ dùng requestAnimationFrame khi cần, dừng khi đã ổn định, tab ẩn hoặc login ẩn; chuột rời trang đưa nền về vị trí nghỉ. Thiết bị cảm ứng và prefers-reduced-motion dùng nền tĩnh. Không có canvas, không tải script sóng/vòng elip nước cũ, không thêm thư viện runtime hoặc tài nguyên bên ngoài và không nới CSP.

## Kiểm thử

Chạy từ thư mục dự án:

```powershell
python -m unittest discover -s D:\TestSystem\tests -p test_workspace_ui.py -v
```

Suite tự tạo database trong thư mục tạm, thay cấu hình trong tiến trình (không đọc `.env`), chạy Uvicorn loopback và giả lập `model_provider.complete`. Không gọi OpenRouter thật, không sửa database đang dùng. Chromium/Playwright đã cài trên máy được dùng cho kiểm thử browser; nếu không có, các ca browser báo skip. Không thêm Playwright vào dependency runtime.

Suite hiện gồm **6 ca tích hợp**, bao gồm:

1. API đăng nhập/logout, static logo và CSP, model được cấp/bị từ chối, quyền admin, quyền sở hữu hội thoại, tìm kiếm/phân trang, RAG với phản hồi giả lập, usage không mất khi xóa chat và hạn mức chặn trước provider.
2. Browser desktop: theme lưu qua reload, sidebar thành viên/admin, 56 lịch sử, tìm kiếm, tạo/gửi/khôi phục/xóa chat, hủy xác nhận xóa, đọc tài liệu, truy cập đổi mật khẩu, màn hình người dùng/hệ thống; không ghi nhận lỗi JavaScript hoặc CSP trong luồng kiểm tra.
3. Mobile 390×844: theme hệ thống/nút góc phải, không còn canvas, drawer/Escape/focus, composer trong viewport, không tràn ngang, thành viên không có mục tài khoản và admin vẫn truy cập được.
4. Hội thoại 105 lượt: tải 100 + 5 lượt cũ, lỗi tải lịch sử và thử lại, tìm kiếm rỗng, localStorage bị chặn, vòng focus bàn phím trên drawer.
5. Quyền mật khẩu: chưa đăng nhập nhận 401, thành viên nhận 403 và không mất phiên; admin đặt lại mật khẩu nhân viên, tự đổi mật khẩu, thu hồi mọi phiên cũ và đăng nhập bằng mật khẩu mới.

6. Aurora login: tiêu đề và mô tả, di chuyển chuột ở hai theme, màu riêng theo theme, form/chữ không dịch chuyển, dừng frame khi ổn định/ẩn tab/đã đăng nhập, về vị trí nghỉ khi chuột rời trang, giảm chuyển động và nền tĩnh trên mobile ở cả hai theme.

Đã kiểm cú pháp tất cả JavaScript bằng `node --check`, `git diff --check`, kiểm ID HTML không trùng và xem ảnh chụp desktop/mobile. Ảnh kiểm tra lưu tại `artifacts/ui-review/` (Git bỏ qua), sử dụng dữ liệu giả lập.

## Giới hạn

- Đã chạy Windows / Python 3.13 với dependency có sẵn, không phải môi trường Linux/Python 3.14 khớp toàn bộ lockfile. Có cảnh báo deprecated từ websockets/Uvicorn cài sẵn, không làm test thất bại.
- Browser kiểm tra là Chromium headless và viewport mobile giả lập; chưa nghiệm thu Safari/Firefox, bàn phím ảo điện thoại thật, hiệu năng trên máy yếu thật hoặc screen reader.
- Không kiểm chất lượng/độ trễ model trả phí, kết nối OpenRouter thật hay đường hầm public. Quota không thay đổi; backend tự đổi mật khẩu nay chỉ cho phép admin, còn cơ chế đặt lại mật khẩu của quản trị được giữ nguyên.
- Các thay đổi đã có trong `main.py` và `docs/PUBLIC_SHARE.md` được giữ nguyên.
