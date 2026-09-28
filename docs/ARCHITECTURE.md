# Kiến trúc

Một FastAPI process phục vụ `/`, `/api` và giao diện static. Một SQLite `data/demo.sqlite3` lưu người dùng, tài liệu, phiên, hội thoại, phản hồi và nhật ký. Tên DB cũ được giữ để không đổi cơ chế đăng nhập.

`accounts.py`: member/admin, mật khẩu scrypt, phiên có thể thu hồi. Mọi thành viên dùng cùng tri thức; hội thoại vẫn theo chủ tài khoản. `conversations.py` kiểm quyền xem/xóa và ẩn trả lời khi nguồn bị thu hồi.

`sync_knowledge.py`: chuẩn hóa và đồng bộ có hash, loại nguồn bị xóa, giữ trạng thái thu hồi. `rag.py`: ưu tiên nhóm A–F cục bộ, TF-IDF từ + ký tự, mở rộng một số thuật ngữ, chọn đoạn có độ đa dạng, bỏ dòng lặp và giới hạn prompt. Nhóm là ưu tiên mềm để không loại nhầm nguồn liên ngành.

`model_provider.py`: boundary duy nhất cho OpenRouter hoặc llama.cpp. Đọc .env phía server; API URL cố định tới OpenRouter. Gửi prompt và max_tokens, tắt reasoning khi provider hỗ trợ. Không gửi tham số llama.cpp sang API, không retry tự động hoặc tự đổi provider. `generation.py` giới hạn đồng thời và chặn bảo trì khi đang trả lời.

`app.py`: truy xuất, đóng gói, gọi model một lần, kiểm tra mã nguồn, lưu kết quả và usage. Chỉ chuyển chủ đề ngắn của câu hỏi trước cho câu hỏi nối tiếp, không gửi toàn bộ transcript. Kiểm mã trích dẫn không chứng minh nội dung được nguồn hỗ trợ về ngữ nghĩa.

Ứng dụng chỉ bind localhost, chặn Origin/Host ngoài danh sách. Không cấu hình nhiều uvicorn workers vì hàng chờ và khóa ở bộ nhớ một process.
