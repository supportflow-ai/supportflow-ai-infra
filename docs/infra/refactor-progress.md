# Tiến độ củng cố hạ tầng

Ngày: 30/10/2026. Phạm vi đợt đầu: baseline P0 và sửa khởi tạo MinIO thuộc P1. Chưa nghiệm thu M1.

## Mốc code

| Repo | Baseline trước sửa |
| --- | --- |
| Backend | `codex/backend-clean-architecture@61c0225816939bbc66e57c3bef7135404c3bd1ef`, sạch |
| Frontend | `main@7d768d8cf09a9bb9c2fae71e97f218d730cbb645`, có diff local từ trước; không sửa trong đợt này |
| AI | Nhánh main chưa có commit; code untracked từ trước; không sửa trong đợt này |
| Infra | Nhánh main chưa có commit; code untracked từ trước; chỉ sửa các file liệt kê dưới đây |

Các mốc này chưa tạo bộ phiên bản phát hành tái tạo được. Không commit/push hoặc thay lịch sử Git trong đợt này.

## Đã sửa

- `docker-compose.yml`, `deploy/compose.system.yml`: truyền credentials/bucket vào minio-init; mount script dùng chung read-only; giữ điều kiện hoàn tất thành công trước API/Worker.
- `scripts/init_minio_buckets.sh`: yêu cầu credentials, giới hạn thử lại, trả lỗi xác thực/tạo bucket; không in đầu ra mc chứa thông tin xác thực.
- `minio/mc`: ghim `RELEASE.2024-10-08T09-37-26Z`, có release/tag chính thức. Tag cũ không có trong repo mc tại lúc kiểm tra; chưa xác minh pull image local.
- `.gitattributes`: shell script dùng LF để chạy trong container Linux.
- `tests/unit/test_minio_init.py`: hồi quy credentials tùy chỉnh, lỗi, init lặp, retry và kiểm tra Compose đã nội suy; shell không chạy được phải báo lỗi điều kiện kiểm thử.
- `tests/integration/`: stack MinIO dùng tmpfs, không host port, tên project UUID riêng; kiểm tra bucket thật, init lặp và dependency bị chặn khi sai credentials.
- `.github/workflows/ci.yml`: bổ sung các nhóm test trên và dùng config --quiet với env-file tường minh. Workflow mới chưa chạy trên GitHub.
- `README.md`, `deploy/README.md`: cập nhật lệnh kiểm chứng và thứ tự startup thực tế.

## Kết quả kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| Backend locked restore và Release build tại SHA trên | Đạt; 0 warning/0 error |
| ArchitectureTests sau build | Hủy: vstest không kết nối được testhost sau 20 giây; 0 test hoàn tất. Lượt trước cũng bị timeout ở 90 giây |
| Unit cấu hình Compose | 1 test đạt, kiểm tra cả hai Compose với credentials/bucket tùy chỉnh |
| Unit chạy script shell thật với mc giả | Bị chặn trước test: Git sh không khởi chạy được, MSYS NtCreateDirectoryObject trả Access Denied. Không tính các ca lỗi là đạt |
| Compose local/system và stack MinIO test | Cấu hình hợp lệ qua CLI; không chứng minh runtime |
| Python test files | Parse AST hợp lệ |
| MinIO thật/gateway/container smoke | Chưa chạy: Docker engine trả permission denied tại context desktop-linux |

Không sửa Docker/WSL/BIOS, không chạy migration/seed, không khởi động stack hoặc xóa volume dữ liệu. Các test tích hợp mới chỉ cấu hình cho môi trường test dùng một lần.

## Việc tiếp theo

1. Chạy unit shell và MinIO integration ở runner Linux có Docker; ghi kết quả đúng phiên bản code, không coi cấu hình CI là bằng chứng đã đạt.
2. Hoàn tất P0 bằng runner chạy được testhost và ghi phiên bản có thể truy vết cho AI/infra cùng diff frontend.
3. Tiếp tục proxy trust và kiểm tra cấu hình P1 trên topology mạng đã xác định; không mở trust toàn mạng để xử lý nhanh.
4. Thực hiện P2 Compose/image/release manifest sau khi lỗi startup đã kiểm chứng; giữ mapping volume hiện hữu khi chuyển cấu hình.

Nguồn phiên bản mc: https://github.com/minio/mc/releases/tag/RELEASE.2024-10-08T09-37-26Z
