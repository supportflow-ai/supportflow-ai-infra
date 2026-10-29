# Hướng dẫn triển khai hệ thống toàn diện (System Deployment Runbook)

Tài liệu này hướng dẫn triển khai toàn bộ hệ thống SupportFlow AI (Web, 2 Node API Backend, Worker, AI Service, PostgreSQL 16, MinIO, NGINX Gateway) sử dụng Docker Compose trên môi trường Staging/Production VPS.

---

## 1. Yêu cầu hệ thống
- Hệ điều hành: Linux (Ubuntu 22.04 LTS hoặc tương đương)
- Docker Engine >= 24.0.0
- Docker Compose v2 >= 2.20.0
- RAM tối thiểu: 4GB (Khuyến nghị 8GB khi chạy cả AI Service và build image .NET)
- Port 80 (và 443 nếu cấu hình SSL ngoài) không bị chiếm dụng.

---

## 2. Quy trình triển khai

### Bước 1: Chuẩn bị biến môi trường
Sao chép file mẫu và cấu hình các giá trị bí mật:
```bash
cd deploy
cp example.env .env
chmod 600 .env
```
*Lưu ý quan trọng:*
- `JWT_SECRET_KEY`: Bắt buộc chuỗi UTF-8 ngẫu nhiên từ 32 ký tự trở lên.
- `POSTGRES_PASSWORD` và `MINIO_ROOT_PASSWORD`: Mật khẩu bảo mật mạnh.
- `AI_S2S_BEARER_TOKEN`: Khóa bí mật dùng cho giao tiếp S2S giữa API/Worker và AI Service.

### Bước 2: Kiểm tra cú pháp Compose
```bash
docker compose --env-file .env -f compose.system.yml config --quiet
```

### Bước 3: Build và khởi động toàn bộ cụm dịch vụ
```bash
docker compose -f compose.system.yml up -d --build
```

Thứ tự khởi động tự động:
1. `postgres` và `minio` khởi động và đạt trạng thái `healthy`.
2. `migration` chạy EF Core database migration rồi tự thoát (`exit 0`).
3. `minio-init` nhận credentials/bucket qua environment và chạy script dùng chung. Lỗi xác thực hoặc tạo bucket trả exit code khác 0; không được bỏ qua lỗi này.
4. `api-1`, `api-2`, `worker` chỉ khởi động sau khi migration và minio-init hoàn tất thành công. `ai-service` khởi động độc lập; backend hiện vẫn dùng NoOp adapter.
5. `web` build Vite app và phục vụ qua Nginx container.
6. `gateway` (NGINX reverse proxy & load balancer) khởi động, cân bằng tải 2 node API và phục vụ Web tại cổng 80.

---

## 3. Kiểm tra trạng thái và nhật ký (Logs)

Kiểm tra trạng thái các container:
```bash
docker compose -f compose.system.yml ps
```

Xem log thời gian thực:
```bash
docker compose -f compose.system.yml logs -f gateway api-1 api-2 ai-service
```

---

## 4. Kiểm thử sau triển khai (Post-Deploy Smoke Test)

Chạy script kiểm thử gateway và cân bằng tải:
```bash
python ../scripts/run_smoke_tests.py --target-url http://localhost
```

Tiêu chí đạt:
- `GET /` trả về mã `200 OK` (SPA Web HTML).
- `GET /health/ready` trả về `200 OK` qua nhóm máy chủ backend.
- `GET /internal/**` trả về `403 Forbidden` (Đảm bảo endpoint nội bộ và AI không bị lộ ra ngoài Internet).
