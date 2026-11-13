# SupportFlow AI — Infrastructure & Gateway Repository (`supportflow-ai-infra`)

Cập nhật 05/11/2026: [runtime Knowledge indexing](docs/infra/knowledge-index-runtime.md) dùng PostgreSQL 17 + pgvector 0.8.1 (chuẩn của dự án từ 2026-11-13, trước đó là 16) và embedding CPU offline; xem lưu ý nâng cấp volume (Alpine sang Debian, PostgreSQL 16 sang 17) trước rollout.

Kho lưu trữ hạ tầng và cổng truy cập trung tâm của hệ thống **SupportFlow AI** (Hệ thống IT Service Desk hỗ trợ xử lý và phân loại phiếu bằng AI).

---

## 1. Vai trò kiến trúc

Theo [ADR-008](https://github.com/supportflow-ai/ai-it-service-desk/blob/main/docs/adr/ADR-008-docker-compose-nginx.md) và [ADR-012](https://github.com/supportflow-ai/ai-it-service-desk/blob/main/docs/adr/ADR-012-ai-contract-and-future-transport.md), kho `supportflow-ai-infra` giữ các trách nhiệm độc quyền:
1. **Dịch vụ phụ trợ Local Dev (`docker-compose.yml`)**: Cung cấp PostgreSQL 17 với pgvector trên Debian, MinIO S3 Object Storage và Mailpit cho lập trình viên chạy local mà không cần cài đặt phần mềm phụ trợ trực tiếp trên máy host.
2. **Cổng NGINX Gateway & Cân bằng tải (`nginx/`)**:
   - Định tuyến `/` tới giao diện người dùng SPA (`ai-it-service-desk-web`).
   - Định tuyến `/api/` tới cụm máy chủ backend (`backend_cluster`: `api-1:8080` và `api-2:8080`).
   - Chặn tuyệt đối mọi truy cập công khai vào `/internal/` và port của `ai-service` (bảo đảm an toàn S2S).
3. **Triển khai toàn hệ thống (`deploy/compose.system.yml`)**: Điều phối khởi động toàn bộ stack gồm Web, 2 API nodes, Worker, AI Service, PostgreSQL, MinIO và NGINX Gateway.
4. **Kiểm thử khói tự động (`scripts/run_smoke_tests.py`, `tests/smoke/`)**: Xác minh tính thông suốt của cổng gateway sau khi triển khai.
5. **Bản phát hành (`deploy/compose.release.yml`, `sources.lock.json`)**: Staging và production chạy năm image theo digest; `sources.lock.json` ghim SHA nguồn của ba kho. Nâng phiên bản là quyết định phát hành.

> **Ranh giới quan trọng**: Kho này **không** sở hữu mã nguồn ứng dụng và **không** chứa file migration SQL. Toàn quyền sở hữu schema cơ sở dữ liệu thuộc về `ai-it-service-desk` (EF Core).

---

## 2. Cấu trúc thư mục

```text
supportflow-ai-infra/
├── .github/workflows/ci.yml         # CI: kiểm tra Compose và NGINX, MinIO thật, smoke trên stack dùng một lần
├── deploy/
│   ├── compose.system.yml           # Toàn hệ thống build từ các kho anh em, gồm migration, seed vai trò, init MinIO
│   ├── compose.release.yml          # Staging/production dùng năm image theo digest
│   ├── example.env                  # Bản mẫu cấu hình cho VPS
│   ├── minio/Dockerfile             # Build MinIO từ bản phát hành bảo mật của upstream
│   ├── nginx/nginx.conf             # Cấu hình gateway cho stack CI (compose.yaml)
│   ├── smoke/                       # Smoke sau triển khai (smoke-test.sh, smoke-test.ps1)
│   └── README.md                    # Runbook triển khai chi tiết
├── docs/
│   ├── project/                     # Tài liệu chung: phạm vi MVP, đối chiếu API và quyền, mốc nguồn
│   ├── infra/                       # Ranh giới kho, chạy local, vận hành, runtime Knowledge, tiến độ củng cố
│   ├── release-and-storage.md       # Chuẩn bị bản phát hành và lưu trữ
│   └── team-handbook.md             # Cẩm nang làm việc chung (bản giống hệt ở bốn kho)
├── nginx/                           # Cấu hình gateway cho compose.system.yml và compose.release.yml
│   ├── conf.d/default.conf          # Upstream load balance 2 node API, route / và /api
│   └── nginx.conf
├── scripts/
│   ├── assemble_release.py          # Ghép manifest phát hành từ năm tệp bằng chứng image
│   ├── init_minio_buckets.sh        # Tạo bucket MinIO ban đầu
│   ├── run_smoke_tests.py           # Smoke test gateway (Python stdlib)
│   └── wait_for_services.sh         # Chờ dịch vụ phụ trợ sẵn sàng
├── storage/pending-upload-lifecycle.json
├── tests/
│   ├── unit/                        # Script init MinIO, manifest phát hành, cấu hình Compose
│   ├── integration/                 # MinIO thật
│   └── smoke/                       # Định tuyến gateway
├── AGENTS.md                        # Quy tắc riêng của kho (cho người và trợ lý AI)
├── compose.yaml, compose.local.yaml # Stack dùng trong CI smoke, build từ các checkout cạnh nhau
├── docker-compose.yml               # Dịch vụ phụ trợ local: PostgreSQL, MinIO, Mailpit
├── sources.lock.json                # SHA nguồn ba kho và digest năm image phát hành
├── example.env, .env.example, .env.local.example
└── README.md
```

---

## 3. Khởi động nhanh (Quickstart)

### Phát triển Local (Chỉ chạy DB & Storage phụ trợ)
```bash
# 1. Khởi động PostgreSQL 17 và MinIO
cp example.env .env
docker compose up -d

# 2. Xem trạng thái dịch vụ
docker compose ps
```
Lúc này bạn có thể khởi động `ai-it-service-desk` (port 5000), `ai-service` (port 8000), và `ai-it-service-desk-web` (port 5173) trực tiếp trên máy tính.

---

### Chạy thử nghiệm Full System (Tất cả container sau NGINX Gateway)
```bash
cd deploy
cp example.env .env
# Điền mật khẩu an toàn và JWT_SECRET_KEY trong .env
docker compose -f compose.system.yml up -d --build

# Chạy kiểm thử khói gateway
python ../scripts/run_smoke_tests.py --target-url http://localhost
```

---

## 4. Tài liệu chi tiết

- [Tài liệu chung SupportFlow AI](docs/project/README.md) — kiến trúc bốn kho, phạm vi MVP và đối chiếu API, quyền truy cập.

Kiểm tra cấu hình và khởi tạo MinIO từ gốc repo:

```bash
docker compose --env-file example.env -f docker-compose.yml config --quiet
docker compose --env-file deploy/example.env -f deploy/compose.system.yml config --quiet
python -m unittest discover -s tests/unit -v
```

Nhóm unit dùng Python standard library, POSIX `sh` và Docker Compose CLI (không cần engine).
Trên Windows có thể đặt `TEST_SH` tới Git `sh.exe`; shell phải chạy được trong môi trường hiện tại.
Nhóm này chạy script thật với `mc` giả để kiểm tra lỗi xác thực/tạo bucket, giới hạn thử lại và che credentials.
Nếu shell không chạy được, kiểm thử báo lỗi môi trường thay vì coi exit code khác 0 là bằng chứng xử lý lỗi đúng.

Khi Docker engine sẵn sàng, chạy kiểm thử MinIO thật:

```bash
python -m unittest discover -s tests/integration -v
```

Kiểm thử tạo project UUID riêng, không publish port, dùng tmpfs cho dữ liệu MinIO và dọn đúng project đó.
Nó xác minh bucket tùy chỉnh tồn tại, init lặp lại thành công và service phụ thuộc bị chặn khi sai credentials.
CI có job riêng chạy nhóm này; đây chưa phải smoke toàn hệ thống/API.

Hai Compose dùng chung `scripts/init_minio_buckets.sh`, mount read-only và truyền credentials rõ ràng.
Script yêu cầu credentials; default cho local được khai báo ở Compose. Không sửa env để xoay credentials của storage đã có dữ liệu mà chưa thực hiện quy trình tương ứng.
Image `mc` được ghim theo [release chính thức 2024-10-08](https://github.com/minio/mc/releases/tag/RELEASE.2024-10-08T09-37-26Z).
Giá trị cũ `RELEASE.2024-10-14T17-57-55Z` không có tag/release tương ứng trong repo `minio/mc` tại lúc kiểm tra.
CI integration sẽ kiểm tra việc pull/chạy image; xác minh release GitHub không thay thế kiểm thử container.

- [Ranh giới các Repository](docs/infra/repository-boundaries.md)
- [Hướng dẫn Phát triển Cục bộ](docs/infra/local-development.md)
- [Sổ tay Vận hành & Khắc phục Sự cố](docs/infra/operations-runbook.md)
- [Hướng dẫn Triển khai Staging/Production](deploy/README.md)
- [Cẩm nang làm việc chung](docs/team-handbook.md) (nhánh, commit, PR, giới hạn an toàn) và [AGENTS.md](AGENTS.md) (quy tắc riêng của kho)
