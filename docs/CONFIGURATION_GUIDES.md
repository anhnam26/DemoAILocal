# Hướng dẫn cấu hình chi tiết

## Chính sách trả lời

Câu cấu hình tổng thể trả lời trước, hỏi model/firmware/topology ở cuối để tinh
chỉnh. Hướng dẫn phân biệt mục bắt buộc và tùy chọn; có đầu vào, bước thực hiện,
kiểm thử và rollback. Không tự tạo lệnh phụ thuộc phiên bản chưa có nguồn.
`accepted` cho phép sử dụng hướng dẫn, không xác minh thiết bị/dữ kiện khách hàng.
Ô khảo sát chưa điền không phủ nhận kiến thức kỹ thuật trong cùng nguồn.

Retrieval vẫn chỉ dùng tài liệu caller được phép truy cập. Bộ nhận diện cục bộ
cho firewall/FortiGate, switch, VLAN, VPN, DNS/DHCP; câu rộng chọn nguồn theo
marker tiêu đề đa hạng mục, câu hẹp tăng điểm tính năng. Không lấy migration,
BOM/SOW để lấp hướng dẫn cấu hình; không kéo hãng khác vào câu chung. Marker
coverage là chẩn đoán, không chứng nhận đủ ngữ nghĩa hay citation entailment.
Phiếu khảo sát có guidance vẫn dùng được, nhưng ưu tiên hướng dẫn kỹ thuật.

## Ngân sách

| Loại | UTF-8 bytes input | Tokens output | Nguồn tối đa |
|---|---:|---:|---:|
| Khái niệm | tối đa 32000 | tối đa 4000 | 6 |
| Chuyên môn/cấu hình/SOW/BOM | configured cap (default 192000) | configured cap (default 16000) | configured cap (default 48) |

Mặc định code mới ngày 2026-10-09; `.env` cũ không tự cập nhật. Chi tiết file,
URL, reasoning và migration tại [CHAT_CAPABILITIES.md](CHAT_CAPABILITIES.md).
Catalog bên dưới là snapshot lịch sử, không giới hạn live đã nghiệm thu.

Tất cả chịu trần RAG_INPUT_BYTES/RAG_OUTPUT_TOKENS/RAG_TOP_K. Input là byte
proxy, không token chính xác; usage provider mới là số thực. Không tăng quota,
đổi model hoặc quyền. Public catalog OpenRouter đã kiểm read-only 2026-10-05:

| Model | Context top provider | Max completion top provider |
|---|---:|---:|
| nvidia/nemotron-3-super-120b-a12b:free | 262144 | 235929 |
| openai/gpt-6-luna-pro | 1050000 | 128000 |
| qwen/qwen3.5-9b | 256000 | 32768 |
| deepseek/deepseek-v4.1-flash | 1048576 | 943718 |

Nguồn `https://openrouter.ai/api/v1/models`, không gửi key/chat và không gọi
generation. Đây là catalog snapshot, không đảm bảo availability/rate limit hoặc
endpoint runtime. 64000 byte proxy + 8000 output + margin nằm dưới các context
trên; không có benchmark model thật. Local .env ghi limits theo snapshot này.
Admin có thể đặt RAG_MODEL_LIMITS JSON theo ID model chính xác, ví dụ:

```text
RAG_MODEL_LIMITS={"test/model":{"context_tokens":32768,"output_tokens":4096}}
```

Đây là ví dụ, không phải giới hạn của model thật. Code clamp output và giảm
byte proxy input theo context trừ output trừ 1024 margin. Không đảm bảo tokenizer
remote; cấu hình sai fail trước call. Model không có entry ghi limits_configured
false, không suy diễn từ tên/slot. Plugin web remote vẫn có overhead riêng.

Quota reserve toàn ngân sách trước mỗi call, không tự rút output hoặc retry.
240s deadline tổng provider (sau queue <=180s) và 180s timeout mỗi call được giữ;
chưa có benchmark tốc độ/output thật, 8000 tokens có thể không hoàn thành trước
deadline. `finish_reason=length` hiển thị thông báo và truncated=true; người dùng
gửi “Tiếp tục hướng dẫn ở trên” để tiếp tục, tính quota riêng. Lịch sử giữ nguyên
cặp question/answer, tối đa nửa budget cho follow-up; nếu quá lớn sẽ báo không
giữ được ngữ cảnh, không âm thầm gọi thêm.

## Web và nghiệm thu

Thiếu marker bao phủ câu tổng thể có thể kích hoạt lookup bounded; truy vấn
auto chỉ dùng topic/identifier công khai, không đưa nguyên chat/source/private
IP/secret. URL an toàn không đồng nghĩa nguồn chính thức; prompt ưu tiên hãng,
trích đúng ID trả về, chưa có xác minh entailment tự động. Tối đa một lookup,
hai completion trong deadline cũ, không auto-continuation.

Offline tests chứng minh routing/packing/budget/isolation/accounting/citation ID,
không chứng minh chất lượng model thật. Đánh giá có phí cần ngân sách riêng và
kỹ sư chấm độ chi tiết, relevance, nguồn/lệnh đúng phiên bản, latency/chi phí.