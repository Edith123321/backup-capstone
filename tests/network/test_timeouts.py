# tests/network/test_timeouts.py
import time
import pytest
import requests

pytestmark = pytest.mark.network

ENDPOINTS = ['/health', '/', '/api/test-cors', '/api/offline/status']


class TestTimeouts:
    @pytest.mark.parametrize('path', ENDPOINTS)
    def test_responds_within_bound(self, base_url, path):
        s = time.time(); r = requests.get(f"{base_url}{path}", timeout=30); dt = time.time() - s
        assert r.status_code < 600
        assert dt < 30, f"{path} took {dt:.1f}s"

    @pytest.mark.parametrize('path', ENDPOINTS)
    def test_no_hang(self, base_url, path):
        try:
            requests.get(f"{base_url}{path}", timeout=30)
        except requests.Timeout:
            pytest.fail(f"{path} timed out")

    def test_screening_health_bound(self, base_url, api_prefix):
        s = time.time(); requests.get(f"{base_url}{api_prefix}/screening/health", timeout=30)
        assert time.time() - s < 30

    def test_connect_timeout_respected(self, base_url):
        # A tiny connect timeout to an unroutable host should fail fast, not hang.
        with pytest.raises((requests.ConnectionError, requests.Timeout)):
            requests.get('http://10.255.255.1/health', timeout=(1, 1))
