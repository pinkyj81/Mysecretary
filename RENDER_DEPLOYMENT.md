# MySecretary Render 배포 가이드 (최종 안정 버전)

## 핵심 원칙
- 배포 환경은 반드시 Docker 사용
- MSSQL 연결은 ODBC/pyodbc 대신 pymssql 사용
- 스키마 점검 실패는 요청 전체 실패로 이어지지 않도록 처리

## 현재 기준 기술 스택
- Python 3.11
- Flask + SQLAlchemy
- Gunicorn
- pymssql

## 배포 전 확인
1. requirements.txt에 pymssql 포함
2. db_config.py 연결 문자열이 mssql+pymssql 형식
3. Dockerfile에서 freetds-dev 설치
4. app.py의 before_request 스키마 체크가 예외를 삼키고 로그만 남김

## Render 설정
- Environment: Docker
- Branch: main
- Root Directory: MySecretary (필요 시)
- Region: Singapore 권장

## Render 환경 변수
- DB_SERVER=ms1901.gabiadb.com
- DB_NAME=yujincast
- DB_USER=(실제 계정)
- DB_PASSWORD=(실제 비밀번호)
- FLASK_ENV=production

## 배포 순서
1. git add .
2. git commit -m "Deploy: render stable config"
3. git push origin main
4. Render에서 자동/수동 재배포

## 배포 후 점검
- https://mysecretary.onrender.com 접속 확인
- /desktop, /mobile 페이지 확인
- Render Logs에서 traceback 유무 확인

## 장애 대응 빠른 체크
1. 500 에러 + 서비스는 live인 경우
   - 앱 런타임 예외임
   - Render Logs에서 최신 traceback 확인
2. DB 연결 오류
   - 환경 변수 값 오타 확인
   - DB 방화벽에 Render IP 허용 확인
3. 한글 깨짐
   - DB 컬럼/연결 인코딩(정렬/콜레이션) 점검

## 재사용 메모
다음 프로젝트도 동일하게 Docker + pymssql 조합으로 시작하면
ODBC 드라이버 관련 배포 오류를 대부분 피할 수 있습니다.
