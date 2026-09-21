param([string]$Python = "python", [switch]$SkipInstall)
$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot
foreach ($port in @(8012,3012)) {
  if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    throw "Portul $port este deja folosit. Oprește doar instanța de test înainte de repornire."
  }
}
$localDir = Join-Path $projectRoot '.local-data'
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$configPath = Join-Path $localDir 'config.json'
if (!(Test-Path -LiteralPath $configPath)) {
  & $Python -c "import secrets,json,sys,base64; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps({'SECRET_KEY':secrets.token_urlsafe(48),'DATA_ENCRYPTION_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}))" $configPath
  if ($LASTEXITCODE -ne 0) {throw 'Nu s-au putut genera cheile locale.'}
}
$config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
$env:SECRET_KEY=$config.SECRET_KEY
$env:DATA_ENCRYPTION_KEY=$config.DATA_ENCRYPTION_KEY
$env:ENVIRONMENT='development'
$env:LOCAL_DATA_DIR=$localDir
$env:DATABASE_URL='sqlite:///' + (Join-Path $localDir 'medical.db').Replace('\','/')
$env:STORAGE_BACKEND='local'
$env:AI_DEFAULT_PROVIDER='mock'
$env:SMTP_HOST=''
$env:FRONTEND_URL='http://localhost:3012'
$env:BACKEND_CORS_ORIGINS='http://localhost:3012,http://127.0.0.1:3012'
$env:NEXT_PUBLIC_API_URL='http://localhost:8012'
$env:NEXT_PUBLIC_TEST_MODE='true'
if (!$SkipInstall) {
  & $Python -m pip install -r backend/requirements.txt
  if ($LASTEXITCODE -ne 0) {throw 'Instalarea backendului a eșuat.'}
  npm.cmd --prefix frontend ci
  if ($LASTEXITCODE -ne 0) {throw 'Instalarea frontendului a eșuat.'}
}
Push-Location backend
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {throw 'Migrarea a eșuat.'}
Pop-Location
npm.cmd --prefix frontend run build
if ($LASTEXITCODE -ne 0) {throw 'Buildul a eșuat.'}
$apiProcess=Start-Process -FilePath $Python -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8012','--no-access-log' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localDir 'api.log') -RedirectStandardError (Join-Path $localDir 'api-error.log')
$nodeCommand=(Get-Command node).Source
$webProcess=Start-Process -FilePath $nodeCommand -ArgumentList 'node_modules/next/dist/bin/next','start','-p','3012','-H','127.0.0.1' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localDir 'web.log') -RedirectStandardError (Join-Path $localDir 'web-error.log')
@{api=$apiProcess.Id;web=$webProcess.Id} | ConvertTo-Json | Set-Content (Join-Path $localDir 'processes.json')
Write-Output 'Aplicația de test: http://localhost:3012 — folosește doar date fictive.'
Write-Output "Emailurile locale: $localDir/mailbox"
