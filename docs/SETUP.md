# Cài đặt

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
