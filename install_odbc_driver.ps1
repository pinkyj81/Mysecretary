# ODBC Driver 18 for SQL Server 자동 설치 스크립트
# 관리자 권한으로 실행 필요!

# 관리자 권한 확인
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ 관리자 권한이 필요합니다!" -ForegroundColor Red
    Write-Host "이 파일을 우클릭 → '관리자로 실행'을 선택해주세요."
    exit 1
}

Write-Host "🔌 ODBC Driver 18 for SQL Server 설치 시작..." -ForegroundColor Cyan
Write-Host ""

# 1. 기존 설치 확인
Write-Host "1️⃣  기존 ODBC 드라이버 확인 중..." -ForegroundColor Yellow
$OdbcDrivers = Get-OdbcDriver -ErrorAction SilentlyContinue

if ($OdbcDrivers | Where-Object { $_.Name -like "*ODBC Driver 18*" }) {
    Write-Host "✅ ODBC Driver 18이 이미 설치되어 있습니다!" -ForegroundColor Green
    exit 0
}

Write-Host "❌ ODBC Driver 18을 찾을 수 없습니다. 설치를 진행합니다." -ForegroundColor Yellow
Write-Host ""

# 2. 다운로드 경로 설정
$TempDir = "$env:TEMP\ODBC_Installation"
if (-not (Test-Path $TempDir)) {
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    Write-Host "📁 임시 폴더 생성: $TempDir"
}

# 3. 다운로드 URL (Windows x64)
$DownloadUrl = "https://go.microsoft.com/fwlink/?linkid=2249004"
$InstallerPath = Join-Path $TempDir "msodbcsql.msi"

Write-Host "2️⃣  ODBC Driver 18 다운로드 중... (약 30초~1분 소요)" -ForegroundColor Yellow

try {
    # HTTPS 보안 설정
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    
    # 다운로드
    $WebClient = New-Object System.Net.WebClient
    $WebClient.DownloadFile($DownloadUrl, $InstallerPath)
    
    Write-Host "✅ 다운로드 완료: $InstallerPath" -ForegroundColor Green
} catch {
    Write-Host "❌ 다운로드 실패: $_" -ForegroundColor Red
    exit 1
}

# 4. 설치
Write-Host ""
Write-Host "3️⃣  ODBC Driver 18 설치 중... (약 2~3분 소요)" -ForegroundColor Yellow

try {
    # MSI 설치
    $InstallProcess = Start-Process -FilePath msiexec.exe `
        -ArgumentList "/i `"$InstallerPath`" /quiet /norestart" `
        -NoNewWindow `
        -Wait `
        -PassThru
    
    if ($InstallProcess.ExitCode -eq 0) {
        Write-Host "✅ ODBC Driver 18 설치 완료!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  설치가 완료되었지만 코드: $($InstallProcess.ExitCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ 설치 실패: $_" -ForegroundColor Red
    exit 1
}

# 5. 설치 확인
Write-Host ""
Write-Host "4️⃣  설치 확인 중..." -ForegroundColor Yellow

Start-Sleep -Seconds 2

$OdbcDriversAfter = Get-OdbcDriver -ErrorAction SilentlyContinue
if ($OdbcDriversAfter | Where-Object { $_.Name -like "*ODBC Driver 18*" }) {
    Write-Host "✅ ODBC Driver 18 설치 확인 완료!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 모든 설치가 완료되었습니다!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📌 다음 단계:" -ForegroundColor White
    Write-Host "   1. PowerShell을 재시작합니다"
    Write-Host "   2. MySecretary 폴더로 이동: cd c:\Users\yujin\OneDrive\문서\pythonTest\MySecretary"
    Write-Host "   3. 앱 실행: python app.py"
    Write-Host ""
    Write-Host "💻 웹 브라우저에서 http://localhost:5000/desktop 으로 접속하세요!" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  ODBC Driver 18 설치 결과를 확인할 수 없습니다." -ForegroundColor Yellow
    Write-Host "💡 컴퓨터를 재부팅 후 다시 확인해주세요."
}

# 6. 정리
Write-Host ""
Write-Host "5️⃣  임시 파일 정리 중..." -ForegroundColor Yellow

try {
    if (Test-Path $InstallerPath) {
        Remove-Item $InstallerPath -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✅ 정리 완료" -ForegroundColor Green
} catch {
    Write-Host "⚠️  정리 중 오류: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✨ 설치 스크립트 종료" -ForegroundColor Cyan
