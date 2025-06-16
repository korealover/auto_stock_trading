"""
한국투자증권 오픈API 연결 테스트
연결 문제 해결을 위한 간단한 테스트 스크립트
"""

import requests
import json
import time
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# SSL 경고 무시 (임시 해결책)
urllib3.disable_warnings(InsecureRequestWarning)


def test_basic_connection():
    """기본 연결 테스트"""
    print("=== 기본 연결 테스트 ===")

    # 모의투자 URL
    vts_url = "https://openapivts.koreainvestment.com:29443"

    # 다양한 설정으로 테스트
    test_configs = [
        {
            "name": "기본 설정",
            "timeout": 30,
            "verify": True,
            "headers": {"User-Agent": "Mozilla/5.0"}
        },
        {
            "name": "긴 타임아웃",
            "timeout": 60,
            "verify": True,
            "headers": {"User-Agent": "Mozilla/5.0"}
        },
        {
            "name": "SSL 검증 비활성화",
            "timeout": 30,
            "verify": False,
            "headers": {"User-Agent": "Mozilla/5.0"}
        },
        {
            "name": "세션 사용",
            "timeout": 30,
            "verify": True,
            "headers": {"User-Agent": "Mozilla/5.0"},
            "use_session": True
        }
    ]

    for config in test_configs:
        print(f"\n{config['name']} 테스트 중...")
        try:
            if config.get('use_session'):
                session = requests.Session()
                response = session.get(
                    f"{vts_url}/",
                    timeout=config['timeout'],
                    verify=config['verify'],
                    headers=config['headers']
                )
            else:
                response = requests.get(
                    f"{vts_url}/",
                    timeout=config['timeout'],
                    verify=config['verify'],
                    headers=config['headers']
                )

            print(f"✓ 성공: HTTP {response.status_code}")
            print(f"  응답 시간: {response.elapsed.total_seconds():.2f}초")
            return True

        except requests.exceptions.ConnectTimeout:
            print("✗ 연결 타임아웃")
        except requests.exceptions.ReadTimeout:
            print("✗ 응답 타임아웃")
        except requests.exceptions.ConnectionError as e:
            print(f"✗ 연결 오류: {e}")
        except Exception as e:
            print(f"✗ 기타 오류: {e}")

    return False


def test_token_request():
    """토큰 요청 테스트 (가짜 키 사용)"""
    print("\n=== 토큰 요청 테스트 ===")

    vts_url = "https://openapivts.koreainvestment.com:29443"
    token_url = f"{vts_url}/oauth2/tokenP"

    headers = {
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # 가짜 데이터로 테스트 (실제 API 키가 없어도 연결 확인 가능)
    data = {
        "grant_type": "client_credentials",
        "appkey": "TEST_KEY",
        "appsecret": "TEST_SECRET"
    }

    configs = [
        {"timeout": 30, "verify": True},
        {"timeout": 60, "verify": True},
        {"timeout": 30, "verify": False}
    ]

    for i, config in enumerate(configs, 1):
        print(f"\n설정 {i} 테스트 중... (타임아웃: {config['timeout']}초)")
        try:
            response = requests.post(
                token_url,
                headers=headers,
                data=json.dumps(data),
                timeout=config['timeout'],
                verify=config['verify']
            )

            print(f"✓ 연결 성공: HTTP {response.status_code}")
            print(f"  응답 시간: {response.elapsed.total_seconds():.2f}초")

            if response.status_code == 400:
                print("  (400 오류는 정상입니다 - 잘못된 API 키로 인한 오류)")

            return True

        except requests.exceptions.ConnectTimeout:
            print("✗ 연결 타임아웃")
        except requests.exceptions.ReadTimeout:
            print("✗ 응답 타임아웃")
        except requests.exceptions.ConnectionError as e:
            print(f"✗ 연결 오류: {e}")
        except Exception as e:
            print(f"✗ 기타 오류: {e}")

    return False


def test_with_proxy():
    """프록시 설정으로 테스트"""
    print("\n=== 프록시 설정 테스트 ===")

    import os

    # 환경변수에서 프록시 확인
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    proxy_settings = {}

    for var in proxy_vars:
        if os.environ.get(var):
            proxy_settings[var.lower()] = os.environ[var]

    if proxy_settings:
        print("발견된 프록시 설정:")
        for key, value in proxy_settings.items():
            print(f"  {key}: {value}")

        try:
            response = requests.get(
                "https://openapivts.koreainvestment.com:29443/",
                timeout=30,
                proxies=proxy_settings
            )
            print(f"✓ 프록시 연결 성공: HTTP {response.status_code}")
            return True
        except Exception as e:
            print(f"✗ 프록시 연결 실패: {e}")
    else:
        print("프록시 설정이 발견되지 않았습니다.")

    return False


def check_firewall_ports():
    """방화벽 포트 확인"""
    print("\n=== 방화벽 포트 확인 ===")

    import socket

    hosts_ports = [
        ("openapivts.koreainvestment.com", 29443),
        ("openapi.koreainvestment.com", 9443)
    ]

    for host, port in hosts_ports:
        print(f"\n{host}:{port} 연결 테스트 중...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print(f"✓ 포트 연결 성공")
            else:
                print(f"✗ 포트 연결 실패 (오류 코드: {result})")

        except Exception as e:
            print(f"✗ 포트 테스트 오류: {e}")


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("한국투자증권 오픈API 연결 문제 진단")
    print("=" * 60)

    # 1. 기본 연결 테스트
    basic_ok = test_basic_connection()

    # 2. 토큰 요청 테스트
    token_ok = test_token_request()

    # 3. 프록시 테스트
    proxy_ok = test_with_proxy()

    # 4. 방화벽 포트 확인
    check_firewall_ports()

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    if basic_ok or token_ok:
        print("✓ 연결 성공! API 키 설정을 확인해보세요.")
    else:
        print("✗ 연결 실패")
        print("\n해결 방안:")
        print("1. 인터넷 연결 상태 확인")
        print("2. 방화벽에서 9443, 29443 포트 허용")
        print("3. 안티바이러스 소프트웨어 설정 확인")
        print("4. 회사 네트워크인 경우 IT 부서에 문의")
        print("5. VPN 연결 해제 후 재시도")
        print("6. 다른 네트워크(모바일 핫스팟)에서 테스트")


def create_test_config():
    """테스트용 설정 파일 생성"""
    test_config = {
        "connection_settings": {
            "timeout": 60,
            "max_retries": 5,
            "retry_delay": 2,
            "verify_ssl": True,
            "use_session": True
        },
        "api_credentials": {
            "app_key": "YOUR_APP_KEY",
            "app_secret": "YOUR_APP_SECRET",
            "account_no": "12345678-01",
            "is_real": False
        }
    }

    with open('test_config.json', 'w', encoding='utf-8') as f:
        json.dump(test_config, f, indent=2, ensure_ascii=False)

    print("test_config.json 파일이 생성되었습니다.")


if __name__ == "__main__":
    try:
        main()

        print("\n테스트용 설정 파일을 생성하시겠습니까? (y/n): ", end="")
        if input().lower() == 'y':
            create_test_config()

    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 중 오류 발생: {e}")