from pathlib import Path
docs={
'README.md':r'''# CyberAnt — kho tri thức dùng chung

Một ứng dụng tại http://127.0.0.1:8088, một cơ sở dữ liệu, hai chế độ sinh câu trả lời: **OpenRouter API** hoặc **local llama.cpp**. Không còn trang chọn Demo/Internal hoặc phân chia Sale/Kỹ thuật. Thành viên đọc cùng kho tri thức; quản trị quản lý tài liệu, tài khoản và model.

## Chạy trên máy hiện tại

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

API key và model được đọc từ `.env`: hỗ trợ `API_KEY`/`MODEL` đang có hoặc `OPENROUTER_API_KEY`/`OPENROUTER_MODEL`. Key không được gửi tới trình duyệt. Model dùng ID gốc của OpenRouter, ví dụ `nvidia/nemotron-3-super-120b-a12b:free`, không thêm tiền tố adapter `openrouter/`.

Chọn **Hệ thống → Chế độ trả lời** hoặc đặt `LLM_MODE=openrouter` / `LLM_MODE=local` trong `.env`. Chế độ API khởi động được khi không có GPU, GGUF hay llama-server. Chọn local khi model chưa chạy thì bấm Khởi động model. Không tự chuyển sang nhà cung cấp khác khi gặp lỗi.

Tài khoản hiện có được giữ mật khẩu, chuyển vai trò Sale/Kỹ thuật thành Thành viên. Tên đăng nhập cũ vẫn sử dụng được. Khi cài mới, tạo member/admin với mật khẩu ngẫu nhiên trong `data/initial-accounts.json`.

## Dữ liệu và RAG

Kho hiện có 1.194 tài liệu sau loại trùng: thuật ngữ, cấu hình, khảo sát, quy trình/SOW, ATTT và quy tắc chất lượng dữ liệu. Không có CRM, hợp đồng khách, công nợ, ticket hay hồ sơ khách hàng ví dụ. Hướng dẫn bổ sung chưa được kỹ sư duyệt vẫn mang nhãn `draft_engineer_review`, không trở thành cam kết thực tế.

Luồng: câu hỏi → tìm kiếm từ/ký tự và ưu tiên nhóm trên CPU → chọn tối đa 6 đoạn đa dạng, bỏ phần lặp → giới hạn prompt → một lượt gọi model → kiểm tra mã trích dẫn → lưu lịch sử theo tài khoản. Câu hỏi hồ sơ khách hàng hoặc không tìm thấy nguồn có thể trả lời mà không gọi model.

Không gọi thêm API phân loại cho mọi câu hỏi. Không gửi nguyên nhóm tài liệu. Ngân sách mặc định: `RAG_INPUT_TOKENS=6000`, `RAG_OUTPUT_TOKENS=1000`, `RAG_TOP_K=6`, `API_PARALLEL=2`. Đếm đầu vào theo byte UTF-8 bảo thủ, không phải tokenizer chính xác của mọi model; token thực tế và chi phí lấy từ `usage` của API. Xem [ngân sách](docs/TOKEN_LIMITS.md).

## Tài liệu và kiểm tra

- [Cài đặt](docs/SETUP.md), [sử dụng](docs/USER_GUIDE.md), [dữ liệu](docs/DATA.md).
- [Kiến trúc](docs/ARCHITECTURE.md), [vận hành](docs/OPERATIONS.md), [xử lý lỗi](docs/TROUBLESHOOTING.md).
- [Báo cáo thay đổi và giới hạn](docs/CHANGE_REPORT.md).

```powershell
.venv-runtime\Scripts\python.exe -X utf8 -m pytest -q
.venv-runtime\Scripts\python.exe -X utf8 evaluate_rag.py
.venv-runtime\Scripts\python.exe -X utf8 check_unified.py
# Có gọi OpenRouter thật; có thể tính phí tùy model:
.venv-runtime\Scripts\python.exe -X utf8 check_unified.py --live
```
''',
'docs/SETUP.md':r'''# Cài đặt

Dùng Python 3.14 và môi trường `.venv-runtime` đã kiểm trên Windows. Không cần cài model local nếu chỉ dùng API.

```powershell
python -m venv .venv-runtime
.venv-runtime\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Chỉ sao chép `.env.example` nếu chưa có `.env`; không ghi đè key hiện có. Điền `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` và `LLM_MODE=openrouter` (hoặc các tên `API_KEY`/`MODEL`). Biến môi trường hệ điều hành ưu tiên hơn file.

Đặt nguồn đã lọc ở `data/sources/*.json` và `NewData/data/processed/company_knowledge.jsonl`, rồi chạy:

```powershell
.venv-runtime\Scripts\python.exe -X utf8 sync_knowledge.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
```

Mở http://127.0.0.1:8088. Tài khoản cài mới nằm trong `data/initial-accounts.json`. Không commit file này. Bản clone chỉ có `data/sources/theory.json` vẫn chạy với phần lý thuyết chung; nguồn công ty/NewData phải sao chép riêng nếu không có trong Git.

Local cần `runtime/llama-server.exe`, `models/Qwen3.5-9B-Q4_K_M.gguf`, Vulkan và cấu hình trong `data/runtime-config.json`. Chọn `LLM_MODE=local` trước khi chạy launcher. Dùng script `download_model.py` nếu cần tải GGUF theo cấu hình sẵn; kiểm tra dung lượng và nguồn model trước tải.

Kiểm thử UI dùng Microsoft Edge đã cài trên máy; không bắt buộc tải Chromium của Playwright.
''',
'docs/DATA.md':'''# Nguồn dữ liệu duy nhất

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
''',
'docs/ARCHITECTURE.md':'''# Kiến trúc

Một FastAPI process phục vụ `/`, `/api` và giao diện static. Một SQLite `data/demo.sqlite3` lưu người dùng, tài liệu, phiên, hội thoại, phản hồi và nhật ký. Tên DB cũ được giữ để không đổi cơ chế đăng nhập.

`accounts.py`: member/admin, mật khẩu scrypt, phiên có thể thu hồi. Mọi thành viên dùng cùng tri thức; hội thoại vẫn theo chủ tài khoản. `conversations.py` kiểm quyền xem/xóa và ẩn trả lời khi nguồn bị thu hồi.

`sync_knowledge.py`: chuẩn hóa và đồng bộ có hash, loại nguồn bị xóa, giữ trạng thái thu hồi. `rag.py`: ưu tiên nhóm A–F cục bộ, TF-IDF từ + ký tự, mở rộng một số thuật ngữ, chọn đoạn có độ đa dạng, bỏ dòng lặp và giới hạn prompt. Nhóm là ưu tiên mềm để không loại nhầm nguồn liên ngành.

`model_provider.py`: boundary duy nhất cho OpenRouter hoặc llama.cpp. Đọc .env phía server; API URL cố định tới OpenRouter. Gửi prompt và max_tokens, tắt reasoning khi provider hỗ trợ. Không gửi tham số llama.cpp sang API, không retry tự động hoặc tự đổi provider. `generation.py` giới hạn đồng thời và chặn bảo trì khi đang trả lời.

`app.py`: truy xuất, đóng gói, gọi model một lần, kiểm tra mã nguồn, lưu kết quả và usage. Chỉ chuyển chủ đề ngắn của câu hỏi trước cho câu hỏi nối tiếp, không gửi toàn bộ transcript. Kiểm mã trích dẫn không chứng minh nội dung được nguồn hỗ trợ về ngữ nghĩa.

Ứng dụng chỉ bind localhost, chặn Origin/Host ngoài danh sách. Không cấu hình nhiều uvicorn workers vì hàng chờ và khóa ở bộ nhớ một process.
''',
'docs/TOKEN_LIMITS.md':'''# Ngân sách và giảm token

Phân loại bằng LLM rồi gửi toàn bộ nhóm thường vẫn dư dữ liệu, thêm một lượt mạng và token cho phân loại. Bản này tìm kiếm ngay trên máy và chỉ gửi đoạn phù hợp. Với câu hỏi có nguồn: thông thường **một lượt API**. Câu hỏi không có nguồn/hồ sơ khách hàng: có thể **không gọi API**.

| Biến .env | Mặc định | Ý nghĩa |
|---|---:|---|
| RAG_INPUT_TOKENS | 6000 | Ngân sách ước lượng gồm system, câu hỏi, nguồn, phần dư template |
| RAG_OUTPUT_TOKENS | 1000 | max_tokens gửi provider |
| RAG_TOP_K | 6 | Số đoạn tối đa trước đóng gói |
| API_PARALLEL | 2 | Số lượt API đồng thời |

Ước lượng đầu vào dùng độ dài UTF-8 byte bảo thủ; không dùng giả định tiếng Việt bằng ký tự/4. Đây không phải tokenizer chính xác cho mọi provider. `usage.prompt_tokens`, `completion_tokens`, `cost` là số thực từ API và hiển thị dưới câu trả lời. Giá trị không có trong phản hồi không được tự suy ra. Chưa tự tải context limit của từng model: khi đổi model cần đặt ngân sách phù hợp.

Local còn giới hạn theo context tiến trình và trần đầu ra của runtime. Ngân sách local = min(ngân sách RAG, context − output − phần dự phòng). Prompt cố định đứng đầu, nguồn và câu hỏi theo sau để thuận lợi cho cache của nhà cung cấp, nhưng chưa bật cache đặc thù hoặc hứa tỷ lệ cache hit.

Không cắt âm thầm câu hỏi quá ngân sách: trả lỗi yêu cầu rút gọn. Nguồn có thể chỉ còn đoạn trích; vẫn dẫn về tài liệu gốc. Không gửi toàn bộ lịch sử. Không tự gọi lại request timeout vì có thể tăng hóa đơn.

Tối ưu tiếp: đánh giá câu trả lời thực trên bộ câu hỏi chuẩn; embeddings/reranker local cho câu diễn đạt khác từ khóa; tokenizer đúng model; cache câu trả lời gắn hash kho/model/prompt; chọn model giá rẻ đã đạt tiêu chí; chỉ dùng API phân loại khi truy xuất cục bộ không rõ.

Tham khảo: [Chat API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request), [prompt caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching), [reasoning tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
''',
'docs/USER_GUIDE.md':'''# Sử dụng

Đăng nhập bằng tài khoản hiện có. Vai trò thành viên dùng chung kho tài liệu; quản trị có thêm Người dùng, Hệ thống và Quản trị tri thức.

Hỏi bằng tiếng Việt, kèm loại thiết bị/dịch vụ và điều cần biết. Mở nguồn ở cạnh câu trả lời để đối chiếu. Nhãn bản nháp kỹ thuật nghĩa cần kỹ sư kiểm tra; trợ lý không tự cam kết giá, SLA hoặc chạy cấu hình. Lịch sử thuộc tài khoản, tiếp tục được sau đăng nhập lại.

Kho tri thức lọc theo nhóm A–F. Quản trị tải tài liệu lý thuyết, đọc rồi duyệt; thu hồi khi không còn đúng. Không đưa dữ liệu khách hàng vào kho chung.

Hệ thống chọn Local GPU/OpenRouter API. API gửi câu hỏi cùng đoạn tài liệu được chọn tới OpenRouter; key/model được quản lý trong .env. Local dùng model trên máy. Khi chuyển sang Local mà model chưa chạy, bấm Khởi động model. Điều khiển GPU bị vô hiệu trong chế độ API.

Token vào/ra và chi phí hiện dưới câu trả lời nếu provider trả usage. “API đã cấu hình” chỉ xác nhận có cấu hình, không có nghĩa đã thử key hoặc số dư. Lỗi API hiện rõ và không tự retry.
''',
'docs/OPERATIONS.md':r'''# Vận hành

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Demo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Restart-App.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Demo.ps1
```

Launcher chỉ khởi động model GPU khi chọn local. Restart chỉ nạp lại backend, giữ model đã chạy. Đổi mode không tự dừng tiến trình GPU đang tồn tại; có thể dừng model trong chế độ local trước khi chuyển API để giải phóng VRAM.

Sửa nguồn chuẩn rồi bấm Đồng bộ kho tri thức. CLI `sync_knowledge.py` tạo bản chuẩn; cần restart để áp dụng vào DB đang chạy. Nút đồng bộ trên web áp dụng ngay.

Sao lưu trong Hệ thống tạo SQLite snapshot và JSON runtime/tri thức, bỏ initial-accounts. Muốn khôi phục đầy đủ cần lưu thêm `data/sources`, NewData và .env ở nơi phù hợp; backup mặc định không đóng gói Word/Excel/nguồn gốc. Không phục hồi backup demo cũ chứa khách hàng vào hệ thống mới.

Logs tại `logs/`, reports tại `artifacts/`. Không đưa key, tài khoản khởi tạo hoặc log câu hỏi nhạy cảm vào Git. Chạy một uvicorn worker. Trước mở LAN cần thiết kế TLS, xác thực và chính sách dữ liệu phù hợp.
''',
'docs/TROUBLESHOOTING.md':'''# Xử lý lỗi

- API 401: kiểm API key trong .env. 402: kiểm số dư. 429: chờ hạn mức nhà cung cấp phục hồi; ứng dụng không tự gọi lại.
- Model không hợp lệ: lấy ID gốc ở catalog OpenRouter, không thêm `openrouter/` trước `nvidia/...`. Key/model không hợp lệ vẫn có thể hiện “API đã cấu hình”, vì health không gọi API có phí.
- Phản hồi rỗng: có thể model chỉ sinh reasoning hoặc hết max_tokens; mặc định API yêu cầu tắt reasoning. Một số provider không hỗ trợ tắt, cần kiểm model hoặc tăng trần phù hợp.
- Không có nguồn: nêu rõ thiết bị/dịch vụ; kiểm tài liệu đã duyệt, còn hiệu lực và đã đồng bộ. Câu hỏi khách hàng không có dữ liệu để trả lời.
- Quá ngân sách: rút gọn câu hỏi hoặc tăng RAG_INPUT_TOKENS vừa đủ trong .env.
- Local không chạy: kiểm GGUF, llama-server, Vulkan và cổng 1234. API mode không cần các file này.
- Đăng nhập cũ: username/mật khẩu được giữ, nhưng vai trò sale/technical đã đổi thành member. File mật khẩu khởi tạo không được cập nhật khi đổi mật khẩu trong web.
- UI test: `check_unified.py` dùng Microsoft Edge. Kiểm `artifacts/unified_smoke.json` và ảnh desktop/mobile. Test không có --live không gọi model thật.
''',
'CONTRIBUTING.md':r'''# Phát triển

Đọc README và docs/ARCHITECTURE.md. Một app, hai provider, một kho lý thuyết. Không thêm lại CRM/finance hoặc ứng dụng internal riêng.

Chạy `.venv-runtime\Scripts\python.exe -X utf8 -m pytest -q`. Test tạo DB và tài khoản biệt lập, mock provider để không gọi API. `evaluate_rag.py` kiểm truy xuất 16 câu hỏi, chưa chấm độ đúng câu trả lời. `check_unified.py --live` gọi model thật theo .env và có thể tính phí.

Không commit .env, DB, tài khoản, NewData hoặc nội dung công ty khi chưa có quyền chia sẻ. Khi đổi adapter nguồn phải giữ provenance, trạng thái review và kiểm loại dữ liệu khách hàng. Khi đổi prompt/provider phải kiểm budget, lỗi mạng, token usage và mã nguồn giả.
''',
'SECURITY.md':'''# Dữ liệu và truy cập

Ứng dụng bind localhost, kiểm Host/Origin, cookie HttpOnly/SameSite, mật khẩu scrypt. Thành viên dùng chung tài liệu; chỉ admin duyệt nguồn, quản lý user và model. Hội thoại kiểm ownership ở backend. Chưa có TLS/SSO/MFA/HA cho phục vụ LAN.

OpenRouter mode gửi câu hỏi và đoạn nguồn ra API. API key đọc từ .env phía server, không trả trong health/admin UI. Không tự retry hoặc chuyển provider khi lỗi. Local mode chỉ gọi localhost.

Kho chỉ chứa lý thuyết và mẫu trống. Không tải dữ liệu khách hàng, secret hoặc thông tin chưa được phép chia sẻ. Mã trích dẫn hợp lệ không bảo đảm câu trả lời đúng ngữ nghĩa; cần đối chiếu nguồn.

Đợt chuyển đổi đã xóa dữ liệu khách hàng trong working tree, DB, backups và chỉ mục cũ. Git history và bản sao ngoài workspace không được rewrite/xóa trong đợt này. Báo sự cố qua kênh riêng của chủ hệ thống, không dán key hoặc hồ sơ nhạy cảm vào issue công khai.
''',
'docs/PUBLIC_RELEASE.md':'''# Phạm vi mã nguồn

Không còn hai phiên bản public/internal. Một codebase chạy local hoặc API theo .env. DataReal, NewData, nguồn dịch vụ công ty, DB, logs, backups và .env là dữ liệu local, không tự xuất bản.

Git history cũ có thể chứa dữ liệu demo đã bị xóa khỏi bản hiện tại. Không coi thao tác xóa working tree là xóa lịch sử Git. Trước chia sẻ source, kiểm nội dung nguồn lý thuyết và giấy phép tài liệu/model; không tự đưa dữ liệu công ty lên remote.
''',
'LUONG_HOAT_DONG.txt':'''Đăng nhập → kho tri thức dùng chung → câu hỏi → ưu tiên nhóm A–F cục bộ → TF-IDF từ/ký tự → chọn đoạn đa dạng → bỏ trùng → đóng gói theo ngân sách → gọi Local hoặc OpenRouter một lần → kiểm mã trích dẫn → trả lời và usage → lưu lịch sử theo tài khoản.

Nguồn chuẩn: data/sources/*.json + NewData/data/processed/company_knowledge.jsonl. Đồng bộ tạo knowledge_documents.json và cập nhật SQLite, xóa nguồn mất, giữ trạng thái thu hồi.

Không có CRM/ticket/công nợ. Không có .local-internal. API key/model trong .env; không đưa key vào trình duyệt. Câu hỏi hồ sơ khách hoặc thiếu nguồn có thể trả lời không gọi API.
'''
}
for name,text in docs.items():Path(name).write_text(text,encoding='utf8')
