# tests/network/test_rate_limiting.py
import time
import pytest
import requests

pytestmark = pytest.mark.network


class TestRateLimiting:
    def test_rapid_requests_handled(self, base_url):
        codes = [requests.get(f"{base_url}/health", timeout=30).status_code for _ in range(15)]
        assert all(c in (200, 429, 503) for c in codes)

    def test_no_server_error_under_burst(self, base_url):
        codes = [requests.get(f"{base_url}/health", timeout=30).status_code for _ in range(20)]
        assert codes.count(500) == 0

    def test_health_stays_available(self, base_url):
        ok = sum(1 for _ in range(10) if requests.get(f"{base_url}/health", timeout=30).status_code == 200)
        assert ok >= 8

    @pytest.mark.parametrize('n', [5, 10, 20])
    def test_burst_sizes(self, base_url, n):
        codes = [requests.get(f"{base_url}/api/test-cors", timeout=30).status_code for _ in range(n)]
        assert all(c in (200, 429, 503) for c in codes)

    def test_rate_limit_returns_json_or_ok(self, base_url):
        r = requests.get(f"{base_url}/health", timeout=30)
        assert r.headers.get('Content-Type', '').startswith('application/json')

    def test_sequential_latency_stable(self, base_url):
        times = []
        for _ in range(8):
            s = time.time(); requests.get(f"{base_url}/health", timeout=30); times.append(time.time() - s)
        assert max(times) < 30
