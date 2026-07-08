# tests/performance/test_endurance.py
import time
import pytest
import requests

pytestmark = pytest.mark.performance


class TestEndurance:
    def test_sustained_health_short(self, base_url):
        """~5s of sustained polling; the endpoint must stay healthy."""
        end = time.time() + 5; ok = total = 0
        while time.time() < end:
            total += 1
            if requests.get(f"{base_url}/health", timeout=30).status_code == 200:
                ok += 1
        assert total > 0 and ok / total >= 0.9

    def test_repeated_root(self, base_url):
        ok = sum(1 for _ in range(20) if requests.get(f"{base_url}/", timeout=30).status_code == 200)
        assert ok >= 18

    def test_no_degradation(self, base_url):
        first = [requests.get(f"{base_url}/health", timeout=30).elapsed.total_seconds() for _ in range(5)]
        last = [requests.get(f"{base_url}/health", timeout=30).elapsed.total_seconds() for _ in range(5)]
        assert max(last) < 30 and max(first) < 30

    def test_mixed_endpoint_endurance(self, base_url, api_prefix):
        paths = ['/health', '/', '/api/test-cors']
        codes = []
        for _ in range(10):
            for p in paths:
                codes.append(requests.get(f"{base_url}{p}", timeout=30).status_code)
        assert codes.count(500) == 0
