# ODBC Driver 18 자동 설치 가이드

## 🚀 자동 설치 방법 (1단계)

### 1️⃣ 스크립트 위치 확인
```
c:\Users\yujin\OneDrive\문서\pythonTest\MySecretary\install_odbc_driver.ps1
```

### 2️⃣ PowerShell을 **관리자 권한**으로 실행

#### Windows 11/10:
1. 시작 버튼 → "PowerShell" 검색
2. **Windows PowerShell** 우클릭
3. **관리자로 실행** 클릭

#### 또는 Win+X 단축키:
- Win+X → A (PowerShell 관리자 선택)

### 3️⃣ 스크립트 실행 권한 설정

PowerShell 창에 다음을 입력:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### 4️⃣ 설치 스크립트 실행

```powershell
& 'c:\Users\yujin\OneDrive\문서\pythonTest\MySecretary\install_odbc_driver.ps1'
```

또는 폴더로 이동 후:
```powershell
cd 'c:\Users\yujin\OneDrive\문서\pythonTest\MySecretary'
.\install_odbc_driver.ps1
```

### 5️⃣ 설치 완료 대기

스크립트가 자동으로:
- ✅ ODBC Driver 18 다운로드 (약 30초)
- ✅ 설치 진행 (약 2~3분)
- ✅ 설치 확인
- ✅ 임시 파일 정리

---

## ✅ 설치 확인

### PowerShell에서:
```powershell
Get-OdbcDriver | Where-Object { $_.Name -like "*ODBC*" }
```

또는:
```powershell
odbcad32.exe
```
→ ODBC Data Source Administrator 열기 → "드라이버" 탭에서 확인

---

## 🎮 앱 실행

설치 완료 후:

```powershell
cd 'c:\Users\yujin\OneDrive\문서\pythonTest\MySecretary'
python app.py
```

또는:
```powershell
cd 'c:\Users\yujin\OneDrive\문서\pythonTest\MySecretary'
flask run
```

### 웹 접속:
- **데스크톱**: http://localhost:5000/desktop
- **모바일**: http://localhost:5000/mobile

---

## ⚠️ 문제 해결

### 오류 1: "관리자 권한이 필요합니다"
**해결**: PowerShell을 **관리자로 실행**하고 다시 시도

### 오류 2: "스크립트를 실행할 수 없습니다"
**해결**: 다음 명령어 실행 후 다시 시도:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### 오류 3: 설치 여전히 실패
**해결**: 수동 설치
1. Microsoft 공식 페이지에서 다운로드:
   https://learn.microsoft.com/ko-kr/sql/connect/odbc/download-odbc-driver-for-sql-server
2. **msodbcsql.msi** (x64) 다운로드 및 실행
3. 기본 설정으로 설치

---

## 🔄 컴퓨터 재부팅 권장

설치 후 최상의 결과를 위해 컴퓨터를 **재부팅**하는 것을 권장합니다:
```powershell
Restart-Computer
```

---

**🎉 모두 완료되면 앱이 정상 작동합니다!**
