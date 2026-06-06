param(
    [string]$Python = "..\.venv312\Scripts\python.exe",
    [int]$Port = 8000,
    [switch]$UseSqlite,
    [string]$RemoteEnvFile = ".env.remote-dev"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backendDir = Join-Path $repoRoot "backend"

if (-not (Test-Path (Join-Path $backendDir $Python))) {
    throw "Python executable not found from backend/: $Python"
}

$env:DEBUG = "False"
$env:AI_ENABLED = "false"
$env:AI_SEARCH_ENABLED = "false"

if (-not $UseSqlite) {
    $remoteEnvPath = Join-Path $backendDir $RemoteEnvFile
    if (Test-Path $remoteEnvPath) {
        Get-Content $remoteEnvPath | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
                return
            }
            $parts = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim("'").Trim('"'), "Process")
        }
    }

    if (-not $env:DATABASE_URL) {
        throw "DATABASE_URL is required. Create backend/$RemoteEnvFile with the remote-tunnel PostgreSQL URL."
    }
    if (-not $env:S3_SECRET_KEY) {
        throw "S3_SECRET_KEY is required. Create backend/$RemoteEnvFile or set it in the current shell."
    }

    $env:STORAGE_BACKEND = "s3"
    if (-not $env:S3_ENDPOINT) { $env:S3_ENDPOINT = "http://127.0.0.1:19000" }
    if (-not $env:S3_BUCKET) { $env:S3_BUCKET = "buctmedia" }
    if (-not $env:S3_ACCESS_KEY) { $env:S3_ACCESS_KEY = "admin" }
    if (-not $env:S3_REGION) { $env:S3_REGION = "us-east-1" }
    if (-not $env:S3_USE_SSL) { $env:S3_USE_SSL = "false" }
    Write-Host "Using remote server PostgreSQL/S3 via local SSH tunnels."
    Write-Host "Required tunnels: 15432->5432, 19000->9000, 19530->19530."
}
else {
    Write-Host "Using local SQLite backend. This is not production-parity."
}

Push-Location $backendDir
try {
    & $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
