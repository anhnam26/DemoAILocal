# Historical report. Do not use as current deployment instructions.

# Báo cáo hoàn thiện bản server — 28/09/2026

> Báo cáo lịch sử của các đợt triển khai trước. Bộ test và công cụ đánh giá offline sau đó đã được xóa theo yêu cầu; số liệu kiểm thử dưới đây không phải kết quả kiểm tra sau khi dọn source. Hướng dẫn vận hành hiện tại nằm trong README và DEPLOYMENT.md.

## Phạm vi đã hoàn tất

- Tách bản local cũ, model, llama.cpp, môi trường Python cũ, dữ liệu gốc và tài liệu cũ sang `D:\CyberAnt-Local-Archive-20260928`. Bản archive được đặt lại `LLM_MODE=local`; chưa chạy lại GPU sau khi di chuyển. Không cần archive để chạy bản server.
- Dự án server chỉ dùng OpenRouter. Bỏ mã tải/chạy/điều khiển model local, cấu hình GPU và các script demo cũ. Bỏ nhãn **DEMO** ở góc trên bên phải.
- Giữ nguyên API key và bốn model trong `.env`. Admin chọn model riêng cho từng tài khoản từ danh sách server cho phép; người dùng không tự đổi model bằng request chat.
- Giữ tài khoản, mật khẩu đã hash, hội thoại và dữ liệu đang có trong `data/app.sqlite3`. Theo yêu cầu tiếp theo, thông tin đăng nhập cũ đã được khôi phục vào `data/initial-accounts.json` để tham khảo riêng trên máy phát triển; không có trong Git, Docker image hoặc gói triển khai.
- Kho chuẩn duy nhất `knowledge/documents.json`, gồm **1.194 tài liệu lý thuyết**; không cần thư mục dữ liệu gốc để khởi động. Đồng bộ có kiểm tra nguồn, cập nhật thêm/sửa/xóa và giữ tài liệu đã thu hồi. Kho chung cho member/admin, không phân sale/kỹ thuật.
- Admin tạo tài khoản, nhập mật khẩu mới hoặc cấp ngẫu nhiên, khóa tài khoản/thu hồi phiên, gán model, đặt hạn mức tháng và xem lượng token của mọi tài khoản. Người dùng xem hạn mức của chính mình.

## Cách tính và bảo vệ hạn mức

Hạn mức tháng mặc định **1.000.000 token**, bao gồm đầu vào và đầu ra; tháng tính theo **UTC**. Đặt 0 để chặn gọi AI. Mỗi tài khoản có thể chỉnh riêng; admin cũng áp dụng hạn mức.

Trước khi gửi API, giữ trước ngân sách bằng transaction SQLite để các lượt đồng thời không cùng tiêu phần còn lại. Sau đó ghi usage thực do OpenRouter trả về và hoàn phần dự phòng thừa. Lưu ledger độc lập với hội thoại: xóa chat, đổi mật khẩu hay đổi model không xóa lượng đã dùng. Usage hợp lệ trong lịch sử cũ được nhập một lần.

Timeout hoặc tiến trình dừng khi API có thể đã nhận yêu cầu được đánh dấu **Cần đối soát** và vẫn giữ dự phòng. Admin chỉ giải quyết sau khi kiểm tra OpenRouter, nhập số thực và ghi chú; hệ thống lưu audit. Không tự retry và không tự chuyển sang model khác.

Ước lượng đầu vào không phải tokenizer chính xác của tất cả model. Nếu provider tính cao hơn dự phòng, hệ thống ghi toàn bộ số thực và chặn lượt tiếp theo; không tuyên bố đây là trần cứng do OpenRouter thực thi. Lượt đã gửi trước khi admin giảm hạn mức/khóa tài khoản vẫn có thể phát sinh usage.

## Tối ưu token và tài nguyên

- Xếp hạng từ/ký tự và ưu tiên nhóm A–F trên CPU, không trả tiền cho một lượt API phân loại.
- Chỉ đóng gói các đoạn liên quan, tối đa 6 đoạn, loại dòng lặp, giới hạn prompt bằng `RAG_INPUT_TOKENS` (mặc định 6.000 theo ước lượng byte UTF-8 bảo thủ).
- Không gửi cả nhóm tài liệu hoặc toàn bộ lịch sử. Câu hỏi tiếp chỉ thêm chủ đề trước tối đa 350 ký tự khi cần.
- Mặc định tối đa 1.000 token đầu ra; còn ít hạn mức thì giảm trần đầu ra. Yêu cầu thiếu căn cứ/hồ sơ khách hàng không cần gọi model.
- Cache một phiên bản chỉ mục truy xuất; khóa lúc dựng chỉ mục để nhiều câu hỏi đầu tiên không cùng dựng nhiều bản, tránh tăng RAM đột ngột.
- Giới hạn mặc định 4 lượt API đồng thời và 16 lượt chờ. Dependencies runtime tách khỏi công cụ kiểm thử và không còn thư viện phục vụ GPU/nhập Word/Excel.

Một lượt thử thật “DNS là gì?”: **1 API call**, **1.464 input + 58 output = 1.522 token**, trích nguồn hợp lệ, provider báo cost 0 với model `:free`. Ước lượng giữ trước đầu vào là 5.887; đây là ví dụ thực tế, không phải cam kết số token cho mọi câu hỏi.

## Docker và kiểm thử

Đã thêm Dockerfile, Compose, dependency lock, mẫu `.env`, Nginx HTTPS và hướng dẫn chuyển DB. Container chạy non-root, root filesystem read-only, named volume lưu dữ liệu, cổng host chỉ mở loopback. Image không chứa `.env`, DB, mật khẩu, tests hoặc model local.

- **32 kiểm thử Python đã qua** trong môi trường sạch `D:\CyberAnt-Server-Tools\.venv`; dependency check không có xung đột.
- Kiểm thử quota đồng thời, chuyển tháng, lỗi mạng, khôi phục pending sau crash, usage dù trả lời lỗi, quyền admin, model theo tài khoản, thu hồi phiên khi đổi mật khẩu, production bootstrap, Secure cookie/Host/Origin và backup SQLite nhất quán.
- Trình duyệt Edge headless: tạo/sửa tài khoản, đổi mật khẩu, gán model/hạn mức, quota 0 chặn trước API, thống kê, trang hệ thống, bỏ nhãn DEMO; không có lỗi JavaScript.
- Kiểm thử tích hợp thật qua OpenRouter thành công bằng model miễn phí mặc định. Xóa hội thoại sau lượt thử không xóa usage.
- Cả bốn ID model trong `.env` có trong danh mục OpenRouter tại thời điểm kiểm tra. Ba model còn lại chưa gọi sinh câu trả lời thật để tránh phát sinh phí ngoài lượt kiểm tra miễn phí.
- Test và dữ liệu QA nằm tách biệt với DB đang dùng. Công cụ/log/ảnh QA nằm ngoài dự án tại `D:\CyberAnt-Server-Tools`.

**Giới hạn xác minh:** máy hiện tại chưa có Docker; chưa build/run container Linux, chưa kiểm thử tải, HTTPS hoặc restore trên server thực. Hai cảnh báo deprecation của thư viện kiểm thử không làm thất bại test.

## Cần thực hiện khi có server

1. Chốt domain, thiết lập DNS/TLS và `APP_ORIGINS` HTTPS chính xác. Build/run Docker và kiểm tra health, login, quyền admin, model, hạn mức.
2. Nếu giữ tài khoản/hội thoại hiện có, chuyển SQLite snapshot riêng vào named volume đúng quyền UID 10001 trước khi khởi động. Docker image không tự mang DB máy phát triển. Xem `DEPLOYMENT.md`.
3. Sao lưu định kỳ ra nơi khác và thử phục hồi. Hệ thống hiện có nút tạo snapshot; chưa cấu hình lịch backup ngoài máy/server.
4. Chạy thử tải với số người dùng dự kiến. Hiện chỉ hỗ trợ **một worker/một instance**. Nhiều replica cần chuyển DB/điều phối hàng chờ phù hợp.
5. Đánh giá chất lượng trên tập câu hỏi thật trước khi giảm ngân sách thêm. Có thể bổ sung embeddings CPU/reranker khi tìm kiếm từ khóa bỏ sót; không nên thêm API phân loại mặc định khi chưa có số liệu chứng minh hiệu quả.
6. Nếu cần tối ưu tiếp: tokenizer đúng từng model, cache câu trả lời có gắn phiên bản nguồn, đối soát generation tự động khi có ID, lưu lịch sử thay đổi hạn mức và cảnh báo chi phí theo USD. Chi phí/token khác nhau giữa model nên quota token chưa phải quota tiền.

Gói nguồn triển khai được tạo ngoài dự án tại `D:\CyberAnt-Server-Release-20260928.zip`; chỉ chứa mã runtime, dữ liệu lý thuyết và hướng dẫn/cấu hình mẫu, không chứa secret hoặc tài khoản. SQLite snapshot chuyển server được lưu riêng trong `D:\CyberAnt-Server-Tools\migration`.

## Cập nhật lệnh Windows theo yêu cầu

`Start-App.ps1` chạy nền; `Stop-App.ps1` dừng ứng dụng bằng lệnh, không cần Ctrl+C. Ghi nhận PID và thời điểm tạo tiến trình để tránh dừng nhầm PID tái sử dụng; không dừng hàng loạt Python. Đã kiểm tra start, start lặp không tạo thêm tiến trình, health/đăng nhập admin cũ, stop và stop lặp. Sau kiểm tra, ứng dụng được để ở trạng thái đã tắt.

Ba tài khoản `sales`, `kythuat`, `admin` còn hoạt động; cả ba mật khẩu trong file tham khảo đều đã được đối chiếu với hash hiện có. Không đặt lại mật khẩu hoặc thay đổi vai trò của các tài khoản.

## Cập nhật Linux / Miniconda

Đã thay hai script shell bằng `main.py`. Entry point chạy UI và backend bằng Python trong env Conda, đọc .env của dự án, dùng một worker và giữ dữ liệu trong data/app.sqlite3 mặc định. Bind cổng trước khi import app để lần start trùng cổng không chạy lại bước khôi phục usage của DB.

Thêm `deploy/cyberant.service.example` để chạy nền, start/stop qua systemd; không cần Ctrl+C khi vận hành bằng service. Cập nhật Run.txt và DEPLOYMENT.md cho Miniconda, chuyển DB và cấu hình service. Docker vẫn là tùy chọn riêng. Hai file shell đã xóa khỏi source và gói ZIP mới.

Kiểm thử: main.py khởi động ứng dụng thật trên cổng riêng với DB tạm, health/UI/tài liệu/đăng nhập hoạt động, start trùng cổng bị từ chối và không sửa DB, tham số cổng sai bị từ chối. Máy phát triển chưa có Conda/systemd Linux; việc cài service và chạy trên server đích cần kiểm tra tại đó.
