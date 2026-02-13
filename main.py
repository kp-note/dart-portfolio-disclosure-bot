#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART 공시 텔레그램 알림 봇
보유 종목의 새로운 공시를 실시간으로 텔레그램 채널에 전송합니다.
"""

import os
import json
import time
import requests
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import pytz

# 환경 변수 로드
load_dotenv()

# 설정 값
DART_API_KEY = os.getenv('DART_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# 파일 경로
CONFIG_FILE = 'config.json'
SENT_DISCLOSURES_FILE = 'sent_disclosures.json'
COMPANY_CODES_FILE = 'company_codes.json'

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')


class DartTelegramBot:
    """DART 공시를 텔레그램으로 전송하는 봇"""

    def __init__(self):
        self.config = self.load_config()
        self.sent_disclosures = self.load_sent_disclosures()
        self.company_codes = self.load_company_codes()
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

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
                # ZIP 파일 저장
                import zipfile
                import io
                import xml.etree.ElementTree as ET

                zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                xml_data = zip_file.read('CORPCODE.xml')

                # XML 파싱
                root = ET.fromstring(xml_data)
                company_codes = {}

                for company in root.findall('list'):
                    corp_name = company.find('corp_name').text
                    corp_code = company.find('corp_code').text
                    stock_code = company.find('stock_code')

                    # 상장사만 저장
                    if stock_code is not None and stock_code.text and stock_code.text.strip():
                        company_codes[corp_name] = {
                            'corp_code': corp_code,
                            'stock_code': stock_code.text
                        }

                # 파일로 저장
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

    def get_corp_code(self, company_name):
        """회사명으로 회사 코드 찾기"""
        if company_name in self.company_codes:
            return self.company_codes[company_name]['corp_code']

        # 정확히 일치하지 않으면 부분 매칭 시도
        for name, info in self.company_codes.items():
            if company_name in name or name in company_name:
                print(f"📍 '{company_name}' → '{name}'으로 매칭됨")
                return info['corp_code']

        print(f"⚠️  '{company_name}' 회사 코드를 찾을 수 없습니다.")
        return None

    def fetch_disclosures(self, corp_code, company_name):
        """특정 회사의 최신 공시 조회"""
        url = 'https://opendart.fss.or.kr/api/list.json'

        # 오늘 날짜
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

            if data['status'] == '000':  # 정상
                if 'list' in data:
                    return data['list']
                else:
                    return []
            elif data['status'] == '013':  # 조회 결과 없음
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
            # 메시지 포맷
            rcept_dt = disclosure['rcept_dt']
            formatted_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"

            report_nm = disclosure['report_nm']
            rcept_no = disclosure['rcept_no']

            # 공시 링크
            disclosure_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

            # 메시지 구성
            message = f"📢 <b>{company_name}</b>\n"
            message += f"{report_nm}\n\n"
            message += f"⏰ {formatted_date}\n"
            message += f"🔗 <a href=\"{disclosure_url}\">상세보기</a>"

            # 텔레그램 전송
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

        # 주말 체크
        if self.config['schedule']['weekdays_only'] and now.weekday() >= 5:
            return False

        # 시간 체크
        start_hour = self.config['schedule']['start_hour']
        end_hour = self.config['schedule']['end_hour']

        if start_hour <= now.hour < end_hour:
            return True

        return False

    async def check_and_send_disclosures(self):
        """새 공시 확인 및 전송"""
        if not self.is_within_operating_hours():
            now = datetime.now(KST)
            if now.weekday() >= 5:
                return  # 주말은 로그도 출력 안 함
            else:
                print(f"⏸  운영 시간 외입니다. (현재: {now.hour}시)")
                return

        print(f"\n[{datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}] 공시 확인 중...")

        stocks = self.config['portfolio']['stocks']
        new_disclosures_count = 0

        for company_name in stocks:
            corp_code = self.get_corp_code(company_name)
            if not corp_code:
                continue

            disclosures = self.fetch_disclosures(corp_code, company_name)

            if disclosures:
                print(f"  📋 {company_name}: {len(disclosures)}건 확인")

                for disclosure in disclosures:
                    rcept_no = disclosure['rcept_no']

                    # 중복 체크
                    if rcept_no not in self.sent_disclosures:
                        # 새 공시 발견!
                        await self.send_telegram_message(company_name, disclosure)

                        # 전송 기록 저장
                        self.sent_disclosures[rcept_no] = {
                            'company': company_name,
                            'report_nm': disclosure['report_nm'],
                            'sent_at': datetime.now(KST).isoformat()
                        }

                        new_disclosures_count += 1

                        # API 부담 줄이기 위해 잠시 대기
                        await asyncio.sleep(1)

        # 전송한 공시 기록 저장
        if new_disclosures_count > 0:
            self.save_sent_disclosures()
            print(f"✨ 총 {new_disclosures_count}건의 새로운 공시를 전송했습니다.\n")
        else:
            print(f"  ℹ️  새로운 공시가 없습니다.\n")

    def run_check(self):
        """비동기 함수를 동기적으로 실행"""
        asyncio.run(self.check_and_send_disclosures())

    def start(self):
        """봇 시작"""
        print("=" * 60)
        print("🚀 DART 공시 텔레그램 알림 봇 시작")
        print("=" * 60)
        print(f"📊 모니터링 종목: {', '.join(self.config['portfolio']['stocks'])}")
        print(f"⏰ 확인 주기: {self.config['schedule']['check_interval_minutes']}분마다")
        print(f"🕐 운영 시간: 평일 {self.config['schedule']['start_hour']}:00 - {self.config['schedule']['end_hour']}:00")
        print(f"📱 텔레그램 채널: {TELEGRAM_CHANNEL_ID}")
        print("=" * 60)

        # 처음 시작할 때 한 번 실행
        print("\n🔍 초기 공시 확인 중...\n")
        self.run_check()

        # 스케줄 설정
        interval = self.config['schedule']['check_interval_minutes']
        schedule.every(interval).minutes.do(self.run_check)

        print(f"\n✅ 스케줄러 시작됨. {interval}분마다 확인합니다.")
        print("종료하려면 Ctrl+C를 누르세요.\n")

        # 스케줄 실행
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 봇을 종료합니다. 안녕히 가세요!")


def main():
    """메인 함수"""
    bot = DartTelegramBot()
    bot.start()


if __name__ == '__main__':
    main()
