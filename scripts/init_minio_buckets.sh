#!/bin/sh
set -eu

# ==============================================================================
# Script khởi tạo MinIO Bucket cho SupportFlow AI
# ==============================================================================

ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
ACCESS_KEY="${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}"
SECRET_KEY="${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}"
BUCKET_NAME="${MINIO_DEFAULT_BUCKET:-servicedesk-attachments}"
MC_BINARY="${MINIO_MC_BINARY:-/usr/bin/mc}"

MAX_ATTEMPTS="${MINIO_INIT_MAX_ATTEMPTS:-30}"
RETRY_DELAY="${MINIO_INIT_RETRY_DELAY_SECONDS:-2}"
case "$MAX_ATTEMPTS" in
    ''|*[!0-9]*|0) echo 'Invalid MINIO_INIT_MAX_ATTEMPTS' >&2; exit 1 ;;
esac
case "$RETRY_DELAY" in
    ''|*[!0-9]*) echo 'Invalid MINIO_INIT_RETRY_DELAY_SECONDS' >&2; exit 1 ;;
esac
ATTEMPT=1

echo '>>> Đang kết nối tới MinIO...'
while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
    if "$MC_BINARY" alias set local "$ENDPOINT" "$ACCESS_KEY" "$SECRET_KEY" > /dev/null 2>&1; then
        echo ">>> Kết nối MinIO thành công!"
        break
    fi
    if [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; then
        echo ">>> Lần thử $ATTEMPT/$MAX_ATTEMPTS: MinIO chưa sẵn sàng, thử lại..."
        sleep "$RETRY_DELAY"
    fi
    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$ATTEMPT" -gt "$MAX_ATTEMPTS" ]; then
    echo ">>> LỖI: Không thể kết nối tới MinIO sau $MAX_ATTEMPTS lần thử." >&2
    exit 1
fi

echo ">>> Khởi tạo bucket '$BUCKET_NAME' nếu chưa tồn tại..."
if ! "$MC_BINARY" mb --ignore-existing "local/$BUCKET_NAME" > /dev/null 2>&1; then
    echo '>>> LỖI: Không thể khởi tạo bucket MinIO.' >&2
    exit 1
fi

echo ">>> Cấu hình bucket hoàn tất thành công!"
exit 0
