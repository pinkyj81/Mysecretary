# 📋 AI 일정 비서 - 설정 가이드 (Google Gemini 무료판)

## 🚀 빠른 시작

### 1. 패키지 설치
```bash
cd MySecretary
pip install -r requirements.txt
```

### 2. Google Gemini API 키 발급 (완전 무료! 🎉)
1. https://aistudio.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. API 키 복사 (AIza로 시작)

**💡 참고:** Gemini API는 무료 할당량이 매우 많습니다!
- 월 1,500회 요청 무료
- 신용카드 등록 불필요

### 3. 환경 변수 설정
`.env` 파일을 열어서 API 키를 입력하세요:

```env
# Google Gemini API 키 (무료!)
GEMINI_API_KEY=AIza-your-actual-api-key-here
```

### 4. 서버 실행
```bash
python app.py
```

### 5. 챗봇 접속
브라우저에서 http://localhost:5000/chatbot 접속

## 💬 사용 예시

### 일정 추가
- "내일 오후 3시에 팀 회의 추가해줘"
- "2월 20일 오전 10시에 병원 예약 잡아줘"
- "모레 저녁 7시에 저녁 약속 추가"

### 일정 조회
- "오늘 일정 있어?"
- "이번 주 일정 보여줘"
- "다음 주 월요일 일정 알려줘"

### 일정 삭제/수정
- "ID 5번 일정 삭제해줘"
- "내일 회의 시간을 오후 4시로 변경해줘"

## 🔧 문제 해결

### "GEMINI_API_KEY를 찾을 수 없습니다" 오류
1. `.env` 파일이 `MySecretary` 폴더에 있는지 확인
2. `GEMINI_API_KEY=` 뒤에 실제 API 키가 입력되었는지 확인
3. API 키가 `AIza`로 시작하는지 확인

### "모듈을 찾을 수 없습니다" 오류
```bash
pip install -r requirements.txt
```

### 데이터베이스 연결 오류
[db_config.py](db_config.py)에서 데이터베이스 설정을 확인하세요.

## 📱 기능

✅ 자연어로 일정 추가
✅ 대화형 일정 조회
✅ 일정 수정/삭제
✅ 날짜 자동 인식 (오늘, 내일, 이번 주 등)
✅ 모바일 반응형 디자인
✅ **완전 무료!** (Google Gemini 1.5 Flash)

## 🎯 주요 URL

- 챗봇: http://localhost:5000/chatbot
- 데스크톱 캘린더: http://localhost:5000/desktop
- 모바일 뷰: http://localhost:5000/mobile

## 🆚 OpenAI에서 Gemini로 전환한 이유

- 💰 **완전 무료** (OpenAI는 유료)
- 🚀 **빠른 응답 속도**
- 📊 **넉넉한 무료 할당량**
- 🎯 **Function Calling 지원**

---
즐거운 일정 관리 되세요! 🎉
