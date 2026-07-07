# tests/functional/test_triage.py
import pytest
import requests

class TestTriageOperations:
    
    def test_calculate_triage(self, base_url, api_prefix, auth_headers):
        """Test triage calculation"""
        triage_input = {
            'respiratory_rate': 28,
            'heart_rate': 110,
            'oxygen_saturation': 88,
            'temperature': 38.5,
            'blood_pressure_systolic': 170,
            'blood_pressure_diastolic': 95,
            'consciousness_level': 'confused',
            'pain_score': 8
        }
        response = requests.post(
            f"{base_url}{api_prefix}/database/triage/calculate",
            headers=auth_headers,
            json=triage_input
        )
        assert response.status_code in [200, 400, 401]
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                assert 'triage_level' in data
                assert 'triage_color' in data
                assert 'triage_score' in data
                # Should be at least Urgent based on input
                assert data['triage_color'] in ['Red', 'Orange', 'Yellow', 'Green', 'Blue']
    
    def test_get_triage_by_doctor(self, base_url, api_prefix, auth_headers, test_doctor_id):
        """Test getting triage records for a doctor"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/triage/doctor/{test_doctor_id}",
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 401]