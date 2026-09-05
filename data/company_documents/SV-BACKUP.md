# Thiết kế sao lưu NAS và phục hồi

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: SV-BACKUP | Phiên bản: demo-1.0 | Vai trò: sale, technical, admin | Khách: Chung

DỮ LIỆU DEMO GIẢ LẬP — KHÔNG PHẢI CHÍNH SÁCH THẬT CYBERANT.
Dịch vụ backup demo gồm đánh giá dữ liệu, thiết kế lịch sao lưu, phân quyền kho backup, bản sao tách biệt và diễn tập khôi phục. Hỏi dung lượng, tăng trưởng, hệ thống nguồn, dữ liệu ưu tiên, thời gian có thể mất RPO và thời gian cần khôi phục RTO. RAID không thay thế backup. Snapshot trên cùng thiết bị không đủ thay cho bản sao tách biệt. Không hứa khôi phục được nếu chưa thử restore. Đầu ra gồm chính sách backup, biên bản restore test và runbook vận hành.