import pandas as pd
import numpy as np
import time
import schedule
from datetime import datetime, timedelta
import logging


class AutoTradingStrategy:
    def __init__(self, kis_api, config):
        """
        자동매매 전략 클래스

        Args:
            kis_api: KISOpenAPI 인스턴스
            config: 설정 딕셔너리
        """
        self.api = kis_api
        self.config = config
        self.watchlist = config.get('watchlist', [])
        self.max_position_count = config.get('max_position_count', 5)
        self.max_invest_ratio = config.get('max_invest_ratio', 0.8)  # 최대 투자비율
        self.stop_loss_ratio = config.get('stop_loss_ratio', 0.05)  # 손절 비율
        self.take_profit_ratio = config.get('take_profit_ratio', 0.1)  # 익절 비율

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def is_market_open(self):
        """장 시간 확인"""
        now = datetime.now()
        weekday = now.weekday()
        current_time = now.time()

        # 주말 제외
        if weekday >= 5:  # 토요일(5), 일요일(6)
            return False

        # 장 시간: 09:00 ~ 15:30
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()

        return market_open <= current_time <= market_close

    def calculate_moving_average(self, prices, period):
        """이동평균 계산"""
        return sum(prices[-period:]) / period if len(prices) >= period else None

    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def analyze_stock(self, stock_code):
        """종목 분석"""
        try:
            # 현재가 정보
            current_info = self.api.get_current_price(stock_code)
            if not current_info:
                return None

            # 차트 데이터 (최근 30일)
            chart_data = self.api.get_chart_data(stock_code, period="D", count=30)
            if not chart_data:
                return None

            closes = [data['close'] for data in chart_data]
            volumes = [data['volume'] for data in chart_data]

            # 기술적 분석
            ma5 = self.calculate_moving_average(closes, 5)
            ma20 = self.calculate_moving_average(closes, 20)
            rsi = self.calculate_rsi(closes)

            current_price = current_info['current_price']
            avg_volume = sum(volumes[-5:]) / 5  # 최근 5일 평균 거래량

            analysis = {
                'stock_code': stock_code,
                'current_price': current_price,
                'change_rate': current_info['change_rate'],
                'volume': current_info['volume'],
                'avg_volume': avg_volume,
                'ma5': ma5,
                'ma20': ma20,
                'rsi': rsi,
                'volume_ratio': current_info['volume'] / avg_volume if avg_volume > 0 else 0
            }

            return analysis

        except Exception as e:
            self.logger.error(f"종목 분석 오류 {stock_code}: {e}")
            return None

    def should_buy(self, analysis):
        """매수 신호 판단"""
        if not analysis or not all([analysis['ma5'], analysis['ma20'], analysis['rsi']]):
            return False

        conditions = [
            # 골든크로스: 5일선이 20일선 위에 있음
            analysis['ma5'] > analysis['ma20'],
            # RSI가 과매도 구간에서 벗어남 (30 이상)
            analysis['rsi'] > 30 and analysis['rsi'] < 70,
            # 거래량이 평균의 1.5배 이상
            analysis['volume_ratio'] > 1.5,
            # 하락률이 3% 이내
            analysis['change_rate'] > -3.0
        ]

        return sum(conditions) >= 3  # 4개 조건 중 3개 이상 만족

    def should_sell(self, analysis, holding_info):
        """매도 신호 판단"""
        if not analysis or not holding_info:
            return False

        current_price = analysis['current_price']
        buy_price = holding_info['buy_price']

        # 수익률 계산
        profit_rate = (current_price - buy_price) / buy_price

        conditions = [
            # 손절: 5% 이상 손실
            profit_rate <= -self.stop_loss_ratio,
            # 익절: 10% 이상 수익
            profit_rate >= self.take_profit_ratio,
            # 데드크로스: 5일선이 20일선 아래로
            analysis['ma5'] and analysis['ma20'] and analysis['ma5'] < analysis['ma20'],
            # RSI 과매수 구간
            analysis['rsi'] and analysis['rsi'] > 80
        ]

        return any(conditions)

    def get_portfolio_status(self):
        """포트폴리오 현황 조회"""
        balance = self.api.get_balance()
        if not balance:
            return None

        cash = balance['cash']
        holdings = {}

        for stock in balance['stocks']:
            if int(stock['hldg_qty']) > 0:  # 보유수량이 있는 경우
                holdings[stock['pdno']] = {
                    'quantity': int(stock['hldg_qty']),
                    'buy_price': int(stock['pchs_avg_pric']),
                    'current_value': int(stock['evlu_amt']),
                    'profit_loss': int(stock['evlu_pfls_amt'])
                }

        return {
            'cash': cash,
            'holdings': holdings,
            'position_count': len(holdings)
        }

    def calculate_position_size(self, stock_price, available_cash):
        """포지션 크기 계산"""
        # 최대 투자 가능 금액
        max_invest_amount = available_cash * self.max_invest_ratio

        # 포지션당 최대 투자 금액 (총 자산을 최대 포지션 수로 나눔)
        max_position_amount = max_invest_amount / self.max_position_count

        # 주문 가능 수량
        quantity = int(max_position_amount / stock_price)

        return max(quantity, 0)

    def execute_buy_order(self, stock_code, analysis):
        """매수 주문 실행"""
        try:
            portfolio = self.get_portfolio_status()
            if not portfolio:
                return False

            # 이미 보유중인지 확인
            if stock_code in portfolio['holdings']:
                self.logger.info(f"{stock_code} 이미 보유중")
                return False

            # 최대 포지션 수 확인
            if portfolio['position_count'] >= self.max_position_count:
                self.logger.info("최대 포지션 수 초과")
                return False

            # 주문 수량 계산
            quantity = self.calculate_position_size(
                analysis['current_price'],
                portfolio['cash']
            )

            if quantity <= 0:
                self.logger.info("주문 수량 부족")
                return False

            # 시장가 매수 주문
            result = self.api.buy_order(stock_code, quantity, price=0)

            if result['success']:
                self.logger.info(f"매수 주문 성공: {stock_code}, 수량: {quantity}")
                return True
            else:
                self.logger.error(f"매수 주문 실패: {result['message']}")
                return False

        except Exception as e:
            self.logger.error(f"매수 주문 오류: {e}")
            return False

    def execute_sell_order(self, stock_code, holding_info):
        """매도 주문 실행"""
        try:
            quantity = holding_info['quantity']

            # 시장가 매도 주문
            result = self.api.sell_order(stock_code, quantity, price=0)

            if result['success']:
                profit_loss = holding_info['profit_loss']
                self.logger.info(f"매도 주문 성공: {stock_code}, 수량: {quantity}, 손익: {profit_loss:,}원")
                return True
            else:
                self.logger.error(f"매도 주문 실패: {result['message']}")
                return False

        except Exception as e:
            self.logger.error(f"매도 주문 오류: {e}")
            return False

    def run_strategy(self):
        """전략 실행"""
        if not self.is_market_open():
            self.logger.info("장 시간이 아닙니다.")
            return

        self.logger.info("=== 자동매매 전략 실행 시작 ===")

        try:
            # 포트폴리오 현황 확인
            portfolio = self.get_portfolio_status()
            if not portfolio:
                self.logger.error("포트폴리오 조회 실패")
                return

            self.logger.info(f"현금: {portfolio['cash']:,}원, 보유종목: {portfolio['position_count']}개")

            # 보유 종목 매도 검토
            for stock_code, holding_info in portfolio['holdings'].items():
                analysis = self.analyze_stock(stock_code)
                if analysis and self.should_sell(analysis, holding_info):
                    self.execute_sell_order(stock_code, holding_info)
                    time.sleep(1)  # API 호출 간격

            # 관심종목 매수 검토
            for stock_code in self.watchlist:
                analysis = self.analyze_stock(stock_code)
                if analysis and self.should_buy(analysis):
                    self.execute_buy_order(stock_code, analysis)
                    time.sleep(1)  # API 호출 간격

        except Exception as e:
            self.logger.error(f"전략 실행 오류: {e}")

        self.logger.info("=== 자동매매 전략 실행 완료 ===")

    def start_scheduler(self):
        """스케줄러 시작"""
        # 장 시간 중 5분마다 실행
        schedule.every(5).minutes.do(self.run_strategy)

        self.logger.info("자동매매 스케줄러 시작")

        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 확인