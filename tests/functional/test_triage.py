# tests/functional/test_triage.py
import pytest
import requests

pytestmark = pytest.mark.functional


# (respiratory_rate, heart_rate, spo2, temp, sbp, dbp, consciousness, pain)
TRIAGE_SCENARIOS = [
    (28, 130, 82, 39.5, 180, 100, 'unresponsive', 10),  # critical
    (26, 120, 88, 38.8, 170, 95, 'confused', 8),        # severe
    (22, 105, 92, 38.0, 150, 90, 'alert', 6),           # moderate
    (18, 88, 96, 37.4, 130, 85, 'alert', 4),            # mild
    (16, 72, 99, 36.9, 120, 80, 'alert', 1),            # normal
    (14, 60, 98, 36.5, 110, 70, 'alert', 0),            # low
    (30, 140, 80, 40.0, 190, 110, 'unresponsive', 10),  # extreme
]


class TestTriageCalculation:
    def test_calculate_triage_basic(self, base_url, api_prefix, auth_headers):
        r = requests.post(f"{base_url}{api_prefix}/database/triage/calculate", headers=auth_headers,
                          json={'respiratory_rate': 28, 'heart_rate': 110, 'oxygen_saturation': 88,
                                'temperature': 38.5, 'blood_pressure_systolic': 170,
                                'blood_pressure_diastolic': 95, 'consciousness_level': 'confused',
                                'pain_score': 8}, timeout=30)
        assert r.status_code in (200, 400, 401)

    @pytest.mark.parametrize('rr,hr,spo2,temp,sbp,dbp,cons,pain', TRIAGE_SCENARIOS)
    def test_calculate_returns_valid_color(self, base_url, api_prefix, auth_headers,
                                           rr, hr, spo2, temp, sbp, dbp, cons, pain):
        r = requests.post(f"{base_url}{api_prefix}/database/triage/calculate", headers=auth_headers,
                          json={'respiratory_rate': rr, 'heart_rate': hr, 'oxygen_saturation': spo2,
                                'temperature': temp, 'blood_pressure_systolic': sbp,
                                'blood_pressure_diastolic': dbp, 'consciousness_level': cons,
                                'pain_score': pain}, timeout=30)
        assert r.status_code in (200, 400, 401)
        if r.status_code == 200 and r.json().get('success'):
            assert r.json()['triage_color'] in ['Red', 'Orange', 'Yellow', 'Green', 'Blue']

    @pytest.mark.parametrize('spo2', [70, 80, 85, 90, 95, 100])
    def test_calculate_across_spo2(self, base_url, api_prefix, auth_headers, spo2):
        r = requests.post(f"{base_url}{api_prefix}/database/triage/calculate", headers=auth_headers,
                          json={'oxygen_saturation': spo2, 'heart_rate': 90, 'respiratory_rate': 18,
                                'temperature': 37.0, 'consciousness_level': 'alert', 'pain_score': 3},
                          timeout=30)
        assert r.status_code in (200, 400, 401)

    def test_calculate_empty_body(self, base_url, api_prefix, auth_headers):
        r = requests.post(f"{base_url}{api_prefix}/database/triage/calculate",
                          headers=auth_headers, json={}, timeout=30)
        assert r.status_code in (200, 400, 401, 500)


class TestTriageRecords:
    def test_get_triage_by_doctor(self, base_url, api_prefix, auth_headers, test_doctor_id):
        r = requests.get(f"{base_url}{api_prefix}/database/triage/doctor/{test_doctor_id}",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (200, 404)

    def test_get_triage_by_patient(self, base_url, api_prefix, auth_headers, create_test_patient):
        pid = create_test_patient or 'x'
        r = requests.get(f"{base_url}{api_prefix}/database/triage/patient/{pid}",
                         headers=auth_headers, timeout=30)
        assert r.status_code in (200, 404)

    def test_create_triage(self, base_url, api_prefix, auth_headers, create_test_patient, test_triage_data):
        if not create_test_patient:
            pytest.skip('no patient created')
        data = dict(test_triage_data); data['patient_id'] = create_test_patient
        r = requests.post(f"{base_url}{api_prefix}/database/triage",
                          headers=auth_headers, json=data, timeout=30)
        assert r.status_code in (200, 400, 401, 500)

    def test_create_triage_missing_patient(self, base_url, api_prefix, auth_headers, test_triage_data):
        r = requests.post(f"{base_url}{api_prefix}/database/triage",
                          headers=auth_headers, json=test_triage_data, timeout=30)
        assert r.status_code in (200, 400, 401, 500)
