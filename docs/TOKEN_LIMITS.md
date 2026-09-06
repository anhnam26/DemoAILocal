# Context, số lượt đồng thời và trần trả lời

## Ba loại giới hạn khác nhau

1. **Model gốc:** Qwen công bố context gốc **262.144 token**. Đây là năng lực kiến trúc, không bảo đảm GPU 8 GB đủ bộ nhớ hoặc độ trễ phù hợp. [Model card chính thức Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B).
2. **Máy được đo:** RTX 4060 Laptop 8 GB, RAM 16 GB, Qwen3.5-9B Q4_K_M, llama.cpp b10816 Vulkan, Q8 KV, 1 slot, offload 33/33 lớp. Kết quả dưới đây đo thật, không suy từ dung lượng file model.
3. **Ứng dụng:** cho chọn 1–4 slot, 2.048–65.536 context/slot, tổng context tối đa 65.536; trần đầu ra mong muốn 256–8.192. Các cận trên là guardrail phần mềm, không bảo đảm mọi tổ hợp phù hợp GPU.

## Kết quả đo một slot

| Context/slot | Nạp model | VRAM toàn máy khi nạp | Kiểm đầu vào gần đầy |
|---:|---|---:|---|
| 8.192 | Thành công, 33/33 lớp GPU | 6.335 MiB | Chỉ thử câu ngắn, chưa kiểm gần đầy |
| 16.384 | Thành công, 33/33 lớp GPU | 6.619 MiB | Chỉ thử câu ngắn, chưa kiểm gần đầy |
| **32.768** | Thành công, 33/33 lớp GPU | 6.792 MiB | **32.512 token đầu vào + 32 đầu ra**, không cắt; khoảng **49,32 giây** |
| 65.536 | Nạp và câu ngắn thành công | 7.425 MiB | Prompt 65.280 token **chưa hoàn tất sau timeout 480 giây**; không xác nhận đạt |

**Mức context cao nhất đã kiểm chứng với prompt gần đầy trong lần đo này là 32.768 token.** Không gọi đây là giới hạn vật lý tuyệt đối: chưa đo hết các mức trung gian và tải hệ thống có thể thay đổi. Không suy ra 262.144 token dùng tốt trên máy này. Mức 65.536 chỉ cho thấy cấp phát/nạp được, chưa cho thấy xử lý gần đầy phù hợp.

Phép đo dùng mảng token đã tokenize, nội dung lặp tổng hợp và tắt context shift, kiểm số token thực model đánh giá. Đây là thử dung lượng/xử lý, **không phải benchmark độ chính xác ngữ nghĩa, tốc độ với mọi tài liệu, trần sinh đầu ra dài hoặc p95 production**. VRAM là toàn máy tại thời điểm lấy mẫu, không phải peak đầy đủ. Đầu vào rất dài có thể vượt timeout 180 giây của API chat ứng dụng.

`benchmark_context.py` có ngưỡng dừng khi RAM khả dụng thấp, dự báo thiếu VRAM hoặc thử thất bại; không cố gây OOM. Nó tạm dừng demo, đo từng mức rồi bật lại cấu hình đã lưu. Báo cáo chi tiết local tại `artifacts/context-benchmark.json`, không đưa log có dữ liệu hoạt động vào bộ public.

## Công thức và ví dụ

```text
Tổng context model = số slot × context mỗi slot
Trần đầu ra hiệu lực mỗi slot = min(trần mong muốn, floor(context mỗi slot / 4))
Tổng trần đầu ra khi cùng chạy = số slot × trần hiệu lực mỗi slot
```

| Slot | Context mỗi slot | Trần mong muốn | Trần hiệu lực/slot | Tổng context |
|---:|---:|---:|---:|---:|
| 2 | 4.096 | 800 | 800 | 8.192 |
| 4 | 4.096 | 2.000 | 1.024 | 16.384 |
| 2 | 8.192 | 8.192 | 2.048 | 16.384 |
| 1 | 32.768 | 8.192 | 8.192 | 32.768 |

Context gồm chỉ dẫn, nguồn, câu hỏi và đầu ra. Đầu ra gồm cả cú pháp JSON, nên lượng chữ hiển thị ít hơn số token sinh. Token không tương đương một từ tiếng Việt. Trần không ép model sinh đủ và không phải lượng đã dùng.

UI hiện giới hạn câu hỏi 1.500 ký tự; RAG lấy tối đa 4 nguồn, mỗi nguồn tối đa khoảng 1.500 ký tự. Tăng context chưa tự biến chat thành công cụ nhập hàng chục nghìn token. Phép thử prompt gần đầy gọi runtime riêng. Prompt hiện yêu cầu câu trả lời ngắn khoảng 300 từ, nên tăng trần không tự yêu cầu bài viết dài.

## Điều chỉnh trên web

Vào **Hệ thống local**, chọn số slot, context/slot và trần mong muốn. Bảng xem trước hiện từng slot; tổng vượt cận phần mềm bị backend từ chối. Bảng đang chạy dùng context/số slot của tiến trình và trần phần mềm có hiệu lực. Mọi slot dùng cùng định mức; không đặt context khác nhau cho từng slot trong phiên bản này.

Lưu cấu hình rồi khởi động lại model để đổi slot/context. Trần đầu ra và temperature áp dụng lượt mới. Nếu đã lưu context lớn nhưng chưa restart, bảng đang chạy và lời gọi model vẫn tính trần theo context đang chạy, tránh hứa sai ngân sách.

Mặc định giữ 2 × 4.096, đầu ra 800. Đã đo hai slot thực xử lý đồng thời, câu thứ ba vào hàng chờ. Tăng số slot chia sẻ GPU, không bảo đảm mỗi câu nhanh hơn. Thông số gợi ý vận hành xuất phát từ phép đo trên máy tham chiếu, cần kiểm lại khi đổi máy/runtime hoặc tải nền.

Đã kiểm tra thêm **4 slot × 4.096**, model `/slots` báo 4 lượt cùng xử lý, backend cũng ghi nhận 4 lượt; bốn câu thử hoàn tất khoảng **26,14 giây**. Cấu hình được lưu/restart qua API quản trị rồi phục hồi 2 slot/4.096/800. Bài thử dùng câu khác và tải nền khác phép đo 2 slot, nên không so trực tiếp hai thời gian để kết luận cấu hình nào nhanh hơn. Báo cáo local: `artifacts/four-slot-report.json`.
