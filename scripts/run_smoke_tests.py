#!/usr/bin/env python3
"""
Script kiểm thử khói (Smoke Test) cho NGINX Gateway và định tuyến toàn hệ thống.
Không phụ thuộc thư viện ngoài (chỉ dùng Python standard library).
"""

import argparse
import sys
import urllib.error
import urllib.request


def test_endpoint(url: str, expected_status: int, description: str) -> bool:
    print(f"[*] Kiểm tra: {description} ({url})...", end=" ")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SupportFlow-SmokeTest/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            if status == expected_status:
                print(f"[ĐẠT] HTTP {status}")
                return True
            else:
                print(f"[THẤT BẠI] Kỳ vọng HTTP {expected_status}, thực tế {status}")
                return False
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            print(f"[ĐẠT] HTTP {e.code}")
            return True
        else:
            print(f"[THẤT BẠI] Kỳ vọng HTTP {expected_status}, thực tế {e.code}")
            return False
    except Exception as e:
        print(f"[LỖI KẾT NỐI] {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy smoke test NGINX Gateway SupportFlow AI")
    parser.add_argument("--target-url", default="http://localhost", help="Địa chỉ gốc của Gateway")
    args = parser.parse_args()

    base_url = args.target_url.rstrip("/")
    print(f"=== Bắt đầu Smoke Test Cổng NGINX Gateway: {base_url} ===\n")

    results = []

    # 1. Kiểm tra Web Frontend SPA
    results.append(
        test_endpoint(
            f"{base_url}/",
            expected_status=200,
            description="Định tuyến Frontend Web SPA",
        )
    )

    # 2. Kiểm tra Backend Health Readiness qua Gateway
    results.append(
        test_endpoint(
            f"{base_url}/health/ready",
            expected_status=200,
            description="Định tuyến Backend API Health Ready",
        )
    )

    # 3. Kiểm tra An ninh: Chặn truy cập công khai vào /internal và /internal/**
    results.append(
        test_endpoint(
            f"{base_url}/internal",
            expected_status=403,
            description="Chặn bảo mật endpoint /internal",
        )
    )
    results.append(
        test_endpoint(
            f"{base_url}/internal/triage",
            expected_status=403,
            description="Chặn bảo mật endpoint /internal/**",
        )
    )

    print("\n" + "=" * 50)
    if all(results):
        print(">>> TẤT CẢ SMOKE TESTS ĐÃ VƯỢT QUA THÀNH CÔNG! <<<")
        return 0
    else:
        print(">>> CÓ BÀI TEST THẤT BẠI! Vui lòng kiểm tra logs NGINX và Backend. <<<")
        return 1


if __name__ == "__main__":
    sys.exit(main())
