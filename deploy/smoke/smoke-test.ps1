param(
    [string]$BaseUrl = $env:SERVICE_DESK_BASE_URL,
    [string]$TestEmail = $env:TEST_USER_EMAIL,
    [string]$TestPassword = $env:TEST_USER_PASSWORD
)
$ErrorActionPreference = 'Stop'
if (-not $BaseUrl) { $BaseUrl = 'http://localhost' }
if (-not $TestEmail) { $TestEmail = 'requester@test.com' }
if (-not $TestPassword) { $TestPassword = 'Test@1234' }
try {
    $health = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 15
    if ($health.status -ne 'Healthy') { throw 'Health check failed' }
    Write-Host '[1/5] Health passed'
    $login = Invoke-RestMethod "$BaseUrl/api/auth/login" -Method Post -ContentType 'application/json' -Body (@{ email = $TestEmail; password = $TestPassword } | ConvertTo-Json) -TimeoutSec 15
    if (-not $login.token) { throw 'Login returned no token' }
    $headers = @{ Authorization = "Bearer $($login.token)" }
    Write-Host '[2/5] Login passed'
    $ticket = Invoke-RestMethod "$BaseUrl/api/tickets" -Method Post -Headers $headers -ContentType 'application/json' -Body (@{ title = 'Smoke test ticket'; description = 'Requester flow verification from smoke test.'; categoryId = 'NET' } | ConvertTo-Json) -TimeoutSec 15
    if (-not $ticket.id -or -not $ticket.ticketNumber -or $ticket.status -ne 1) { throw 'Invalid create response' }
    Write-Host '[3/5] Create ticket passed'
    $page = Invoke-RestMethod "$BaseUrl/api/tickets/me?page=1&pageSize=100" -Headers $headers -TimeoutSec 15
    if ($page.totalCount -lt 1 -or $ticket.id -notin $page.items.id) { throw 'Created ticket missing from list' }
    Write-Host '[4/5] Paged list passed'
    $detail = Invoke-RestMethod "$BaseUrl/api/tickets/$($ticket.id)" -Headers $headers -TimeoutSec 15
    if ($detail.id -ne $ticket.id -or $detail.status -ne 1) { throw 'Invalid detail response' }
    Write-Host '[5/5] Ticket detail passed'
    exit 0
} catch {
    Write-Error $_
    exit 1
}
