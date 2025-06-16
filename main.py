"""
한국투자증권 오픈API 자동매매 프로그램
메인 실행 스크립트
"""

import json
import os
from datetime import datetime
from strategy import AutoTradingStrategy
from api import KISOpenAPI


# 설정 파일 (config.json)을 생성하고 사용하는 예제
def create_config_file():
    """설정 파일 생성"""
    config = {
        "api_credentials": {
            "app_key": "YOUR_APP_KEY",
            "app_secret": "YOUR_APP_SECRET",
            "account_no": "12345678-01",
            "is_real": False  # 모의투자: False, 실제투자: True
        },
        "trading_config": {
            "watchlist": [
                "005930",  # 삼성전자
                "000660",  # SK하이닉스
                "035420",  # NAVER
                "042660",  # 한화오션
                "071050",  # 한국금융지주
                "012450",  # 한화에러로스페이스
            ],
            "max_position_count": 5,  # 최대 보유 종목 수
            "max_invest_ratio": 0.8,  # 최대 투자 비율 (80%)
            "stop_loss_ratio": 0.05,  # 손절 비율 (5%)
            "take_profit_ratio": 0.1  # 익절 비율 (10%)
        }
    }

    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("config.json 파일이 생성되었습니다.")
    print("API 키와 계좌번호를 설정해주세요.")


def load_config():
    """설정 파일 로드"""
    if not os.path.exists('config.json'):
        create_config_file()
        return None

    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_config(config):
    """설정 검증"""
    api_creds = config['api_credentials']

    if api_creds['app_key'] == "YOUR_APP_KEY":
        print("APP_KEY를 설정해주세요.")
        return False

    if api_creds['app_secret'] == "YOUR_APP_SECRET":
        print("APP_SECRET를 설정해주세요.")
        return False

    return True


def main():
    """메인 함수"""
    print("=" * 50)
    print("한국투자증권 오픈API 자동매매 프로그램")
    print("=" * 50)

    # 설정 로드
    config = load_config()
    if not config:
        return

    if not validate_config(config):
        return

    try:
        # API 초기화
        print("API 연결 중...")
        api = KISOpenAPI(
            app_key=config['api_credentials']['app_key'],
            app_secret=config['api_credentials']['app_secret'],
            account_no=config['api_credentials']['account_no'],
            is_real=config['api_credentials']['is_real']
        )

        print("API 연결 성공!")

        # 계좌 정보 확인
        balance = api.get_balance()
        if balance:
            print(f"현재 잔고: {balance['cash']:,}원")
            print(f"보유 종목 수: {len(balance['stocks'])}개")

        # 자동매매 전략 초기화
        strategy = AutoTradingStrategy(api, config['trading_config'])

        # 실행 모드 선택
        print("\n실행 모드를 선택하세요:")
        print("1. 한 번 실행")
        print("2. 자동 스케줄 실행")
        print("3. 포트폴리오 현황 조회")
        print("4. 종목 분석")

        choice = input("선택 (1-4): ").strip()

        if choice == "1":
            # 한 번 실행
            strategy.run_strategy()

        elif choice == "2":
            # 스케줄 실행
            print("자동매매 스케줄러를 시작합니다...")
            print("Ctrl+C로 중단할 수 있습니다.")
            strategy.start_scheduler()

        elif choice == "3":
            # 포트폴리오 현황
            portfolio = strategy.get_portfolio_status()
            if portfolio:
                print(f"\n=== 포트폴리오 현황 ===")
                print(f"현금: {portfolio['cash']:,}원")
                print(f"보유 종목 수: {portfolio['position_count']}개")

                if portfolio['holdings']:
                    print("\n보유 종목:")
                    for code, info in portfolio['holdings'].items():
                        profit_rate = (info['profit_loss'] / (info['buy_price'] * info['quantity'])) * 100
                        print(f"  {code}: {info['quantity']}주, "
                              f"평단가: {info['buy_price']:,}원, "
                              f"손익: {info['profit_loss']:,}원 ({profit_rate:.2f}%)")

        elif choice == "4":
            # 종목 분석
            stock_code = input("분석할 종목코드 입력: ").strip()
            analysis = strategy.analyze_stock(stock_code)

            if analysis:
                print(f"\n=== {stock_code} 분석 결과 ===")
                print(f"현재가: {analysis['current_price']:,}원")
                print(f"등락률: {analysis['change_rate']:.2f}%")
                print(f"5일 이평: {analysis['ma5']:,.0f}원" if analysis['ma5'] else "5일 이평: N/A")
                print(f"20일 이평: {analysis['ma20']:,.0f}원" if analysis['ma20'] else "20일 이평: N/A")
                print(f"RSI: {analysis['rsi']:.2f}" if analysis['rsi'] else "RSI: N/A")
                print(f"거래량 비율: {analysis['volume_ratio']:.2f}배")

                buy_signal = strategy.should_buy(analysis)
                print(f"매수 신호: {'있음' if buy_signal else '없음'}")
            else:
                print("종목 분석 실패")

        else:
            print("잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()


# 사용 예제 및 테스트 함수들

def test_api_connection():
    """API 연결 테스트"""
    config = load_config()
    if not config or not validate_config(config):
        return

    try:
        api = KISOpenAPI(
            app_key=config['api_credentials']['app_key'],
            app_secret=config['api_credentials']['app_secret'],
            account_no=config['api_credentials']['account_no'],
            is_real=config['api_credentials']['is_real']
        )

        # 삼성전자 현재가 조회 테스트
        price_info = api.get_current_price("005930")
        if price_info:
            print(f"삼성전자 현재가: {price_info['current_price']:,}원")
            print("API 연결 테스트 성공!")
        else:
            print("API 연결 테스트 실패")

    except Exception as e:
        print(f"API 연결 테스트 오류: {e}")


def backtest_strategy(start_date, end_date):
    """전략 백테스트 (간단한 예제)"""
    print("백테스트 기능은 별도 구현이 필요합니다.")
    print("실제 구현시에는 과거 데이터를 이용한 시뮬레이션을 추가하세요.")


# 추가 유틸리티 함수들
def get_market_status():
    """장 상태 확인"""
    strategy = AutoTradingStrategy(None, {})
    is_open = strategy.is_market_open()
    print(f"현재 장 상태: {'개장' if is_open else '폐장'}")


def monitor_watchlist():
    """관심종목 모니터링"""
    config = load_config()
    if not config or not validate_config(config):
        return

    api = KISOpenAPI(
        app_key=config['api_credentials']['app_key'],
        app_secret=config['api_credentials']['app_secret'],
        account_no=config['api_credentials']['account_no'],
        is_real=config['api_credentials']['is_real']
    )

    watchlist = config['trading_config']['watchlist']

    print("=== 관심종목 현황 ===")
    for stock_code in watchlist:
        price_info = api.get_current_price(stock_code)
        if price_info:
            print(f"{stock_code}: {price_info['current_price']:,}원 "
                  f"({price_info['change_rate']:+.2f}%)")


# 주의사항 및 사용법 출력
def print_usage():
    """사용법 안내"""
    print("""
=== 자동매매 프로그램 사용법 ===

1. 준비사항:
   - 한국투자증권 오픈API 신청 및 APP KEY 발급
   - 모의투자 계좌 개설 (실제 투자 전 필수 테스트)

2. 설정:
   - config.json 파일에서 API 키와 계좌번호 설정
   - 관심종목, 투자 비율 등 전략 설정

3. 실행:
   - 먼저 모의투자로 충분히 테스트
   - 실제 투자는 소액부터 시작
   - 정기적으로 로그 확인 및 전략 점검

4. 주의사항:
   - 투자에는 항상 위험이 따릅니다
   - 자동매매라도 지속적인 모니터링 필요
   - 시장 상황에 따른 전략 수정 고려

5. 문의:
   - 한국투자증권 고객센터: 1544-5000
   - 오픈API 관련: 별도 문의 채널 확인
""")


if __name__ == "__main__":
    print_usage()
    main()