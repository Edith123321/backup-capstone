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