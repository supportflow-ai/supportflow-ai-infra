#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SERVICE_DESK_BASE_URL:-http://localhost}"
export TEST_USER_EMAIL="${TEST_USER_EMAIL:-requester@test.com}"
export TEST_USER_PASSWORD="${TEST_USER_PASSWORD:-Test@1234}"

curl --fail --silent --show-error "$BASE_URL/health" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(r.status!=="Healthy") process.exit(1)'
echo '[1/9] Health passed'

LOGIN=$(node -e 'process.stdout.write(JSON.stringify({email:process.env.TEST_USER_EMAIL,password:process.env.TEST_USER_PASSWORD}))')
TOKEN=$(curl --fail --silent --show-error "$BASE_URL/api/auth/login" \
  -H 'Content-Type: application/json' -d "$LOGIN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!r.token) process.exit(1); process.stdout.write(r.token)')
echo '[2/9] Login passed'

TICKET_ID=$(curl --fail --silent --show-error "$BASE_URL/api/tickets" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Smoke test ticket","description":"Requester flow verification from smoke test.","categoryId":"NET"}' |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!r.id||!r.ticketNumber||r.status!==1) process.exit(1); process.stdout.write(r.id)')
export TICKET_ID
echo '[3/9] Create ticket passed'

curl --fail --silent --show-error "$BASE_URL/api/tickets/me?page=1&pageSize=100" \
  -H "Authorization: Bearer $TOKEN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!Array.isArray(r.items)||!r.items.some(t=>t.id===process.env.TICKET_ID)||r.totalCount<1) process.exit(1)'
echo '[4/9] Paged list passed'

curl --fail --silent --show-error "$BASE_URL/api/tickets/$TICKET_ID" \
  -H "Authorization: Bearer $TOKEN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(r.id!==process.env.TICKET_ID||r.status!==1) process.exit(1)'
echo '[5/9] Ticket detail passed'

COMMENT_PAYLOAD=$(node -e 'process.stdout.write(JSON.stringify({content:"Smoke test timeline comment verification."}))')
curl --fail --silent --show-error "$BASE_URL/api/tickets/$TICKET_ID/comments" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d "$COMMENT_PAYLOAD"
echo '[6/9] Add comment passed'

curl --fail --silent --show-error "$BASE_URL/api/tickets/$TICKET_ID/timeline" \
  -H "Authorization: Bearer $TOKEN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!Array.isArray(r)||r.length<1) process.exit(1)'
echo '[7/9] Ticket timeline passed'

ATTACHMENT_PAYLOAD=$(node -e 'process.stdout.write(JSON.stringify({fileName:"smoke-log.txt",fileSizeBytes:1024,contentType:"text/plain"}))')
curl --fail --silent --show-error "$BASE_URL/api/tickets/$TICKET_ID/attachments/upload-url" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d "$ATTACHMENT_PAYLOAD" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!r.uploadUrl||!r.storageKey) process.exit(1)'
echo '[8/9] Presigned upload URL passed'

AGENT_LOGIN=$(node -e 'process.stdout.write(JSON.stringify({email:"agent@test.com",password:"Test@1234"}))')
AGENT_TOKEN=$(curl --fail --silent --show-error "$BASE_URL/api/auth/login" \
  -H 'Content-Type: application/json' -d "$AGENT_LOGIN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!r.token) process.exit(1); process.stdout.write(r.token)')

curl --fail --silent --show-error "$BASE_URL/api/tickets/queue?page=1&pageSize=10" \
  -H "Authorization: Bearer $AGENT_TOKEN" |
  node -e 'const r=JSON.parse(require("fs").readFileSync(0)); if(!Array.isArray(r.items)) process.exit(1)'
echo '[9/9] Agent queue passed'
