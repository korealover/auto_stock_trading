import requests
import socket
import ssl
import time
from urllib.parse import urlparse
import subprocess
import platform


class ConnectionDiagnostic:
    """연결 진단 도구"""

    def __init__(self):
        self.real_api_url = "https://openapi.koreainvestment.com:9443"
        self.vts_api_url = "https://openapivts.koreainvestment.com:29443"

    def check_internet_connection(self):
        """인터넷 연결 상태 확인"""
        print("=== 인터넷 연결 상태 확인 ===")
        try:
            # Google DNS로 연결 테스트
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            print("✓ 인터넷 연결 정상")
            return True
        except OSError:
            print("✗ 인터넷 연결 실패")
            return False

    def check_dns_resolution(self, url):
        """DNS 해석 확인"""
        print(f"\n=== DNS 해석 확인: {url} ===")
        try:
            parsed_url = urlparse(url)
            host = parsed_url.hostname
            ip = socket.gethostbyname(host)
            print(f"✓ DNS 해석 성공: {host} -> {ip}")
            return True
        except socket.gaierror as e:
            print(f"✗ DNS 해석 실패: {e}")
            return False

    def check_port_connectivity(self, url):
        """포트 연결 확인"""
        print(f"\n=== 포트 연결 확인: {url} ===")
        try:
            parsed_url = urlparse(url)
            host = parsed_url.hostname
            port = parsed_url.port

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print(f"✓ 포트 연결 성공: {host}:{port}")
                return True
            else:
                print(f"✗ 포트 연결 실패: {host}:{port}")
                return False
        except Exception as e:
            print(f"✗ 포트 연결 오류: {e}")
            return False

    def check_ssl_certificate(self, url):
        """SSL 인증서 확인"""
        print(f"\n=== SSL 인증서 확인: {url} ===")
        try:
            parsed_url = urlparse(url)
            host = parsed_url.hostname
            port = parsed_url.port or 443

            context = ssl.create_default_context()
            sock = socket.create_connection((host, port), timeout=10)
            ssock = context.wrap_socket(sock, server_hostname=host)

            cert = ssock.getpeercert()
            print(f"✓ SSL 인증서 확인 성공")
            print(f"  발급자: {cert.get('issuer', [{}])[0].get('organizationName', 'Unknown')}")
            print(f"  유효기간: {cert.get('notAfter', 'Unknown')}")

            ssock.close()
            return True
        except Exception as e:
            print(f"✗ SSL 인증서 확인 실패: {e}")
            return False

    def test_http_request(self, url, timeout=30):
        """HTTP 요청 테스트"""
        print(f"\n=== HTTP 요청 테스트: {url} ===")
        try:
            # 간단한 GET 요청으로 연결 테스트
            response = requests.get(
                f"{url}/",
                timeout=timeout,
                verify=True,
                headers={'User-Agent': 'KIS-API-Test/1.0'}
            )

            print(f"✓ HTTP 요청 성공: {response.status_code}")
            return True

        except requests.exceptions.ConnectTimeout:
            print("✗ 연결 타임아웃")
            return False
        except requests.exceptions.ReadTimeout:
            print("✗ 응답 타임아웃")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"✗ 연결 오류: {e}")
            return False
        except Exception as e:
            print(f"✗ HTTP 요청 오류: {e}")
            return False

    def check_firewall_and_proxy(self):
        """방화벽 및 프록시 설정 확인"""
        print("\n=== 방화벽 및 프록시 설정 확인 ===")

        # 환경변수에서 프록시 설정 확인
        import os
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
        proxy_found = False

        for var in proxy_vars:
            if os.environ.get(var):
                print(f"프록시 설정 발견: {var}={os.environ[var]}")
                proxy_found = True

        if not proxy_found:
            print("환경변수에서 프록시 설정을 찾을 수 없습니다.")

        # Windows 방화벽 상태 확인 (Windows만)
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if "ON" in result.stdout:
                    print("Windows 방화벽이 활성화되어 있습니다.")
                    print("방화벽에서 Python 또는 해당 프로그램을 허용해주세요.")
            except:
                print("방화벽 상태를 확인할 수 없습니다.")

    def ping_test(self, host):
        """핑 테스트"""
        print(f"\n=== 핑 테스트: {host} ===")
        try:
            if platform.system() == "Windows":
                cmd = ["ping", "-n", "4", host]
            else:
                cmd = ["ping", "-c", "4", host]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✓ 핑 테스트 성공")
                return True
            else:
                print("✗ 핑 테스트 실패")
                return False

        except subprocess.TimeoutExpired:
            print("✗ 핑 테스트 타임아웃")
            return False
        except Exception as e:
            print(f"✗ 핑 테스트 오류: {e}")
            return False

    def run_full_diagnostic(self, is_real=False):
        """전체 진단 실행"""
        print("=" * 60)
        print("한국투자증권 오픈API 연결 진단 시작")
        print("=" * 60)

        target_url = self.real_api_url if is_real else self.vts_api_url
        target_host = urlparse(target_url).hostname

        results = {}

        # 1. 인터넷 연결 확인
        results['internet'] = self.check_internet_connection()

        # 2. DNS 해석 확인
        results['dns'] = self.check_dns_resolution(target_url)

        # 3. 핑 테스트
        results['ping'] = self.ping_test(target_host)

        # 4. 포트 연결 확인
        results['port'] = self.check_port_connectivity(target_url)

        # 5. SSL 인증서 확인
        results['ssl'] = self.check_ssl_certificate(target_url)

        # 6. HTTP 요청 테스트
        results['http'] = self.test_http_request(target_url)

        # 7. 방화벽 및 프록시 확인
        self.check_firewall_and_proxy()

        # 결과 요약
        print("\n" + "=" * 60)
        print("진단 결과 요약")
        print("=" * 60)

        for test, result in results.items():
            status = "✓ 통과" if result else "✗ 실패"
            print(f"{test.upper()}: {status}")

        # 해결 방안 제시
        failed_tests = [test for test, result in results.items() if not result]

        if failed_tests:
            print(f"\n실패한 테스트: {', '.join(failed_tests)}")
            self.suggest_solutions(failed_tests)
        else:
            print("\n모든 연결 테스트가 성공했습니다!")
            print("API 키나 계좌번호 설정을 확인해보세요.")

    def suggest_solutions(self, failed_tests):
        """해결 방안 제시"""
        print("\n" + "=" * 60)
        print("해결 방안")
        print("=" * 60)

        if 'internet' in failed_tests:
            print("1. 인터넷 연결 문제:")
            print("   - 네트워크 케이블 연결 확인")
            print("   - Wi-Fi 연결 상태 확인")
            print("   - 라우터/모뎀 재시작")

        if 'dns' in failed_tests:
            print("2. DNS 해석 문제:")
            print("   - DNS 서버 설정 확인 (8.8.8.8, 1.1.1.1 등)")
            print("   - hosts 파일 확인")
            print("   - 네트워크 설정 초기화")

        if 'port' in failed_tests or 'http' in failed_tests:
            print("3. 포트 연결 문제:")
            print("   - 방화벽에서 9443/29443 포트 허용")
            print("   - 안티바이러스 소프트웨어 설정 확인")
            print("   - 회사 네트워크인 경우 네트워크 관리자에게 문의")
            print("   - VPN 사용 중인 경우 VPN 설정 확인")

        if 'ssl' in failed_tests:
            print("4. SSL 인증서 문제:")
            print("   - 시스템 시간 확인")
            print("   - 인증서 저장소 업데이트")
            print("   - 안티바이러스의 SSL 스캔 기능 비활성화")

        print("\n일반적인 해결책:")
        print("- 프록시 서버 사용 중인 경우 설정 확인")
        print("- 회사 방화벽인 경우 IT 부서에 문의")
        print("- VPN 연결 해제 후 재시도")
        print("- 다른 네트워크(모바일 핫스팟 등)에서 테스트")


def test_with_different_settings():
    """다양한 설정으로 연결 테스트"""
    print("=== 다양한 설정으로 연결 테스트 ===")

    urls = [
        "https://openapivts.koreainvestment.com:29443",  # 모의투자
        "https://openapi.koreainvestment.com:9443"  # 실제투자
    ]

    session = requests.Session()

    # 다양한 설정으로 테스트
    configs = [
        {"timeout": 10, "verify": True},
        {"timeout": 30, "verify": True},
        {"timeout": 60, "verify": True},
        {"timeout": 30, "verify": False},  # SSL 검증 비활성화
    ]

    for i, url in enumerate(urls):
        print(f"\n{'=' * 50}")
        print(f"테스트 URL {i + 1}: {url}")
        print(f"{'=' * 50}")

        for j, config in enumerate(configs):
            print(f"\n설정 {j + 1}: {config}")
            try:
                response = session.get(
                    f"{url}/",
                    **config,
                    headers={'User-Agent': 'KIS-API-Test/1.0'}
                )
                print(f"✓ 성공: {response.status_code}")
                break  # 성공하면 다음 URL로

            except Exception as e:
                print(f"✗ 실패: {type(e).__name__}: {e}")
        else:
            print("모든 설정으로 연결 실패")


if __name__ == "__main__":
    diagnostic = ConnectionDiagnostic()

    print("진단할 환경을 선택하세요:")
    print("1. 모의투자 (VTS)")
    print("2. 실제투자")

    choice = input("선택 (1-2): ").strip()
    is_real = choice == "2"

    diagnostic.run_full_diagnostic(is_real)

    print("\n추가 테스트를 진행하시겠습니까? (y/n): ", end="")
    if input().lower() == 'y':
        test_with_different_settings()