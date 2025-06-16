import requests
import json
import time
import pandas as pd
from datetime import datetime
import hashlib
import hmac
import base64


class KISOpenAPI:
    def __init__(self, app_key, app_secret, account_no, is_real=False):
        """
        한국투자증권 오픈API 클래스

        Args:
            app_key: API 키
            app_secret: API 시크릿
            account_no: 계좌번호 (8자리-2자리)
            is_real: 실제투자(True) vs 모의투자(False)
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.is_real = is_real

        # API 기본 URL 설정
        if is_real:
            self.base_url = "https://openapi.koreainvestment.com:9443"
        else:
            self.base_url = "https://openapivts.koreainvestment.com:29443"

        self.access_token = None
        self.token_expired = None

        # 최초 토큰 발급
        self.get_access_token()

    def get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"

        headers = {
            "content-type": "application/json"
        }

        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        # 타임아웃 설정 및 재시도 로직 추가
        max_retries = 3
        timeout = 30  # 30초 타임아웃

        for attempt in range(max_retries):
            try:
                print(f"토큰 발급 시도 {attempt + 1}/{max_retries}")

                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(data),
                    timeout=timeout,
                    verify=True  # SSL 인증서 검증
                )

                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result["access_token"]
                    self.token_expired = result["access_token_token_expired"]
                    print("토큰 발급 성공")
                    return
                else:
                    print(f"토큰 발급 실패: {response.status_code} - {response.text}")

            except requests.exceptions.ConnectTimeout:
                print(f"연결 타임아웃 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(5)  # 5초 대기 후 재시도
                    continue
                else:
                    raise Exception("연결 타임아웃: 네트워크 또는 방화벽 설정을 확인해주세요")

            except requests.exceptions.ConnectionError as e:
                print(f"연결 오류: {e}")
                raise Exception("연결 오류: 인터넷 연결 상태를 확인해주세요")

            except requests.exceptions.RequestException as e:
                print(f"요청 오류: {e}")
                raise Exception(f"요청 오류: {e}")

        raise Exception("토큰 발급 실패: 최대 재시도 횟수 초과")

    def get_headers(self, tr_id, tr_cont=""):
        """API 요청 헤더 생성"""
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "tr_cont": tr_cont
        }
        return headers

    def make_request(self, method, url, headers=None, params=None, data=None, timeout=30, max_retries=3):
        """공통 API 요청 메서드 (재시도 로직 포함)"""
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=timeout,
                        verify=True
                    )
                elif method.upper() == 'POST':
                    response = requests.post(
                        url,
                        headers=headers,
                        data=data,
                        timeout=timeout,
                        verify=True
                    )
                else:
                    raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

                return response

            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
                print(f"타임아웃 발생 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                    continue
                else:
                    raise Exception(f"최대 재시도 횟수 초과: {e}")

            except requests.exceptions.ConnectionError as e:
                print(f"연결 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"연결 오류: {e}")

            except Exception as e:
                print(f"예기치 못한 오류: {e}")
                raise

        raise Exception("요청 실패")

    def get_current_price(self, stock_code):
        """현재가 조회 (개선된 버전)"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"

        headers = self.get_headers("FHKST01010100")

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        try:
            response = self.make_request('GET', url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                if data["rt_cd"] == "0":
                    output = data["output"]
                    return {
                        "stock_code": stock_code,
                        "current_price": int(output["stck_prpr"]),
                        "change_rate": float(output["prdy_ctrt"]),
                        "volume": int(output["acml_vol"])
                    }
                else:
                    print(f"API 응답 오류: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"HTTP 오류: {response.status_code}")

        except Exception as e:
            print(f"현재가 조회 오류 {stock_code}: {e}")

        return None

    def get_balance(self):
        """계좌 잔고 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        headers = self.get_headers("TTTC8434R")

        params = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["rt_cd"] == "0":
                return {
                    "cash": int(data["output2"][0]["dnca_tot_amt"]),  # 예수금총액
                    "stocks": data["output1"]  # 보유주식
                }
        return None

    def buy_order(self, stock_code, quantity, price=0, order_type="01"):
        """주식 매수 주문

        Args:
            stock_code: 종목코드
            quantity: 주문수량
            price: 주문가격 (0이면 시장가)
            order_type: 주문구분 ("01": 지정가, "01": 시장가)
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        headers = self.get_headers("TTTC0802U")

        # 시장가 주문인 경우
        if price == 0:
            order_type = "01"  # 시장가
            price = "0"
        else:
            order_type = "00"  # 지정가
            price = str(price)

        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": price
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            result = response.json()
            if result["rt_cd"] == "0":
                return {
                    "order_no": result["output"]["ORD_NO"],
                    "success": True,
                    "message": "매수 주문 성공"
                }
            else:
                return {
                    "success": False,
                    "message": result["msg1"]
                }
        return {"success": False, "message": "주문 실패"}

    def sell_order(self, stock_code, quantity, price=0, order_type="01"):
        """주식 매도 주문"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        headers = self.get_headers("TTTC0801U")

        # 시장가 주문인 경우
        if price == 0:
            order_type = "01"  # 시장가
            price = "0"
        else:
            order_type = "00"  # 지정가
            price = str(price)

        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": price
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            result = response.json()
            if result["rt_cd"] == "0":
                return {
                    "order_no": result["output"]["ORD_NO"],
                    "success": True,
                    "message": "매도 주문 성공"
                }
            else:
                return {
                    "success": False,
                    "message": result["msg1"]
                }
        return {"success": False, "message": "주문 실패"}

    def get_chart_data(self, stock_code, period="D", count=30):
        """차트 데이터 조회

        Args:
            stock_code: 종목코드
            period: 기간 ("D": 일봉, "W": 주봉, "M": 월봉)
            count: 조회할 봉의 개수
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"

        headers = self.get_headers("FHKST03010100")

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": "",
            "FID_INPUT_DATE_2": "",
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0"
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["rt_cd"] == "0":
                chart_data = []
                for item in data["output2"][:count]:
                    chart_data.append({
                        "date": item["stck_bsop_date"],
                        "open": int(item["stck_oprc"]),
                        "high": int(item["stck_hgpr"]),
                        "low": int(item["stck_lwpr"]),
                        "close": int(item["stck_clpr"]),
                        "volume": int(item["acml_vol"])
                    })
                return chart_data
        return None