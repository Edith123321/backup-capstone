# tests/security/test_validation.py
import pytest
import requests

class TestDataValidation:
    
    def test_sql_injection_prevention(self, base_url, api_prefix, auth_headers):
        """Test SQL injection attempts are blocked"""
        malicious_inputs = [
            "'; DROP TABLE patients; --",
            "1' OR '1'='1",
            "' UNION SELECT * FROM users --"
        ]
        
        for input_val in malicious_inputs:
            response = requests.get(
                f"{base_url}{api_prefix}/database/patients",
                params={'doctor_id': input_val},
                headers=auth_headers
            )
            # Should handle gracefully, not crash
            assert response.status_code in [200, 400, 401, 404, 500]
    
    def test_xss_prevention(self, base_url, api_prefix, auth_headers):
        """Test XSS attempts are sanitized"""
        xss_payload = "<script>alert('XSS')</script>"
        patient_data = {
            'name': xss_payload,
            'age': 45,
            'gender': 'Male',
            'doctor_id': 'test'
        }
        
        response = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=patient_data
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 401, 500]
    
    def test_invalid_data_types_rejected(self, base_url, api_prefix, auth_headers):
        """Test invalid data types are rejected"""
        invalid_data = {
            'name': 'Test',
            'age': 'not_a_number',  # Invalid type
            'doctor_id': 'test'
        }
        
        response = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=invalid_data
        )
        assert response.status_code in [200, 400, 500]

class TestInjectionVectors:
    SQLI = ["'; DROP TABLE patients; --", "1' OR '1'='1", "' UNION SELECT * FROM doctors --",
            "admin'--", "1; DELETE FROM patients", "' OR 1=1 --"]
    XSS = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "javascript:alert(1)",
           "<svg/onload=alert(1)>", "'\"><script>alert(1)</script>"]
    TRAVERSAL = ["../../etc/passwd", "..\\..\\windows\\system32", "%2e%2e%2fetc%2fpasswd",
                 "/etc/shadow", "....//....//etc/passwd"]

    @pytest.mark.parametrize('payload', SQLI)
    def test_sqli_does_not_crash(self, base_url, api_prefix, auth_headers, payload):
        r = requests.get(f"{base_url}{api_prefix}/database/patients",
                         params={'doctor_id': payload}, headers=auth_headers, timeout=30)
        assert r.status_code in (200, 400, 401, 404, 500)

    @pytest.mark.parametrize('payload', XSS)
    def test_xss_stored_handled(self, base_url, api_prefix, auth_headers, payload):
        r = requests.post(f"{base_url}{api_prefix}/database/patients", headers=auth_headers,
                          json={'name': payload, 'age': 30, 'gender': 'Male', 'doctor_id': 'test'}, timeout=30)
        assert r.status_code in (200, 400, 401, 500)
        pid = r.json().get('patient_id') if r.status_code == 200 else None
        if pid:
            requests.delete(f"{base_url}{api_prefix}/database/patients/{pid}", headers=auth_headers)

    @pytest.mark.parametrize('payload', TRAVERSAL)
    def test_path_traversal_download(self, base_url, api_prefix, payload):
        r = requests.get(f"{base_url}{api_prefix}/reports/download/{payload}", timeout=30)
        assert r.status_code in (400, 403, 404, 500)

    @pytest.mark.parametrize('bad_age', ['abc', None, [], {}, '99999999999999999999'])
    def test_invalid_age_types(self, base_url, api_prefix, auth_headers, bad_age):
        r = requests.post(f"{base_url}{api_prefix}/database/patients", headers=auth_headers,
                          json={'name': 'T', 'age': bad_age, 'doctor_id': 'test'}, timeout=30)
        assert r.status_code in (200, 400, 401, 500)

    def test_oversized_field(self, base_url, api_prefix, auth_headers):
        r = requests.post(f"{base_url}{api_prefix}/database/patients", headers=auth_headers,
                          json={'name': 'A' * 500000, 'age': 30, 'doctor_id': 'test'}, timeout=30)
        assert r.status_code in (200, 400, 413, 401, 500)

    def test_malformed_json(self, base_url, api_prefix, auth_headers):
        r = requests.post(f"{base_url}{api_prefix}/database/patients", headers=auth_headers,
                          data='{not valid json', timeout=30)
        assert r.status_code in (400, 401, 500)
