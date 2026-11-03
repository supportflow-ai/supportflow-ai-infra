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
APP_KEY="${MINIO_APP_ACCESS_KEY:-}"
APP_SECRET="${MINIO_APP_SECRET_KEY:-}"
case "$BUCKET_NAME" in
    ''|*[!a-z0-9.-]*) echo 'Invalid MINIO_DEFAULT_BUCKET' >&2; exit 1 ;;
esac
if [ -n "$APP_KEY" ] || [ -n "$APP_SECRET" ]; then
    if [ -z "$APP_KEY" ] || [ "${#APP_SECRET}" -lt 8 ]; then
        echo 'Provide both application storage credentials (secret at least 8 characters).' >&2
        exit 1
    fi
fi

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

if [ -n "$APP_KEY" ]; then
    umask 077
    POLICY_FILE="$(mktemp)"
    trap 'rm -f "$POLICY_FILE"' EXIT HUP INT TERM
    cat > "$POLICY_FILE" <<EOF
{"Version":"2012-10-17","Statement":[
{"Effect":"Allow","Action":["s3:GetBucketLocation","s3:ListBucket"],"Resource":["arn:aws:s3:::$BUCKET_NAME"]},
{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["arn:aws:s3:::$BUCKET_NAME/uploads/pending/*","arn:aws:s3:::$BUCKET_NAME/tickets/*"]}
]}
EOF
    if ! "$MC_BINARY" admin user add local "$APP_KEY" "$APP_SECRET" > /dev/null 2>&1 ||
       ! "$MC_BINARY" admin policy create local "$BUCKET_NAME-app" "$POLICY_FILE" > /dev/null 2>&1 ||
       ! "$MC_BINARY" admin policy attach local "$BUCKET_NAME-app" --user "$APP_KEY" > /dev/null 2>&1; then
        echo 'Application storage credentials/policy initialization failed.' >&2
        exit 1
    fi
fi

# This file is the desired lifecycle configuration for the dedicated attachment bucket.
# Import replaces its lifecycle rules; do not point this initializer at a shared bucket.
if [ -n "${MINIO_LIFECYCLE_FILE:-}" ]; then
    if ! "$MC_BINARY" ilm import "local/$BUCKET_NAME" < "$MINIO_LIFECYCLE_FILE" > /dev/null 2>&1; then
        echo 'Pending-upload lifecycle initialization failed.' >&2
        exit 1
    fi
fi

echo ">>> Cấu hình bucket hoàn tất thành công!"
exit 0
