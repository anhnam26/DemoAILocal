# So sánh backup và HA

> DỮ LIỆU GIẢ LẬP. Snapshot 2026-09-05. Không phải chính sách thật.

Mã: CMP-BACKUP-HA | Phiên bản: company-demo-2.0 | Vai trò: sale, technical, admin | Khách: Chung

| Tiêu chí | Backup | HA |
| Mục đích | Khôi phục dữ liệu/trạng thái lịch sử | Duy trì dịch vụ khi một thành phần lỗi |
| Ví dụ | Sao lưu máy ảo vào kho tách biệt | Cặp thiết bị active/passive |
| Không giải quyết hết | Không chuyển đổi dịch vụ tức thì nếu chưa thiết kế | Có thể đồng bộ cả dữ liệu bị xóa/lỗi |
| Đo lường | RPO, RTO qua restore test | Thời gian chuyển đổi qua failover test |
| Kết luận | Cần kết hợp HA theo nhu cầu | Cần kết hợp backup và diễn tập |