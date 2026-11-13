# AGENTS.md — Hạ tầng và cổng hệ thống (`supportflow-ai-infra`)

Dành cho mọi người làm việc trong kho này, gồm lập trình viên, người kiểm thử, người vận hành và trợ lý AI. Quy tắc chung của cả dự án (quy trình nhánh, commit, PR, giới hạn an toàn, hoàn thành) nằm ở [cẩm nang chung](docs/team-handbook.md). File này chỉ ghi phần riêng của hạ tầng.

## 0. Đọc trước

**Kho này làm gì.** Ghép bốn kho thành một hệ thống chạy được và kiểm chứng nó chạy cùng nhau: dịch vụ phụ trợ cho lập trình viên (PostgreSQL, MinIO, Mailpit), cổng NGINX duy nhất, Compose cho toàn hệ thống và cho bản phát hành, kiểm thử khói, và **ghim phiên bản phát hành** (`sources.lock.json`).

**Không làm.** Không chứa mã ứng dụng, không chứa migration hay DDL (schema thuộc backend), không sửa nghiệp vụ. Thấy lỗi ở kho khác thì báo kho đó, đừng vá trong Compose.

Tám điều cần nhớ trước khi sửa:

1. **Ghim phiên bản là quyết định phát hành.** `sources.lock.json` chứa SHA của backend, web, ai-service và digest của năm image. Chỉ đổi khi có quyết định phát hành, và đổi cả hai phần cùng nhau.
2. **NGINX là cổng vào duy nhất.** `/` tới web, `/api/` tới `api-1` và `api-2`; chặn tuyệt đối truy cập công khai vào `/internal/` và cổng của ai-service.
3. **Không đưa bí mật vào Git.** `.env` không commit; `example.env` chỉ chứa giá trị mẫu. Không in mật khẩu hay token ra log.
4. **Không xoay credential của storage đã có dữ liệu** bằng cách sửa env; cần quy trình riêng (xem [sổ tay vận hành](docs/infra/operations-runbook.md)).
5. **Không xóa volume hay `down -v`** khi chưa xác nhận đích là môi trường dùng một lần.
6. **Không thao tác VPS, staging, production** khi chưa được yêu cầu rõ lệnh và đích.
7. **Smoke phải dùng đúng SHA** của kho được kiểm chứng; kết quả của SHA cũ không chứng nhận SHA mới.
8. **Kiểm thử phải chạy thật.** Một lệnh kết thúc bằng mã khác 0 vì thiếu shell hay Docker không phải bằng chứng xử lý lỗi đúng.

## 1. Cấu trúc

| Đường dẫn | Nội dung |
| --- | --- |
| `docker-compose.yml` | Dịch vụ phụ trợ local: PostgreSQL (pgvector 0.8.1, PostgreSQL 17), MinIO, Mailpit, `minio-init` |
| `compose.yaml` + `compose.local.yaml` | Stack dùng trong CI smoke, build từ các checkout cạnh nhau (`BACKEND_PATH`, `WEB_PATH`) |
| `deploy/compose.system.yml` | Toàn hệ thống build từ các kho anh em (Web, 2 API, Worker, AI, PostgreSQL, MinIO, NGINX, migration và seed vai trò) |
| `deploy/compose.release.yml` | Staging và production dùng năm image theo digest; `DEPLOY_ENV` tách project, network, volume |
| `sources.lock.json` | SHA nguồn của ba kho và digest của năm image |
| `nginx/`, `deploy/nginx/` | Cấu hình gateway |
| `scripts/` | `init_minio_buckets.sh`, `wait_for_services.sh`, `run_smoke_tests.py`, `assemble_release.py` |
| `tests/unit`, `integration`, `smoke` | Kiểm thử script và Compose; MinIO thật; định tuyến gateway |
| `deploy/smoke/` | Smoke sau triển khai (`smoke-test.sh`, `smoke-test.ps1`) |
| `docs/infra/` | Ranh giới kho, chạy local, vận hành, tiến độ củng cố |
| `docs/project/` | Phạm vi MVP và đối chiếu API, quyền truy cập giữa các kho |
| `docs/release-and-storage.md` | Chuẩn bị phát hành và lưu trữ |

Tài liệu: [README](README.md), [ranh giới các kho](docs/infra/repository-boundaries.md), [chạy local](docs/infra/local-development.md), [sổ tay vận hành](docs/infra/operations-runbook.md), [triển khai](deploy/README.md), [tài liệu chung và phạm vi MVP](docs/project/README.md).

## 2. Lệnh

Chạy từ gốc repo. Cần Docker (có Compose) và Python 3.12; kiểm thử đơn vị còn cần `sh` POSIX (trên Windows đặt `TEST_SH` tới `sh.exe` của Git).

```sh
# Kiểm tra cấu hình Compose (không khởi động gì)
docker compose --env-file example.env -f docker-compose.yml config --quiet
docker compose --env-file deploy/example.env -f deploy/compose.system.yml config --quiet
docker compose --env-file .env.local.example -f compose.yaml -f compose.local.yaml config --quiet

# Kiểm thử
python -m unittest discover -s tests/unit -v          # script init MinIO, manifest phát hành, cấu hình Compose
python -m unittest discover -s tests/integration -v   # MinIO thật, cần Docker engine đang chạy

# Local và toàn hệ thống
cp example.env .env && docker compose up -d                                  # chỉ dịch vụ phụ trợ
cd deploy && cp example.env .env && docker compose -f compose.system.yml up -d --build
python scripts/run_smoke_tests.py --target-url http://localhost              # smoke gateway
python scripts/assemble_release.py --help                                    # ghép manifest phát hành
```

Số kiểm thử thực sự chạy phải lớn hơn 0. Kiểm thử tích hợp tạo project riêng, không publish cổng, dọn đúng project đó; không chạy nó trên Docker engine của máy dùng chung khi chưa biết đích.

CI ([ci.yml](.github/workflows/ci.yml)) chạy trên push và PR vào `main` hoặc `master`: kiểm tra cấu hình Compose và NGINX, kiểm thử MinIO thật, và smoke trên stack dùng một lần theo hai hồ sơ (`locked` dùng SHA trong `sources.lock.json`; `migrator` dùng một SHA backend cố định để kiểm chứng công cụ Migrator). PR vào nhánh khác không được CI này kiểm.

## 3. Quy tắc kỹ thuật

- **Compose dùng chung script khởi tạo MinIO** (`scripts/init_minio_buckets.sh`) mount chỉ đọc; script đòi credential rõ ràng, giới hạn thử lại, không in đầu ra `mc` chứa thông tin xác thực. Image `mc` được ghim theo release chính thức.
- **Đường dẫn Dockerfile của backend** do biến `BACKEND_API_DOCKERFILE`, `BACKEND_WORKER_DOCKERFILE`, `BACKEND_MIGRATOR_DOCKERFILE` quyết định, để build được theo SHA backend có bố cục thư mục cũ. CI tự chọn theo SHA đã ghim. Đổi cấu trúc thư mục backend phải cập nhật Compose, workflow và kiểm thử cùng nhau.
- **Migration chạy trước API và Worker**: `migration` rồi `seed-roles` phải hoàn thành thành công trước khi API và Worker khởi động; kiểm thử CI chứng minh migration lỗi thì chặn cả hai.
- **Phát hành theo digest:** `assemble_release.py` chỉ ghi `release.json` và `images.env` khi đủ năm image, đúng repository, digest SHA-256 và SHA nguồn đầy đủ; ba image backend phải cùng commit.
- **Chuẩn PostgreSQL 17** (chủ dự án chốt 2026-11-13): `docker-compose.yml`, `compose.yaml`, `compose.system.yml` và `compose.release.yml` cùng dùng `pgvector/pgvector:0.8.1-pg17-bookworm` ghim digest; khớp VPS dev dùng chung (17.11) và kiểm thử tích hợp backend. Đổi phiên bản chính tiếp theo cần quyết định riêng và kế hoạch di chuyển dữ liệu; volume PostgreSQL 16 cũ không khởi động được dưới 17.

## 4. Ngôn ngữ và Git

Quy ước đầy đủ ở [cẩm nang chung](docs/team-handbook.md). Điểm riêng:

- Tài liệu mới, mô tả commit và PR bằng tiếng Việt có dấu; giữ nguyên định danh, câu lệnh và cấu hình.
- Tạo nhánh từ `main` và mở PR vào `main` (các PR đã hợp nhất đều đi theo luồng này).
- Commit dạng `<loại>(<phạm vi>): <mô tả tiếng Việt>`. **Mã công việc (Jira hoặc công cụ khác) không bắt buộc**; commit cũ có `[TC-<id>]` giữ nguyên.
- Kiểm tra nhánh, HEAD và thay đổi chưa commit trước khi sửa; chỉ đưa phần thuộc nhiệm vụ vào commit, không dùng `git add -A` khi chưa xác minh. Không tự commit khi chỉ được yêu cầu đánh giá hay lập kế hoạch.
- Chỉ sửa AGENTS.md khi nhiệm vụ yêu cầu. Ngoại lệ: đổi lệnh hoặc cấu hình được ghim thì cập nhật hướng dẫn bị ảnh hưởng trong cùng thay đổi.

## 5. Giới hạn an toàn

- Không đưa bí mật thật vào Git, log hay ảnh chụp: mật khẩu PostgreSQL và MinIO, `JWT_SECRET_KEY`, `AI_S2S_BEARER_TOKEN`. Tệp `.env` nằm ngoài Git.
- Không tự push, hợp nhất PR, phát hành image hay triển khai khi chưa được giao. Không đổi `sources.lock.json` hay digest để "cho smoke chạy" khi chưa có quyết định phát hành.
- Không chạy lệnh làm mất dữ liệu (`down -v`, xóa volume, `reset --hard`, `clean`) trên môi trường dùng chung hay có dữ liệu thật. Backup và restore theo [sổ tay vận hành](docs/infra/operations-runbook.md).
- Không nới NGINX để mở `/internal/` hay cổng ai-service, kể cả "tạm thời".
- Không sửa test hay cấu hình để làm CI xanh; không hạ ghim image để né lỗi.

## 6. Đồng bộ với kho khác

Hạ tầng thường là bên **phải đuổi theo** thay đổi của kho khác:

| Kho khác đổi | Hạ tầng phải làm |
| --- | --- |
| Backend đổi đường dẫn Dockerfile, tên project, lệnh Migrator, biến môi trường, cổng | Cập nhật Compose, `ci.yml`, kiểm thử và tài liệu triển khai |
| Web đổi cổng, `VITE_API_BASE_URL` hay Dockerfile | Cập nhật proxy `/api` và Compose |
| ai-service đổi cổng, health, biến `SUPPORTFLOW_AI_*` | Cập nhật Compose (`SUPPORTFLOW_AI_SERVICE_TOKEN` lấy từ `AI_S2S_BEARER_TOKEN`) và NGINX |
| Quyết định phát hành mới | Cập nhật `sources.lock.json` (SHA và digest), chạy smoke với đúng SHA |
| Phạm vi, quyền hoặc luồng chức năng đổi | Cập nhật [docs/project](docs/project/README.md) kèm mốc đã đối chiếu |

## 7. Kiểm chứng và bàn giao

| Thay đổi | Kiểm tra cần chạy |
| --- | --- |
| Chỉ tài liệu | Đối chiếu liên kết, lệnh và cấu hình với mã hiện tại; không bắt buộc chạy Docker |
| Compose, biến môi trường | Ba lệnh `config --quiet` ở §2 và `tests/unit` |
| Script MinIO, lifecycle storage | `tests/unit` và `tests/integration` (cần Docker) |
| NGINX, định tuyến | Kiểm tra cú pháp NGINX theo CI và `scripts/run_smoke_tests.py` trên stack thật |
| Ghim phiên bản, manifest phát hành | `tests/unit` (manifest) và smoke với đúng SHA |
| Workflow | Kiểm tra cấu trúc và lệnh mới; chạy lại các job chịu ảnh hưởng |

Gắn kết quả với SHA và thay đổi chưa commit nếu có. Bàn giao ngắn: phạm vi, cách sửa, lệnh cùng số test và kết quả, kiểm tra chưa chạy và lý do, giới hạn, nhánh, SHA và trạng thái push hay PR. CI đạt không tự chứng minh đã nghiệm thu đầy đủ; không tuyên bố hoàn thành khi thiếu bằng chứng.
