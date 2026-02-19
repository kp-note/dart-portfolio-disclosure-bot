#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART 공시 텔레그램 알림 봇
보유 종목의 새로운 공시를 실시간으로 텔레그램 채널에 전송합니다.

명령어 (봇에게 DM으로):
  /list   - 현재 모니터링 중인 종목 목록
  /add    - 종목 추가 (예: /add 삼성전자)
  /remove - 종목 제거 (예: /remove 삼성전자)
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import pytz

# 환경 변수 로드
load_dotenv()

# 설정 값
DART_API_KEY = os.getenv('DART_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
ADMIN_CHAT_ID = int(os.getenv('TELEGRAM_ADMIN_CHAT_ID', '0'))
STOCKS_ENV = os.getenv('STOCKS', '')

# 파일 경로
CONFIG_FILE = 'config.json'
SENT_DISCLOSURES_FILE = 'sent_disclosures.json'
COMPANY_CODES_FILE = 'company_codes.json'
PORTFOLIO_FILE = 'portfolio.json'

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')


class DartTelegramBot:
    """DART 공시를 텔레그램으로 전송하는 봇"""

    def __init__(self):
        self.config = self.load_config()
        self.sent_disclosures = self.load_sent_disclosures()
        self.company_codes = self.load_company_codes()
        self.stocks = self.load_stocks()
        self.bot = None  # start()에서 app.bot으로 설정됨

    def load_config(self):
        """설정 파일 로드"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 오류: {CONFIG_FILE} 파일을 찾을 수 없습니다.")
            exit(1)

    def load_sent_disclosures(self):
        """이미 전송한 공시 목록 로드"""
        try:
            with open(SENT_DISCLOSURES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_sent_disclosures(self):
        """전송한 공시 목록 저장"""
        with open(SENT_DISCLOSURES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.sent_disclosures, f, ensure_ascii=False, indent=2)

    def load_company_codes(self):
        """회사 코드 매핑 로드"""
        try:
            with open(COMPANY_CODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("📥 회사 코드 정보를 다운로드합니다...")
            return self.download_company_codes()

    def download_company_codes(self):
        """DART에서 전체 회사 목록 다운로드"""
        url = 'https://opendart.fss.or.kr/api/corpCode.xml'
        params = {'crtfc_key': DART_API_KEY}

        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                import zipfile
                import io
                import xml.etree.ElementTree as ET

                zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                xml_data = zip_file.read('CORPCODE.xml')

                root = ET.fromstring(xml_data)
                company_codes = {}

                for company in root.findall('list'):
                    corp_name = company.find('corp_name').text
                    corp_code = company.find('corp_code').text
                    stock_code = company.find('stock_code')

                    if stock_code is not None and stock_code.text and stock_code.text.strip():
                        company_codes[corp_name] = {
                            'corp_code': corp_code,
                            'stock_code': stock_code.text
                        }

                with open(COMPANY_CODES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(company_codes, f, ensure_ascii=False, indent=2)

                print(f"✅ {len(company_codes)}개 회사 정보를 다운로드했습니다.")
                return company_codes
            else:
                print(f"❌ 회사 코드 다운로드 실패: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ 회사 코드 다운로드 중 오류: {e}")
            return {}

    def load_stocks(self):
        """포트폴리오 종목 로드
        우선순위: portfolio.json > STOCKS 환경변수 > config.json
        """
        # 1. portfolio.json (런타임 변경사항)
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stocks = data.get('stocks', [])
                if stocks:
                    print(f"📂 portfolio.json에서 {len(stocks)}개 종목 로드")
                    return stocks
        except FileNotFoundError:
            pass

        # 2. STOCKS 환경변수 (쉼표 구분)
        if STOCKS_ENV:
            stocks = [s.strip() for s in STOCKS_ENV.split(',') if s.strip()]
            if stocks:
                print(f"🌐 STOCKS 환경변수에서 {len(stocks)}개 종목 로드")
                return stocks

        # 3. config.json fallback
        stocks = self.config['portfolio']['stocks']
        print(f"📋 config.json에서 {len(stocks)}개 종목 로드")
        return stocks

    def save_stocks(self):
        """현재 포트폴리오를 portfolio.json에 저장"""
        data = {
            'stocks': self.stocks,
            'updated_at': datetime.now(KST).isoformat()
        }
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def find_company_name(self, input_name):
        """입력된 이름으로 company_codes에서 실제 종목명 반환 (부분매칭 포함)"""
        # 정확 매칭
        if input_name in self.company_codes:
            return input_name
        # 부분 매칭
        for name in self.company_codes:
            if input_name in name or name in input_name:
                return name
        return None

    def is_admin(self, update: Update) -> bool:
        """관리자 권한 확인"""
        if ADMIN_CHAT_ID == 0:
            return False
        return update.effective_chat.id == ADMIN_CHAT_ID

    def get_corp_code(self, company_name):
        """회사명으로 회사 코드 찾기"""
        if company_name in self.company_codes:
            return self.company_codes[company_name]['corp_code']

        for name, info in self.company_codes.items():
            if company_name in name or name in company_name:
                print(f"📍 '{company_name}' → '{name}'으로 매칭됨")
                return info['corp_code']

        print(f"⚠️  '{company_name}' 회사 코드를 찾을 수 없습니다.")
        return None

    def fetch_disclosures(self, corp_code, company_name):
        """특정 회사의 최신 공시 조회"""
        url = 'https://opendart.fss.or.kr/api/list.json'

        today = datetime.now(KST).strftime('%Y%m%d')

        params = {
            'crtfc_key': DART_API_KEY,
            'corp_code': corp_code,
            'bgn_de': today,
            'end_de': today,
            'page_count': 100
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data['status'] == '000':
                return data.get('list', [])
            elif data['status'] == '013':
                return []
            else:
                print(f"⚠️  {company_name} 공시 조회 오류: {data.get('message', '알 수 없는 오류')}")
                return []
        except Exception as e:
            print(f"❌ {company_name} 공시 조회 중 오류: {e}")
            return []

    async def send_telegram_message(self, company_name, disclosure):
        """텔레그램으로 공시 메시지 전송"""
        try:
            rcept_dt = disclosure['rcept_dt']
            formatted_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"
            report_nm = disclosure['report_nm']
            rcept_no = disclosure['rcept_no']
            disclosure_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

            message = f"📢 <b>{company_name}</b>\n"
            message += f"{report_nm}\n\n"
            message += f"⏰ {formatted_date}\n"
            message += f"🔗 <a href=\"{disclosure_url}\">상세보기</a>"

            await self.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            print(f"  ✅ 텔레그램 전송: {company_name} - {report_nm}")
            return True

        except TelegramError as e:
            print(f"  ❌ 텔레그램 전송 실패: {e}")
            return False

    def is_within_operating_hours(self):
        """운영 시간 체크 (평일 7시-19시)"""
        now = datetime.now(KST)

        if self.config['schedule']['weekdays_only'] and now.weekday() >= 5:
            return False

        start_hour = self.config['schedule']['start_hour']
        end_hour = self.config['schedule']['end_hour']

        return start_hour <= now.hour < end_hour

    async def check_and_send_disclosures(self):
        """새 공시 확인 및 전송"""
        if not self.is_within_operating_hours():
            now = datetime.now(KST)
            if now.weekday() < 5:
                print(f"⏸  운영 시간 외입니다. (현재: {now.hour}시)")
            return

        print(f"\n[{datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}] 공시 확인 중...")

        new_disclosures_count = 0

        for company_name in self.stocks:
            corp_code = self.get_corp_code(company_name)
            if not corp_code:
                continue

            disclosures = self.fetch_disclosures(corp_code, company_name)

            if disclosures:
                print(f"  📋 {company_name}: {len(disclosures)}건 확인")

                for disclosure in disclosures:
                    rcept_no = disclosure['rcept_no']

                    if rcept_no not in self.sent_disclosures:
                        await self.send_telegram_message(company_name, disclosure)

                        self.sent_disclosures[rcept_no] = {
                            'company': company_name,
                            'report_nm': disclosure['report_nm'],
                            'sent_at': datetime.now(KST).isoformat()
                        }

                        new_disclosures_count += 1
                        await asyncio.sleep(1)

        if new_disclosures_count > 0:
            self.save_sent_disclosures()
            print(f"✨ 총 {new_disclosures_count}건의 새로운 공시를 전송했습니다.\n")
        else:
            print(f"  ℹ️  새로운 공시가 없습니다.\n")

    async def job_check_disclosures(self, context: ContextTypes.DEFAULT_TYPE):
        """JobQueue 콜백: 주기적 공시 확인"""
        await self.check_and_send_disclosures()

    # ── 명령어 핸들러 ──────────────────────────────────────────

    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/list - 현재 모니터링 중인 종목 목록"""
        if not self.is_admin(update):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        if not self.stocks:
            await update.message.reply_text("현재 모니터링 중인 종목이 없습니다.")
            return

        stock_list = '\n'.join(f"{i+1}. {s}" for i, s in enumerate(self.stocks))
        await update.message.reply_text(
            f"📊 현재 모니터링 중인 종목 ({len(self.stocks)}개):\n\n{stock_list}"
        )

    async def cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/add 회사명 - 포트폴리오에 종목 추가"""
        if not self.is_admin(update):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        if not context.args:
            await update.message.reply_text(
                "사용법: /add 회사명\n예) /add 삼성전자"
            )
            return

        input_name = ' '.join(context.args)

        # 이미 포트폴리오에 있는지 확인
        if input_name in self.stocks:
            await update.message.reply_text(f"⚠️ '{input_name}'은 이미 포트폴리오에 있습니다.")
            return

        # company_codes에서 종목 검색
        matched_name = self.find_company_name(input_name)
        if not matched_name:
            await update.message.reply_text(
                f"❌ '{input_name}'을 찾을 수 없습니다.\n"
                f"DART에 등록된 정확한 종목명을 입력해주세요."
            )
            return

        # 추가 및 저장
        self.stocks.append(matched_name)
        self.save_stocks()

        msg = f"✅ '{matched_name}'"
        if matched_name != input_name:
            msg += f" ('{input_name}'으로 검색됨)"
        msg += f"이 추가되었습니다.\n현재 모니터링: {len(self.stocks)}개 종목"
        await update.message.reply_text(msg)

    async def cmd_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/remove 회사명 - 포트폴리오에서 종목 제거"""
        if not self.is_admin(update):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        if not context.args:
            await update.message.reply_text(
                "사용법: /remove 회사명\n예) /remove 삼양식품"
            )
            return

        input_name = ' '.join(context.args)

        # 포트폴리오에서 매칭 종목 찾기 (부분매칭 포함)
        to_remove = None
        for stock in self.stocks:
            if input_name == stock or input_name in stock or stock in input_name:
                to_remove = stock
                break

        if not to_remove:
            await update.message.reply_text(
                f"❌ '{input_name}'을 포트폴리오에서 찾을 수 없습니다.\n"
                f"/list 로 현재 종목을 확인하세요."
            )
            return

        # 제거 및 저장
        self.stocks.remove(to_remove)
        self.save_stocks()

        await update.message.reply_text(
            f"🗑️ '{to_remove}'이 제거되었습니다.\n"
            f"현재 모니터링: {len(self.stocks)}개 종목"
        )

    # ── 봇 시작 ────────────────────────────────────────────────

    def start(self):
        """봇 시작"""
        if ADMIN_CHAT_ID == 0:
            print("⚠️  경고: TELEGRAM_ADMIN_CHAT_ID가 설정되지 않았습니다. 명령어 사용 불가.")

        print("=" * 60)
        print("🚀 DART 공시 텔레그램 알림 봇 시작")
        print("=" * 60)
        print(f"📊 모니터링 종목: {', '.join(self.stocks)}")
        interval = self.config['schedule']['check_interval_minutes']
        print(f"⏰ 확인 주기: {interval}분마다")
        print(f"🕐 운영 시간: 평일 {self.config['schedule']['start_hour']}:00 - {self.config['schedule']['end_hour']}:00")
        print(f"📱 텔레그램 채널: {TELEGRAM_CHANNEL_ID}")
        print(f"👤 관리자 chat ID: {ADMIN_CHAT_ID if ADMIN_CHAT_ID else '미설정'}")
        print("=" * 60)

        # Application 생성 (JobQueue 포함)
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # send_telegram_message에서 self.bot 사용하므로 참조 설정
        self.bot = app.bot

        # 명령어 핸들러 등록
        app.add_handler(CommandHandler("list", self.cmd_list))
        app.add_handler(CommandHandler("add", self.cmd_add))
        app.add_handler(CommandHandler("remove", self.cmd_remove))

        # JobQueue: n분마다 공시 확인 (시작 10초 후 첫 실행)
        app.job_queue.run_repeating(
            self.job_check_disclosures,
            interval=interval * 60,
            first=10
        )

        print(f"\n✅ 스케줄러 시작됨. {interval}분마다 확인합니다.")
        print("명령어: /list, /add 회사명, /remove 회사명")
        print("종료하려면 Ctrl+C를 누르세요.\n")

        # 실행 (내부적으로 이벤트루프 관리, drop_pending으로 과거 명령어 무시)
        app.run_polling(drop_pending_updates=True)


def main():
    """메인 함수"""
    bot = DartTelegramBot()
    bot.start()


if __name__ == '__main__':
    main()
