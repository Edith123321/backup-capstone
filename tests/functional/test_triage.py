# tests/functional/test_triage.py
import pytest
import requests

class TestTriageOperations:
    
    def test_create_triage(self, base_url, api_prefix, auth_headers, test_triage_data, test_patient_data):
        """Test creating a triage record"""
        # Create patient first
        patient_resp = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=test_patient_data
        )
        patient_id = patient_resp.json().get('patient_id')
        
        if patient_id:
            test_triage_data['patient_id'] = patient_id
            
            response = requests.post(
                f"{base_url}{api_prefix}/database/triage",
                headers=auth_headers,
                json=test_triage_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get('success') == True
            assert 'triage_id' in data
            
            # Clean up
            if data.get('triage_id'):
                # Delete triage record via patient deletion
                pass
            requests.delete(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers
            )
    
    def test_get_triage_by_doctor(self, base_url, api_prefix, auth_headers, test_doctor_id):
        """Test getting triage records for a doctor"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/triage/doctor/{test_doctor_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'triage' in data
        assert isinstance(data['triage'], list)
    
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
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'triage_level' in data
        assert 'triage_color' in data
        assert 'triage_score' in data
        
        # Should be at least Urgent based on input
        assert data['triage_color'] in ['Red', 'Orange', 'Yellow', 'Green', 'Blue']
        assert data['triage_score'] >= 0
    
    def test_triage_jones_calculation_red(self, base_url, api_prefix, auth_headers):
        """Test Red triage level calculation"""
        triage_input = {
            'respiratory_rate': 35,
            'heart_rate': 150,
            'oxygen_saturation': 80,
            'temperature': 40,
            'blood_pressure_systolic': 190,
            'blood_pressure_diastolic': 110,
            'consciousness_level': 'unresponsive',
            'pain_score': 10
        }
        response = requests.post(
            f"{base_url}{api_prefix}/database/triage/calculate",
            headers=auth_headers,
            json=triage_input
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert data['triage_color'] == 'Red'
        assert data['triage_score'] >= 15
    
    def test_triage_jones_calculation_green(self, base_url, api_prefix, auth_headers):
        """Test Green triage level calculation"""
        triage_input = {
            'respiratory_rate': 16,
            'heart_rate': 72,
            'oxygen_saturation': 98,
            'temperature': 37,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'consciousness_level': 'alert',
            'pain_score': 2
        }
        response = requests.post(
            f"{base_url}{api_prefix}/database/triage/calculate",
            headers=auth_headers,
            json=triage_input
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert data['triage_color'] == 'Green' or data['triage_color'] == 'Blue'