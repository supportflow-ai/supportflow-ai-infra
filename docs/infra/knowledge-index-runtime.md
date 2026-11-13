# Runtime Knowledge indexing

Cập nhật 05/11/2026, thay đổi local trên nền `77ba2db53c6971adc182a0de60dab607109ed163`, phục vụ TC-348–TC-350. Chưa triển khai production.

Ba Compose (và stack CI smoke) dùng PostgreSQL 17 + pgvector 0.8.1, ghim `pgvector/pgvector:0.8.1-pg17-bookworm@sha256:3e8b3adfd27b5707128f60956f62a793c3c9326ea8cfaf0eab7adccb5d700b21` (chuẩn thống nhất ngày 2026-11-13; trước đó local, system và release dùng PostgreSQL 16). Core sở hữu extension/migration/schema; Infra không tự tạo bảng hoặc chạy migration khi PostgreSQL startup.

System/release bật `KnowledgeIndex__Enabled`, endpoint nội bộ `http://ai-service:8000`, S2S token cùng `AI_S2S_BEARER_TOKEN` và model CPU `local-e5`. Image AI tải model/tokenizer revision cố định lúc build, runtime đọc `/opt/models` offline; không gửi nội dung bài tới provider ngoài. AI không mở port công khai. API/Worker/Database cùng phiên bản Core chứa migration mới và AI cùng contract `knowledge-index/v1`; release manifest classification hiện có không tự chứng minh hai bản Knowledge contract tương thích, cần đối chiếu thêm manifest/profile giữa hai artifact trước rollout.

## Nâng cấp có kiểm soát

1. Xác minh Docker context, database đích và backup phục hồi được theo runbook hiện hành. Không chạy stack hoặc migration vào volume đang dùng chỉ để thử tính năng.
2. Image cũ dùng Alpine, image pgvector mới dùng Debian; khác libc/collation; thêm vào đó PostgreSQL 16 sang 17 là đổi phiên bản chính nên **không dùng lại được thư mục dữ liệu** (cần `pg_upgrade` hoặc dump/restore). Chưa có dữ liệu production, nên chỉ máy lập trình viên có volume cũ phải tạo lại. Với dữ liệu có sẵn, diễn tập dump/restore vào volume mới và kiểm tra collation/index trước cutover. Không mặc định gắn volume Alpine cũ vào Debian, không xóa volume cũ.
3. Kiểm tra extension vector available; dùng Database tool của đúng Core commit để áp migration `AddKnowledgeIndexPipeline` sau khi đích được xác minh. API/Worker không tự migrate/seed.
4. Khởi chạy AI và kiểm tra `/health/embedding`; khởi chạy Core/Worker cùng token. Publish bài giả lập → job Succeeded → chunks/version/dimension=384 theo runbook Core.
5. Kiểm tra re-publish V2 và job cũ không kích hoạt V1; archive loại khỏi active view. Backfill bài Published cũ bằng API rebuild có kiểm soát.

Model chạy CPU có cold start và dùng RAM/đĩa lớn hơn baseline rule; đo tài nguyên và độ trễ với dữ liệu nhóm trước chốt SLA. Concurrency inference mặc định 1/process; khi bận trả 503, Worker retry có giới hạn. Theo dõi job Failed, tuổi job Pending, attempts và `/health/embedding`.

## Kiểm chứng và dừng

```powershell
docker compose --env-file example.env -f docker-compose.yml config --quiet
docker compose --env-file deploy/example.env -f deploy/compose.system.yml config --quiet
python -m unittest discover -s tests/unit -v
```

Trên Windows dùng Python UTF-8 mode (`PYTHONUTF8=1`) và đặt `TEST_SH` tới Git `sh.exe` cho test shell. Test release Compose dùng digest giả trong fixture và chỉ đọc config. Core integration tests dùng pgvector container riêng, AI CI kiểm model thật. Smoke gateway hiện có không thay bằng chứng indexing.

Nếu cần dừng indexing, tắt worker capability, giữ job/snapshot/vector. Không `down -v` hoặc migration Down trên dữ liệu thật. Rollback ứng dụng giữ schema additive; việc bỏ schema indexing cần kế hoạch riêng vì mất lịch sử index, dù ArticleVersion vẫn còn để rebuild.
