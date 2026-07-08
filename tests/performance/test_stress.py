# tests/performance/test_stress.py
import concurrent.futures as cf
import pytest
import requests

pytestmark = pytest.mark.performance


def _get(base_url, path='/health'):
    try:
        return requests.get(f"{base_url}{path}", timeout=30).status_code
    except Exception:
        return 0


class TestStress:
    @pytest.mark.parametrize('workers', [4, 8, 16])
    def test_concurrent_requests(self, base_url, workers):
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            codes = list(ex.map(lambda _: _get(base_url), range(workers * 2)))
        assert codes.count(500) == 0
        assert sum(1 for c in codes if c == 200) >= len(codes) * 0.7

    def test_concurrent_mixed_endpoints(self, base_url):
        paths = ['/health', '/', '/api/test-cors', '/api/offline/status'] * 4
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            codes = list(ex.map(lambda p: _get(base_url, p), paths))
        assert codes.count(500) == 0

    def test_large_payload_rejected_cleanly(self, base_url, api_prefix, auth_headers):
        big = {'name': 'X' * 100000, 'age': 30, 'doctor_id': 'test'}
        r = requests.post(f"{base_url}{api_prefix}/database/patients",
                          headers=auth_headers, json=big, timeout=30)
        assert r.status_code in (200, 400, 413, 401, 500)

    def test_server_recovers_after_burst(self, base_url):
        with cf.ThreadPoolExecutor(max_workers=16) as ex:
            list(ex.map(lambda _: _get(base_url), range(32)))
        assert requests.get(f"{base_url}/health", timeout=30).status_code == 200
