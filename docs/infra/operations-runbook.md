# Sổ tay Vận hành Hạ tầng (Operations Runbook)

Tài liệu này cung cấp các quy trình bảo trì, sao lưu, phục hồi và khắc phục sự cố hệ thống SupportFlow AI.

---

## 1. Sao lưu và Phục hồi Cơ sở dữ liệu (PostgreSQL)

### Sao lưu (Backup)
Thực hiện sao lưu snapshot logic dạng custom-format nén:
```bash
docker exec -t supportflow-postgres pg_dump -U servicedesk -d servicedesk -F c -b -v -f /tmp/servicedesk_backup.dump
docker cp supportflow-postgres:/tmp/servicedesk_backup.dump ./servicedesk_$(date +%Y%m%d_%H%M%S).dump
```

### Phục hồi (Restore)
Trước khi phục hồi, đảm bảo dừng các tiến trình ghi (API, Worker):
```bash
# Đưa file dump vào container
docker cp ./servicedesk_backup.dump supportflow-postgres:/tmp/restore.dump

# Phục hồi sạch dữ liệu
docker exec -t supportflow-postgres pg_restore -U servicedesk -d servicedesk --clean --if-exists -v /tmp/restore.dump
```

---

## 2. Quản lý Lưu trữ Tệp đính kèm (MinIO)

### Kiểm tra dung lượng và bucket
Truy cập qua MinIO Client CLI:
```bash
docker exec -it supportflow-minio mc alias set local http://localhost:9000 minioadmin minioadmin_secret_change_me
docker exec -it supportflow-minio mc ls local/servicedesk-attachments
```

### Chính sách dọn dẹp / TTL
Nếu cần cấu hình xóa tệp tạm cũ hơn 30 ngày:
```bash
docker exec -it supportflow-minio mc ilm add --expiry-days 30 local/servicedesk-attachments/temp/
```

---

## 3. Cấu hình SSL / HTTPS cho NGINX Gateway

Trong môi trường Production thực tế có domain công khai:
1. Trỏ bản ghi DNS `A` của tên miền về IP của VPS.
2. Dùng Certbot cấu hình Let's Encrypt:
   ```bash
   apt-get install -y certbot python3-certbot-nginx
   certbot certonly --standalone -d supportflow.example.com
   ```
3. Mount chứng chỉ vào container NGINX Gateway (`/etc/letsencrypt/live/...`) và mở port 443 trong `compose.system.yml`.

---

## 4. Xử lý Sự cố Thường gặp (Troubleshooting)

### Sự cố 1: NGINX trả về `502 Bad Gateway`
- **Nguyên nhân**: Cụm backend (`api-1` hoặc `api-2`) chưa hoàn thành khởi động hoặc crash do sai cấu hình kết nối DB/JWT.
- **Kiểm tra**:
  ```bash
  docker compose -f deploy/compose.system.yml logs api-1 api-2
  ```
- **Xử lý**: Xác minh migration DB đã hoàn tất (`supportflow-system-migration`), chuỗi kết nối PostgreSQL và biến `JWT_SECRET_KEY` đủ 32 ký tự.

### Sự cố 2: Lỗi cổng trùng lặp `address already in use: 0.0.0.0:5432`
- **Nguyên nhân**: Máy chủ host đã có PostgreSQL cục bộ đang chạy.
- **Xử lý**: Đổi `POSTGRES_PORT=15432` trong file `.env` của `supportflow-ai-infra`. Cập nhật cổng kết nối trong cấu hình của backend tương ứng.

### Sự cố 3: AI Service phản hồi `401 Unauthorized` hoặc `400 Bad Request`
- **Nguyên nhân**:
  - `401`: Token S2S Bearer giữa API backend và `ai-service` không khớp.
  - `400`: Thuật toán băm `ai-input-v2` phía caller không khớp với hash SHA-256 phía AI Service.
- **Kiểm tra**: So sánh biến `AI_S2S_BEARER_TOKEN` ở cả 2 service và kiểm tra log chi tiết của `ai-service`.
