# tests/functional/test_patients.py
import pytest
import requests
import json

class TestPatientOperations:
    
    def test_create_patient(self, base_url, api_prefix, auth_headers, test_patient_data):
        """Test creating a new patient"""
        response = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=test_patient_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'patient_id' in data
        
        # Clean up
        if data.get('patient_id'):
            requests.delete(
                f"{base_url}{api_prefix}/database/patients/{data['patient_id']}",
                headers=auth_headers
            )
    
    def test_get_patients(self, base_url, api_prefix, auth_headers, test_doctor_id):
        """Test retrieving patients for a doctor"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/patients",
            params={'doctor_id': test_doctor_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'patients' in data
        assert isinstance(data['patients'], list)
    
    def test_get_patients_missing_doctor_id(self, base_url, api_prefix, auth_headers):
        """Test patients endpoint without doctor_id"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert 'doctor_id required' in data.get('error', '')
    
    def test_get_single_patient(self, base_url, api_prefix, auth_headers, test_patient_data):
        """Test retrieving a specific patient"""
        # Create patient first
        create_resp = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=test_patient_data
        )
        patient_id = create_resp.json().get('patient_id')
        
        if patient_id:
            # Get patient
            response = requests.get(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get('success') == True
            assert data.get('patient').get('id') == patient_id
            
            # Clean up
            requests.delete(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers
            )
    
    def test_update_patient_rhd_status(self, base_url, api_prefix, auth_headers, test_patient_data):
        """Test updating patient RHD status"""
        # Create patient
        create_resp = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=test_patient_data
        )
        patient_id = create_resp.json().get('patient_id')
        
        if patient_id:
            # Update RHD status
            rhd_data = {
                'rhd_status': 'confirmed',
                'rhd_diagnosis_date': '2024-01-01',
                'rhd_treatment': 'Antibiotic prophylaxis',
                'rhd_notes': 'Patient diagnosed with RHD'
            }
            response = requests.put(
                f"{base_url}{api_prefix}/database/patients/{patient_id}/rhd-status",
                headers=auth_headers,
                json=rhd_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get('success') == True
            
            # Clean up
            requests.delete(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers
            )
    
    def test_get_patients_by_rhd_status(self, base_url, api_prefix, auth_headers, test_doctor_id):
        """Test filtering patients by RHD status"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/patients/rhd-status/confirmed",
            params={'doctor_id': test_doctor_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'patients' in data
    
    def test_get_rhd_summary(self, base_url, api_prefix, auth_headers, test_doctor_id):
        """Test getting RHD summary statistics"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/patients/rhd-summary",
            params={'doctor_id': test_doctor_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'summary' in data
        summary = data['summary']
        assert 'total' in summary
        assert 'confirmed' in summary
        assert 'suspected' in summary
    
    def test_update_patient(self, base_url, api_prefix, auth_headers, test_patient_data):
        """Test updating patient information"""
        # Create patient
        create_resp = requests.post(
            f"{base_url}{api_prefix}/database/patients",
            headers=auth_headers,
            json=test_patient_data
        )
        patient_id = create_resp.json().get('patient_id')
        
        if patient_id:
            # Update patient
            update_data = {
                'name': 'Updated Name',
                'contact': '0798765432'
            }
            response = requests.put(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers,
                json=update_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get('success') == True
            
            # Clean up
            requests.delete(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers
            )