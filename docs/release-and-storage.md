# Chuẩn bị bản phát hành và storage

Trạng thái 03/11/2026: đã chuẩn bị code, chưa chạy stack thật, chưa phát hành image hoặc tác động VPS.

## Ba cách chạy

| Tệp | Mục đích |
| --- | --- |
| `docker-compose.yml` | Dịch vụ phụ thuộc local |
| `deploy/compose.system.yml` | Build toàn hệ thống từ các repo anh em |
| `deploy/compose.release.yml` | Stack độc lập cho staging/production, dùng năm image ứng dụng theo digest |

Release stack dùng `DEPLOY_ENV` để tách tên project, network và volume của staging với production. Thay đổi này không tự nhập dữ liệu từ volume cũ. Các cổng gateway phải được cấu hình riêng nếu chạy đồng thời trên cùng máy. Database/storage không có cổng công khai trong release stack.

## Tạo manifest

CI Backend/Web/AI có job GHCR chạy khi người vận hành dispatch với `publish_images=true`, sau quality gates. Tải năm tệp bằng chứng từ artifact CI: `servicedesk-api.json`, `servicedesk-worker.json`, `servicedesk-database.json`, `servicedesk-web.json`, `ai-service.json`.

Gọi `python scripts/assemble_release.py --help` để xem các đối số. Truyền năm `--artifact`, `--release-id`, ID `--migration` có thật của image Database, đường dẫn contract AI v1 bằng `--contract`, và thư mục `--output`.

Công cụ chỉ ghi `release.json` và `images.env` sau khi đủ năm image, đúng repository, digest SHA-256 và SHA nguồn đầy đủ. Ba image backend phải cùng commit. Manifest lưu hash byte của contract và mốc migration; công cụ không chứng minh database hiện tại đã tương thích mốc đó. Không dùng digest giả, tag `latest` hoặc kết quả build local để làm bằng chứng phát hành.

Kiểm tra cấu hình, chưa triển khai:

```powershell
docker compose --env-file deploy/.env --env-file releases/RELEASE_ID/images.env -f deploy/compose.release.yml config --quiet
```

`deploy/.env` phải có `DEPLOY_ENV=staging` hoặc `production`, bí mật riêng và các origin thực tế. Trước khi chạy migration/deploy phải xác minh đích, backup/restore và tương thích schema theo runbook backend. Chưa có lệnh tự triển khai production, tự rollback database hoặc tự restore trong công cụ này.

## Storage

- `MINIO_ROOT_*` chỉ cấp cho server/init. API/Worker dùng `MINIO_APP_ACCESS_KEY` và `MINIO_APP_SECRET_KEY`; init gắn policy giới hạn bucket và các prefix pending/ticket.
- `MINIO_PUBLIC_ENDPOINT` là origin trình duyệt truy cập được. Gateway storage chuyển nguyên `Host`, bao gồm cổng, để giữ chữ ký.
- `PUBLIC_WEB_ORIGIN` giới hạn CORS. Khi đưa lên Internet, cần HTTPS cho cả web và storage, qua TLS proxy được cấu hình riêng. Listener HTTP hiện có chưa phải cấu hình HTTPS hoàn chỉnh.
- Lifecycle import là cấu hình mong muốn cho **bucket attachment chuyên dụng** và thay toàn bộ lifecycle của bucket đó. Không trỏ initializer tới bucket dùng chung có quy tắc khác.
- Pending object hết hạn sau một ngày. Yêu cầu upload backend hết hạn sau một giờ. Object cuối mồ côi do lỗi copy/commit cần đối soát metadata trước khi xóa; chưa có tác vụ dọn tự động.

Chưa nghiệm thu pull image MinIO server/client, policy tài khoản ứng dụng và lifecycle trên MinIO thật do Docker engine chưa hoạt động. Các test shell, MinIO và smoke trong CI phải đạt trước phát hành.

## Phần vận hành còn thiếu

Chưa có nghiệm thu HTTPS, backup/restore, migration nâng cấp trên dữ liệu mẫu, full-stack smoke nghiệp vụ, cảnh báo, tài khoản database ứng dụng riêng và diễn tập rollback. Manifest/Compose đạt kiểm tra tĩnh không đồng nghĩa mốc triển khai đã hoàn tất.
