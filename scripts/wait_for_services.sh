#!/bin/sh
set -e

# ==============================================================================
# Script chờ các dịch vụ phụ trợ đạt trạng thái sẵn sàng (Healthcheck Poll)
# ==============================================================================

MAX_ATTEMPTS=30
SLEEP_SECONDS=2

wait_for_tcp() {
    HOST="$1"
    PORT="$2"
    SERVICE_NAME="$3"

    echo ">>> Đang chờ $SERVICE_NAME ($HOST:$PORT)..."
    ATTEMPT=1
    while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
        # Tương thích cả GNU netcat, BusyBox netcat và /dev/tcp
        if (nc -w 1 "$HOST" "$PORT" < /dev/null > /dev/null 2>&1) || (nc -z "$HOST" "$PORT" > /dev/null 2>&1); then
            echo ">>> $SERVICE_NAME đã sẵn sàng!"
            return 0
        fi
        echo ">>> Lần thử $ATTEMPT/$MAX_ATTEMPTS: $SERVICE_NAME chưa phản hồi, chờ ${SLEEP_SECONDS}s..."
        sleep "$SLEEP_SECONDS"
        ATTEMPT=$((ATTEMPT + 1))
    done

    echo ">>> LỖI: Hết thời gian chờ $SERVICE_NAME sau $((MAX_ATTEMPTS * SLEEP_SECONDS)) giây!" >&2
    return 1
}

wait_for_http() {
    URL="$1"
    SERVICE_NAME="$2"

    echo ">>> Đang chờ HTTP endpoint $SERVICE_NAME ($URL)..."
    ATTEMPT=1
    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        if curl -f -s -o /dev/null "$URL"; then
            echo ">>> $SERVICE_NAME đã sẵn sàng (HTTP 200)!"
            return 0
        fi
        echo ">>> Lần thử $ATTEMPT/$MAX_ATTEMPTS: $SERVICE_NAME chưa trả về 200, chờ ${SLEEP_SECONDS}s..."
        sleep $SLEEP_SECONDS
        ATTEMPT=$((ATTEMPT + 1))
    done

    echo ">>> LỖI: Hết thời gian chờ HTTP $SERVICE_NAME sau $((MAX_ATTEMPTS * SLEEP_SECONDS)) giây!" >&2
    return 1
}

case "$1" in
    postgres)
        wait_for_tcp "${POSTGRES_HOST:-localhost}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
        ;;
    minio)
        wait_for_http "${MINIO_ENDPOINT:-http://localhost:9000}/minio/health/live" "MinIO"
        ;;
    gateway)
        wait_for_http "${GATEWAY_URL:-http://localhost:80}/" "NGINX Gateway"
        ;;
    *)
        echo "Cách dùng: $0 [postgres|minio|gateway]"
        exit 1
        ;;
esac
