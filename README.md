# DART 공시 텔레그램 알림 봇 📊

금융감독원 전자공시시스템(DART)에서 보유 종목의 새로운 공시를 실시간으로 모니터링하고 텔레그램으로 알림을 보내주는 봇입니다.

## 주요 기능

- 📢 **실시간 공시 알림**: 보유 종목의 새로운 공시를 자동으로 감지
- ⏰ **스케줄링**: 설정한 주기마다 자동으로 공시 확인
- 🕐 **운영 시간 설정**: 평일/주말, 시간대별 운영 설정 가능
- 📱 **텔레그램 전송**: HTML 포맷의 깔끔한 메시지로 알림
- 🔄 **중복 방지**: 이미 전송한 공시는 다시 전송하지 않음
- 🏢 **자동 회사 코드 매핑**: DART API에서 전체 상장사 정보 자동 다운로드

## 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd dart_portfolio_disclosure_bot
```

### 2. 가상환경 생성 (권장)
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

## 설정 방법

### 1. 환경 변수 설정

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
# DART API 키 (https://opendart.fss.or.kr/ 에서 발급)
DART_API_KEY=your_dart_api_key_here

# 텔레그램 봇 토큰 (BotFather에서 발급)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# 텔레그램 채널 ID (예: @your_channel 또는 -1001234567890)
TELEGRAM_CHANNEL_ID=your_telegram_channel_id_here
```

#### DART API 키 발급 방법
1. [DART 오픈API](https://opendart.fss.or.kr/) 접속
2. 회원가입 후 로그인
3. 인증키 신청 → API 인증키 발급

#### 텔레그램 봇 생성 방법
1. 텔레그램에서 [@BotFather](https://t.me/botfather) 검색
2. `/newbot` 명령어로 새 봇 생성
3. 봇 이름과 username 설정
4. 발급받은 토큰을 `.env`에 저장

#### 텔레그램 채널 ID 확인 방법
1. 공개 채널: `@channel_username` 형식
2. 비공개 채널/그룹:
   - [@userinfobot](https://t.me/userinfobot)을 채널에 추가
   - 채널 ID 확인 (예: -1001234567890)
   - 봇을 채널 관리자로 추가해야 메시지 전송 가능

### 2. 포트폴리오 설정

`config.json` 파일에서 모니터링할 종목과 스케줄을 설정하세요:

```json
{
  "portfolio": {
    "stocks": [
      "삼성전자",
      "SK하이닉스",
      "NAVER"
    ]
  },
  "schedule": {
    "check_interval_minutes": 5,
    "start_hour": 7,
    "end_hour": 19,
    "weekdays_only": true
  }
}
```

#### 설정 옵션 설명
- `stocks`: 모니터링할 회사명 목록 (정확한 회사명 입력)
- `check_interval_minutes`: 공시 확인 주기 (분 단위)
- `start_hour`: 운영 시작 시간 (24시간 형식)
- `end_hour`: 운영 종료 시간 (24시간 형식)
- `weekdays_only`: 평일만 운영할지 여부 (true/false)

## 실행 방법

### 일반 실행
```bash
python main.py
```

### 백그라운드 실행 (Linux/Mac)
```bash
nohup python main.py > bot.log 2>&1 &
```

### 종료
```
Ctrl + C
```

## 실행 화면 예시

```
============================================================
🚀 DART 공시 텔레그램 알림 봇 시작
============================================================
📊 모니터링 종목: 삼양식품, SK하이닉스, 더존비즈온, 서진시스템
⏰ 확인 주기: 5분마다
🕐 운영 시간: 평일 7:00 - 19:00
📱 텔레그램 채널: @your_channel
============================================================

🔍 초기 공시 확인 중...

[2024-02-12 10:35:00] 공시 확인 중...
  📋 SK하이닉스: 2건 확인
  ✅ 텔레그램 전송: SK하이닉스 - 주요사항보고서
  ✅ 텔레그램 전송: SK하이닉스 - 분기보고서
✨ 총 2건의 새로운 공시를 전송했습니다.

✅ 스케줄러 시작됨. 5분마다 확인합니다.
종료하려면 Ctrl+C를 누르세요.
```

## 텔레그램 메시지 형식

```
📢 SK하이닉스
주요사항보고서(자기주식취득신탁계약체결결정)

⏰ 2024-02-12
🔗 상세보기
```

## 파일 구조

```
dart_portfolio_disclosure_bot/
├── main.py                    # 메인 봇 코드
├── config.json                # 설정 파일
├── requirements.txt           # 패키지 의존성
├── .env                       # 환경 변수 (생성 필요)
├── .gitignore                # Git 제외 파일
├── sent_disclosures.json     # 전송 기록 (자동 생성)
└── company_codes.json        # 회사 코드 매핑 (자동 생성)
```

## 기술 스택

- **Python 3.8+**
- **DART Open API**: 공시 정보 조회
- **python-telegram-bot**: 텔레그램 봇 API
- **schedule**: 작업 스케줄링
- **requests**: HTTP 요청
- **python-dotenv**: 환경 변수 관리
- **pytz**: 시간대 처리

## 주의사항

⚠️ **API 사용 제한**
- DART API는 일일 호출 제한이 있을 수 있습니다
- `check_interval_minutes`를 너무 짧게 설정하지 마세요 (권장: 5분 이상)

⚠️ **보안**
- `.env` 파일은 절대 Git에 커밋하지 마세요
- API 키와 토큰을 공개하지 마세요

⚠️ **텔레그램 봇 권한**
- 봇을 채널 관리자로 추가해야 메시지 전송이 가능합니다
- 비공개 채널의 경우 봇 초대 필수

## 문제 해결

### 회사명을 찾을 수 없다는 오류
```
⚠️ '삼성전자' 회사 코드를 찾을 수 없습니다.
```
- 정확한 상장사 회사명을 입력했는지 확인하세요
- 예: "삼성전자" (O), "삼성" (X)
- `company_codes.json` 파일을 삭제하면 재다운로드됩니다

### 텔레그램 메시지 전송 실패
```
❌ 텔레그램 전송 실패: Forbidden
```
- 봇이 채널 관리자로 추가되었는지 확인
- `TELEGRAM_CHANNEL_ID`가 올바른지 확인
- 봇 토큰이 유효한지 확인

### DART API 오류
```
❌ 공시 조회 중 오류: Invalid API Key
```
- `.env` 파일의 `DART_API_KEY`가 올바른지 확인
- DART API 키가 활성화되었는지 확인

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트는 언제나 환영합니다!

## 연락처

문의사항이 있으시면 이슈를 등록해주세요.

---

**면책 조항**: 이 봇은 개인적인 용도로 제작되었으며, 투자 권유나 조언을 목적으로 하지 않습니다. 모든 투자 결정은 본인의 책임입니다.
