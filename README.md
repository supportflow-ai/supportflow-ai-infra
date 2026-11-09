# SupportFlow AI — Infrastructure & Gateway Repository (`supportflow-ai-infra`)

Cập nhật 05/11/2026: [runtime Knowledge indexing](docs/infra/knowledge-index-runtime.md) dùng PostgreSQL 16 + pgvector 0.8.1 và embedding CPU offline; xem lưu ý nâng cấp volume Alpine sang Debian trước rollout.

Kho lưu trữ hạ tầng và cổng truy cập trung tâm của hệ thống **SupportFlow AI** (Hệ thống IT Service Desk hỗ trợ xử lý và phân loại phiếu bằng AI).

---

## 1. Vai trò kiến trúc

Theo [ADR-008](https://github.com/supportflow-ai/ai-it-service-desk/blob/main/docs/adr/ADR-008-docker-compose-nginx.md) và [ADR-012](https://github.com/supportflow-ai/ai-it-service-desk/blob/main/docs/adr/ADR-012-ai-contract-and-future-transport.md), kho `supportflow-ai-infra` giữ các trách nhiệm độc quyền:
1. **Dịch vụ phụ trợ Local Dev (`docker-compose.yml`)**: Cung cấp PostgreSQL 16 với pgvector trên Debian, MinIO S3 Object Storage và Mailpit cho lập trình viên chạy local mà không cần cài đặt phần mềm phụ trợ trực tiếp trên máy host.
2. **Cổng NGINX Gateway & Cân bằng tải (`nginx/`)**:
   - Định tuyến `/` tới giao diện người dùng SPA (`ai-it-service-desk-web`).
   - Định tuyến `/api/` tới cụm máy chủ backend (`backend_cluster`: `api-1:8080` và `api-2:8080`).
   - Chặn tuyệt đối mọi truy cập công khai vào `/internal/` và port của `ai-service` (bảo đảm an toàn S2S).
3. **Triển khai toàn hệ thống (`deploy/compose.system.yml`)**: Điều phối khởi động toàn bộ stack gồm Web, 2 API nodes, Worker, AI Service, PostgreSQL, MinIO và NGINX Gateway.
4. **Kiểm thử khói tự động (`scripts/run_smoke_tests.py`, `tests/smoke/`)**: Xác minh tính thông suốt của cổng gateway sau khi triển khai.

> **Ranh giới quan trọng**: Kho này **không** sở hữu mã nguồn ứng dụng và **không** chứa file migration SQL. Toàn quyền sở hữu schema cơ sở dữ liệu thuộc về `ai-it-service-desk` (EF Core).

---

## 2. Cấu trúc thư mục

```text
supportflow-ai-infra/
├── .github/
│   └── workflows/
│       └── ci.yml                   # CI kiểm tra cú pháp Compose và cấu hình NGINX
├── deploy/                          # Môi trường Staging / Production toàn diện
│   ├── .env.example
│   ├── compose.system.yml           # Toàn hệ thống, gồm các tác vụ migration, seed vai trò và init MinIO
│   ├── example.env                  # Bản mẫu cấu hình cho VPS
│   └── README.md                    # Runbook triển khai chi tiết
├── docs/
│   └── infra/
│       ├── local-development.md     # Hướng dẫn chi tiết chạy môi trường dev cục bộ
│       ├── operations-runbook.md    # Sổ tay backup/restore DB, MinIO và troubleshooting
│       └── repository-boundaries.md # Ma trận ranh giới và trách nhiệm giữa 4 repos
├── nginx/
│   ├── conf.d/
│   │   └── default.conf             # Upstream load balance 2 node API, route / và /api
│   └── nginx.conf                   # Cấu hình tối ưu NGINX worker, buffer, gzip, logs
├── scripts/
│   ├── init_minio_buckets.sh        # Tạo bucket MinIO ban đầu
│   ├── run_smoke_tests.py           # Chạy smoke test gateway (Python stdlib)
│   └── wait_for_services.sh         # Chờ dịch vụ phụ trợ sẵn sàng
├── tests/
│   └── smoke/
│       └── gateway_routing_test.py  # Pytest suite cho CI smoke test
├── .env.example                     # Biến môi trường mẫu cho local
├── .gitignore
├── docker-compose.yml               # Chỉ chạy DB, Storage, Mail cho Local Dev
├── example.env                      # Bản mẫu dự phòng không bị deny rule
└── README.md
```

---

## 3. Khởi động nhanh (Quickstart)

### Phát triển Local (Chỉ chạy DB & Storage phụ trợ)
```bash
# 1. Khởi động PostgreSQL 16 và MinIO
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
