# verify-postgres-rls.ps1 — PowerShell runner for PostgreSQL RLS integration tests
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " SentinelHealth: PostgreSQL Row-Level Security Verification " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Connecting as 'sentinel_app' (NOBYPASSRLS) with direct SQL queries."
Write-Host ""

$exitCode = 1

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "[*] Executing docker compose test stack (PostGIS + Migrations + RLS Suite)..." -ForegroundColor Yellow
    docker compose -f compose.test.yaml down -v --remove-orphans 2>$null
    docker compose -f compose.test.yaml build
    docker compose -f compose.test.yaml up --abort-on-container-exit --exit-code-from test-runner
    $exitCode = $LASTEXITCODE
    docker compose -f compose.test.yaml down -v
} elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "[*] Docker not found; executing against WSL PostgreSQL / PostGIS test environment..." -ForegroundColor Yellow
    # Ensure postgresql service is active in WSL
    wsl -d kali-linux -u root -e bash -c "pg_ctlcluster 18 main start 2>/dev/null || true"
    wsl -d kali-linux -u root -e bash -c "cd /mnt/c/Users/geete/Hack2skills/sentinelhealth/backend && POSTGRES_PORT=5433 python3 -m pytest tests/postgres/ -v -ra"
    $exitCode = $LASTEXITCODE
} elseif (Get-Command pytest -ErrorAction SilentlyContinue) {
    Write-Host "[*] Running pytest directly on host..." -ForegroundColor Yellow
    $env:PYTHONPATH = "$projectDir\backend"
    Set-Location "$projectDir\backend"
    pytest tests/postgres/ -v -ra
    $exitCode = $LASTEXITCODE
} else {
    Write-Host "[-] Error: Neither Docker, WSL with PostgreSQL, nor pytest is available." -ForegroundColor Red
    exit 1
}

if ($exitCode -eq 0) {
    Write-Host "`n[+] SUCCESS: All mandatory PostgreSQL RLS tests executed and passed without skips." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[-] FAILURE: PostgreSQL RLS verification failed or tests were skipped." -ForegroundColor Red
    exit $exitCode
}
