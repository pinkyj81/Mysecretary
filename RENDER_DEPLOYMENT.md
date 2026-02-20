# 나의 비서 (MySecretary) - Render 배포 가이드

## 프로젝트 구조
- **데스크톱**: 월별 캘린더 뷰
- **모바일**: 일정 리스트 뷰
- **데이터베이스**: MSSQL (외부 연결)

## Render 배포 단계

### 1️⃣ 로컬 준비

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성 (.env.example 참고)
cp .env.example .env
# 실제 DB 정보로 수정
```

### 2️⃣ GitHub 업로드

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/MySecretary.git
git push -u origin main
```

### 3️⃣ Render 배포

1. [Render](https://render.com) 접속
2. 대시보드 → "New +" → "Web Service"
3. GitHub 연동
4. Repository 선택: `MySecretary`
5. 배포 설정:
   - **Name**: `mysecretary`
   - **Environment**: `Python 3`
   - **Build Command**: `bash build.sh`
   - **Start Command**: `gunicorn app:app`
   - **Region**: 선택 (예: Singapore)

6. **Environment Variables** 설정:
   ```
   DB_SERVER = ms0501.gabiadb.com
   DB_NAME = yujincast
   DB_USER = yujin
   DB_PASSWORD = your_secure_password
   DB_DRIVER = ODBC Driver 18 for SQL Server
   FLASK_ENV = production
   ```

7. "Create Web Service" 클릭

### 4️⃣ 배포 후 확인

- 배포 완료 후 URL: `https://mysecretary.onrender.com`
- 접속 확인:
  - 데스크톱: `https://mysecretary.onrender.com/desktop`
  - 모바일: `https://mysecretary.onrender.com/mobile`

## 주의사항

⚠️ **보안**:
- `.env` 파일은 절대 GitHub에 커밋하지 마세요
- `.gitignore`에 이미 포함되어 있습니다
- DB 비밀번호는 Render 환경 변수로만 관리하세요

⚠️ **ODBC 드라이버**:
- Render 서버는 Linux 기반이므로, ODBC Driver 18 설치 필요
- 배포 후 드라이버 설치 오류 발생 시 연락주세요

## 로컬 테스트

```bash
# 로컬에서 실행
python app.py

# 접속
- 브라우저: http://localhost:5000/desktop
```

## 자동 배포

GitHub main 브랜치에 푸시하면 Render가 자동으로 배포합니다.

```bash
git add .
git commit -m "Update features"
git push origin main
# 자동으로 Render에 배포됨
```

## 문제 해결

### ODBC 드라이버 오류
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```
→ 이 경우 Render의 환경 설정에서 `ODBCINSTINI`, `ODBCSYSINI` 환경 변수 추가 필요

### 데이터베이스 연결 불가
- Render IP를 MSSQL 서버 방화벽에 허용 추가
- DB 자격증명 확인

---

**최종 URL**: `https://mysecretary.onrender.com`
