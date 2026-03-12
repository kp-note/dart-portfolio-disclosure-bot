# Oracle Cloud 배포 가이드

Oracle Cloud의 Always Free Tier를 사용하여 DART 공시 봇을 배포하는 완벽 가이드입니다.

## 1단계: Oracle Cloud 계정 생성

### 1.1 회원가입
1. [Oracle Cloud](https://www.oracle.com/cloud/free/) 접속
2. "Start for free" 클릭
3. 필수 정보 입력:
   - 국가: South Korea
   - 이름, 이메일
   - 비밀번호 설정
4. 이메일 인증 완료

### 1.2 계정 설정
1. **Home Region 선택**: `South Korea (Seoul)` 또는 `Japan (Osaka/Tokyo)` 추천
   - ⚠️ Home Region은 나중에 변경 불가!
2. 신용카드 정보 입력 (무료 티어만 사용하면 과금 없음)
3. 전화번호 인증
4. 계정 승인 대기 (보통 몇 분~1시간)

---

## 2단계: VM 인스턴스 생성

### 2.1 Compute Instance 만들기
1. Oracle Cloud Console 로그인
2. 왼쪽 메뉴 ☰ → **Compute** → **Instances** 클릭
3. **Create Instance** 클릭

### 2.2 인스턴스 설정

#### 기본 정보
- **Name**: `dart-bot` (또는 원하는 이름)

#### Image and Shape
- **Image**: `Ubuntu 22.04` (Canonical Ubuntu 22.04 선택)
- **Shape 변경**: "Change Shape" 클릭
  - **Instance Type**: `Ampere` (ARM 기반, 무료)
  - **Shape**: `VM.Standard.A1.Flex`
  - **OCPUs**: `1` (또는 2)
  - **Memory**: `6 GB` (또는 원하는 만큼, 최대 24GB까지 무료)

#### Networking
- **VCN**: 기본값 사용 (자동 생성됨)
- **Subnet**: 기본값 사용
- **Public IP**: ✅ **Assign a public IPv4 address** 체크

#### SSH Keys
- **Add SSH keys** 선택
- **Generate SSH key pair** 클릭
  - **Save Private Key** 클릭 (다운로드됨 - 중요!)
  - **Save Public Key** 클릭 (다운로드됨)
  - ⚠️ Private Key는 안전한 곳에 보관!

#### Boot Volume
- 기본값 사용 (50GB)

### 2.3 인스턴스 생성
- **Create** 클릭
- 인스턴스 생성 대기 (1-2분)
- 상태가 **Running** (초록색)이 되면 완료

### 2.4 Public IP 확인
- Instance Details 페이지에서 **Public IP Address** 확인 및 복사
- 예: `XXX.XXX.XXX.XXX`

---

## 3단계: 방화벽 설정 (선택사항)

이 봇은 외부 접속을 받지 않으므로 SSH(22번 포트)만 열려있으면 됩니다. 기본 설정 그대로 사용하면 됩니다.

---

## 4단계: SSH 접속

### 4.1 SSH Key 권한 설정 (Mac/Linux)
```bash
# 다운로드한 private key 파일을 이동
mv ~/Downloads/ssh-key-*.key ~/.ssh/oracle-key.pem

# 권한 변경 (필수!)
chmod 400 ~/.ssh/oracle-key.pem
```

### 4.2 SSH 접속
```bash
ssh -i ~/.ssh/oracle-key.pem ubuntu@YOUR_PUBLIC_IP
```

**YOUR_PUBLIC_IP**를 위에서 복사한 Public IP로 변경하세요.

처음 접속 시 fingerprint 확인 메시지가 나오면 `yes` 입력

---

## 5단계: 서버 환경 설정

SSH 접속 후 다음 명령어들을 순서대로 실행하세요:

### 5.1 시스템 업데이트
```bash
sudo apt update && sudo apt upgrade -y
```

### 5.2 Python 및 필수 패키지 설치
```bash
# Python 3.10+ 및 pip 설치
sudo apt install python3 python3-pip python3-venv git -y

# Python 버전 확인
python3 --version
```

### 5.3 작업 디렉토리 생성
```bash
# 홈 디렉토리에서 작업
cd ~

# Git 저장소 클론
git clone https://github.com/kp-note/dart-portfolio-disclosure-bot.git

# 디렉토리 이동
cd dart-portfolio-disclosure-bot
```

### 5.4 가상환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 5.5 환경 변수 설정
```bash
# .env 파일 생성
nano .env
```

다음 내용을 입력하세요:
```
DART_API_KEY=267f2c2a43d9031f017c0c1b4804800a27cf9faf
TELEGRAM_BOT_TOKEN=8266044103:AAHKSG00IV4GHpcU5yTI0klxpVhrPadZhAQ
TELEGRAM_CHANNEL_ID=@KP_portfolio_disclosure
```

저장: `Ctrl + O` → `Enter` → `Ctrl + X`

### 5.6 테스트 실행
```bash
# 봇 실행 테스트
python main.py
```

몇 초 후 봇이 정상 작동하는지 확인하세요. `Ctrl + C`로 종료.

---

## 6단계: 자동 실행 설정 (Systemd Service)

봇이 서버 재시작 후에도 자동으로 실행되도록 설정합니다.

### 6.1 Systemd Service 파일 생성
```bash
sudo nano /etc/systemd/system/dart-bot.service
```

다음 내용을 입력하세요:
```ini
[Unit]
Description=DART Disclosure Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dart-portfolio-disclosure-bot
Environment="PATH=/home/ubuntu/dart-portfolio-disclosure-bot/venv/bin"
ExecStart=/home/ubuntu/dart-portfolio-disclosure-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

저장: `Ctrl + O` → `Enter` → `Ctrl + X`

### 6.2 Service 활성화 및 시작
```bash
# systemd 리로드
sudo systemctl daemon-reload

# 서비스 시작
sudo systemctl start dart-bot

# 서비스 상태 확인
sudo systemctl status dart-bot

# 부팅 시 자동 시작 설정
sudo systemctl enable dart-bot
```

### 6.3 서비스 관리 명령어
```bash
# 서비스 중지
sudo systemctl stop dart-bot

# 서비스 재시작
sudo systemctl restart dart-bot

# 서비스 상태 확인
sudo systemctl status dart-bot

# 로그 확인
sudo journalctl -u dart-bot -f
```

---

## 7단계: 완료! 🎉

이제 봇이 24/7 실행됩니다!

### 확인 사항
✅ 봇이 실행 중인지 확인: `sudo systemctl status dart-bot`
✅ 텔레그램 채널에서 공시 알림 수신 확인
✅ 서버 재시작 후에도 자동 실행되는지 확인

### 로그 모니터링
```bash
# 실시간 로그 확인
sudo journalctl -u dart-bot -f

# 최근 100줄 로그 확인
sudo journalctl -u dart-bot -n 100

# 오늘 로그만 확인
sudo journalctl -u dart-bot --since today
```

---

## 추가 팁

### 다른 봇 추가하기
같은 VM에 여러 봇을 실행할 수 있습니다:

1. 새 봇 저장소 클론
```bash
cd ~
git clone https://github.com/your-username/another-bot.git
cd another-bot
```

2. 가상환경 및 패키지 설치
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. 새 systemd service 파일 생성
```bash
sudo nano /etc/systemd/system/another-bot.service
```

4. 서비스 시작
```bash
sudo systemctl daemon-reload
sudo systemctl start another-bot
sudo systemctl enable another-bot
```

### 비용 걱정 없이 사용하기
- Always Free Tier는 **평생 무료**입니다
- ARM VM (A1.Flex) 총 4 OCPUs + 24GB RAM까지 무료
- 과금을 원하지 않으면 **업그레이드하지 마세요**
- 무료 한도를 초과하면 자동으로 경고가 옵니다

### 보안 팁
- SSH 접속만 허용 (기본 설정)
- Private Key는 안전하게 보관
- 정기적으로 `sudo apt update && sudo apt upgrade` 실행
- `.env` 파일은 절대 Git에 커밋하지 마세요

---

## 문제 해결

### 봇이 시작되지 않을 때
```bash
# 로그 확인
sudo journalctl -u dart-bot -n 50

# 수동 실행해서 에러 확인
cd ~/dart-portfolio-disclosure-bot
source venv/bin/activate
python main.py
```

### 저장소 업데이트
```bash
cd ~/dart-portfolio-disclosure-bot
git pull origin main
sudo systemctl restart dart-bot
```

### VM이 멈췄을 때
Oracle Cloud Console → Instances → dart-bot → **Reboot** 클릭

---

**축하합니다! 🎊 Oracle Cloud에 성공적으로 배포되었습니다!**
