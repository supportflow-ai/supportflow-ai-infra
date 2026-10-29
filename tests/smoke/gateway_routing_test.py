"""
Pytest integration tests cho NGINX Gateway Routing.
Yêu cầu cụm container compose.system.yml đã khởi động sẵn.
"""

import os
import urllib.error
import urllib.request

GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://localhost:80").rstrip("/")


def request_url(path: str) -> tuple[int, dict, str]:
    url = f"{GATEWAY_BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Pytest-GatewayRouting/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            headers = dict(response.headers)
            return response.getcode(), headers, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, dict(e.headers), body
    except urllib.error.URLError as e:
        return 0, {}, str(e.reason)


class TestGatewayRouting:
    def test_frontend_routing_returns_200(self):
        """Kiểm tra đường dẫn / trả về trang SPA React (200 OK)"""
        status, headers, body = request_url("/")
        assert status == 200
        assert "text/html" in headers.get("Content-Type", "")
        assert len(body) > 0

    def test_backend_health_ready_routing_returns_200(self):
        """Kiểm tra đường dẫn /health/ready được chuyển tới cluster API (200 OK)"""
        status, _, _ = request_url("/health/ready")
        assert status == 200

    def test_internal_endpoint_blocked_with_403(self):
        """Kiểm tra quy tắc bảo mật: Cấm toàn bộ truy cập công khai vào /internal và /internal/*"""
        status_exact, _, body_exact = request_url("/internal")
        assert status_exact == 403
        assert "Forbidden" in body_exact

        status_sub, _, body_sub = request_url("/internal/sensitive-model-route")
        assert status_sub == 403
        assert "Forbidden" in body_sub

    def test_security_headers_present(self):
        """Kiểm tra NGINX đính kèm các security header cơ bản"""
        status, headers, _ = request_url("/")
        assert status == 200
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "SAMEORIGIN"
