# Hướng dẫn Môi trường Phát triển Cục bộ (Local Development Guide)

Tài liệu này hướng dẫn thiết lập môi trường phát triển cục bộ cho lập trình viên trên hệ thống SupportFlow AI. Quy trình làm việc chung của dự án ở [cẩm nang](../team-handbook.md).

---

## 1. Cấu trúc thư mục chuẩn trên máy phát triển

Khuyến nghị đặt 4 repository ngang hàng trong cùng một thư mục làm việc:
```text
Workspace/
├── ai-it-service-desk/       # Backend .NET C#
├── ai-it-service-desk-web/   # Frontend React 19
├── ai-service/               # AI Inference Python 3.12
└── supportflow-ai-infra/      # Docker Compose & Infra gateway
```

---

## 2. Các bước khởi động môi trường

### Bước 1: Khởi động dịch vụ phụ trợ (Infra)
Dịch vụ hạ tầng (PostgreSQL 16, MinIO, Mailpit) chạy qua Docker Compose:

```bash
cd supportflow-ai-infra
cp example.env .env
docker compose up -d
```

Kiểm tra trạng thái sẵn sàng:
- PostgreSQL 16: `127.0.0.1:5432` (User: `servicedesk`, Pass: `servicedesk_dev_secret_change_me`, DB: `servicedesk`)
- MinIO API: `127.0.0.1:9000` (Console UI: `http://localhost:9001`)
- Mailpit UI: `http://localhost:8025`

### Bước 2: Chạy Database Migration và Backend (.NET)
Mở terminal riêng tại thư mục `ai-it-service-desk`:

```bash
cd ../ai-it-service-desk

# Restore và build
dotnet restore src/backend/ServiceDesk.sln --locked-mode
dotnet build src/backend/ServiceDesk.sln -c Release --no-restore

# Chạy migration schema
python scripts/run_backend.py --no-build database migrate

# Khởi động Backend API
python scripts/run_backend.py --no-build api
```
Backend API sẽ lắng nghe tại `http://localhost:5000`.

### Bước 3 (tùy chọn): Khởi động Dịch vụ AI (Python)
Mở terminal riêng tại thư mục `ai-service`:

```bash
cd ../ai-service

# Tạo venv, cài đặt theo README của ai-service rồi chạy dev server
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements-runtime.lock -e ".[dev]"
cp .env.example .env             # đặt SUPPORTFLOW_AI_SERVICE_TOKEN riêng, không commit
uvicorn supportflow_ai.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```
AI Service sẵn sàng nhận yêu cầu S2S tại `http://localhost:8000`.

### Bước 4: Khởi động Giao diện Web (React)
Mở terminal riêng tại thư mục `ai-it-service-desk-web`:

```bash
cd ../ai-it-service-desk-web

npm ci
npm run dev
```
Frontend Vite sẵn sàng tại `http://localhost:5173`.
Proxy trong `vite.config.ts` sẽ chuyển các cuộc gọi `/api` về `http://localhost:5000`.

---

## 3. Dừng và dọn dẹp môi trường

Khi kết thúc phiên làm việc:
```bash
cd supportflow-ai-infra
docker compose down
```
*Lưu ý: Dữ liệu PostgreSQL và MinIO được lưu trữ trên Docker Named Volumes (`supportflow-postgres-data`, `supportflow-minio-data`). Để xóa trắng dữ liệu kiểm thử:*
```bash
docker compose down -v
```
