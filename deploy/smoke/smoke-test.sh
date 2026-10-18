#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SERVICE_DESK_BASE_URL:-http://localhost}"
export TEST_USER_EMAIL="${TEST_USER_EMAIL:-requester@test.com}"
export TEST_USER_PASSWORD="${TEST_USER_PASSWORD:-Test@1234}"

curl --fail --silent --show-error "$BASE_URL/health" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(r.status!=="Healthy") process.exit(1)'
echo '[1/5] Health passed'

LOGIN=$(node -e 'process.stdout.write(JSON.stringify({email:process.env.TEST_USER_EMAIL,password:process.env.TEST_USER_PASSWORD}))')
TOKEN=$(curl --fail --silent --show-error "$BASE_URL/api/auth/login" \
  -H 'Content-Type: application/json' -d "$LOGIN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!r.token) process.exit(1); process.stdout.write(r.token)')
echo '[2/5] Login passed'

TICKET_ID=$(curl --fail --silent --show-error "$BASE_URL/api/tickets" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Smoke test ticket","description":"Requester flow verification from smoke test.","categoryId":"NET"}' |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!r.id||!r.ticketNumber||r.status!==1) process.exit(1); process.stdout.write(r.id)')
export TICKET_ID
echo '[3/5] Create ticket passed'

curl --fail --silent --show-error "$BASE_URL/api/tickets/me?page=1&pageSize=100" \
  -H "Authorization: Bearer $TOKEN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!Array.isArray(r.items)||!r.items.some(t=>t.id===process.env.TICKET_ID)||r.totalCount<1) process.exit(1)'
echo '[4/5] Paged list passed'

curl --fail --silent --show-error "$BASE_URL/api/tickets/$TICKET_ID" \
  -H "Authorization: Bearer $TOKEN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(r.id!==process.env.TICKET_ID||r.status!==1) process.exit(1)'
echo '[5/5] Ticket detail passed'
