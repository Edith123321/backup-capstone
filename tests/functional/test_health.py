# tests/functional/test_health.py
import pytest
import requests

pytestmark = pytest.mark.functional


class TestSystemEndpoints:
    def test_root(self, base_url):
        r = requests.get(f"{base_url}/", timeout=30)
        assert r.status_code == 200
        assert r.json().get('status') == 'running'

    def test_root_lists_features(self, base_url):
        r = requests.get(f"{base_url}/", timeout=30)
        assert 'features' in r.json()

    def test_root_lists_endpoints(self, base_url):
        r = requests.get(f"{base_url}/", timeout=30)
        assert 'endpoints' in r.json()

    def test_health(self, base_url):
        r = requests.get(f"{base_url}/health", timeout=30)
        assert r.status_code == 200
        assert r.json().get('status') == 'healthy'

    def test_health_services(self, base_url):
        r = requests.get(f"{base_url}/health", timeout=30)
        assert 'services' in r.json()

    def test_health_reports_database(self, base_url):
        r = requests.get(f"{base_url}/health", timeout=30)
        assert r.json().get('services', {}).get('database') in ('healthy', 'unavailable')

    def test_health_has_timestamp(self, base_url):
        r = requests.get(f"{base_url}/health", timeout=30)
        assert 'timestamp' in r.json()

    def test_cors_test_endpoint(self, base_url):
        r = requests.get(f"{base_url}/api/test-cors", timeout=30)
        assert r.status_code == 200
        assert r.json().get('success') is True

    def test_offline_status(self, base_url):
        r = requests.get(f"{base_url}/api/offline/status", timeout=30)
        assert r.status_code == 200

    def test_404_on_unknown(self, base_url):
        r = requests.get(f"{base_url}/api/v1/this/does/not/exist", timeout=30)
        assert r.status_code == 404

    def test_version_present(self, base_url):
        r = requests.get(f"{base_url}/health", timeout=30)
        assert 'version' in r.json()
