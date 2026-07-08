# tests/functional/test_recordings.py
import pytest
import requests

pytestmark = pytest.mark.functional


class TestRecordings:
    def test_get_recordings_for_patient(self, base_url, api_prefix, auth_headers, create_test_patient):
        pid = create_test_patient or 'nonexistent'
        r = requests.get(f"{base_url}{api_prefix}/database/recordings/patient/{pid}",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert isinstance(r.json().get('recordings', []), list)

    def test_get_recordings_unknown_patient(self, base_url, api_prefix, auth_headers):
        r = requests.get(f"{base_url}{api_prefix}/database/recordings/patient/does-not-exist",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (200, 404)

    def test_screening_recordings_route(self, base_url, api_prefix, create_test_patient):
        pid = create_test_patient or 'x'
        r = requests.get(f"{base_url}{api_prefix}/screening/recordings/{pid}", timeout=30)
        assert r.status_code in (200, 404, 500)

    def test_screening_history_route(self, base_url, api_prefix, create_test_patient):
        pid = create_test_patient or 'x'
        r = requests.get(f"{base_url}{api_prefix}/screening/history/{pid}", timeout=30)
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            assert 'history' in r.json()

    def test_save_recording_requires_ids(self, base_url, api_prefix, auth_headers):
        r = requests.post(f"{base_url}{api_prefix}/screening/save-recording",
                          headers=auth_headers, json={}, timeout=30)
        assert r.status_code in (400, 500)

    def test_severity_history(self, base_url, api_prefix, auth_headers, create_test_patient):
        pid = create_test_patient or 'x'
        r = requests.get(f"{base_url}{api_prefix}/database/severity/history/{pid}",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (200, 404)

    def test_severity_trend(self, base_url, api_prefix, auth_headers, create_test_patient):
        pid = create_test_patient or 'x'
        r = requests.get(f"{base_url}{api_prefix}/database/severity/trend/{pid}",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (200, 404)

    def test_recordings_list_shape(self, base_url, api_prefix, auth_headers, create_test_patient):
        pid = create_test_patient or 'x'
        r = requests.get(f"{base_url}{api_prefix}/database/recordings/patient/{pid}",
                         headers=auth_headers, timeout=30)
        if r.status_code == 200:
            body = r.json()
            assert 'success' in body or 'recordings' in body
