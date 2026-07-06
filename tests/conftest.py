# tests/conftest.py
import pytest
import os
import json
import jwt
from datetime import datetime, timedelta
import requests

# Configuration
BASE_URL = os.environ.get('TEST_BASE_URL', 'https://capstone-be-yxzd.onrender.com')
API_PREFIX = '/api/v1'

@pytest.fixture(scope='session')
def base_url():
    """Return the base URL for API tests"""
    return BASE_URL

@pytest.fixture(scope='session')
def api_prefix():
    """Return the API prefix"""
    return API_PREFIX

@pytest.fixture(scope='session')
def test_doctor_id():
    """Return a test doctor ID"""
    return '117085732829392364427'

@pytest.fixture(scope='function')
def auth_headers():
    """Get authentication headers for tests"""
    # Create a test token
    token = jwt.encode(
        {
            'email': 'test@alustudent.com',
            'name': 'Test Doctor',
            'exp': datetime.utcnow() + timedelta(days=1)
        },
        'test-secret',
        algorithm='HS256'
    )
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

@pytest.fixture(scope='function')
def test_patient_data(test_doctor_id):
    """Generate test patient data"""
    import time
    return {
        'name': f'Test Patient {int(time.time())}',
        'age': 45,
        'gender': 'Female',
        'date_of_birth': '1980-01-01',
        'contact': '0712345678',
        'address': '123 Test Street, Nairobi',
        'emergency_contact': '0723456789',
        'medical_history': 'Hypertension, Diabetes',
        'rhd_status': 'unknown',
        'doctor_id': test_doctor_id
    }

@pytest.fixture(scope='function')
def test_triage_data(test_doctor_id):
    """Generate test triage data"""
    return {
        'patient_id': None,  # Will be set in test
        'doctor_id': test_doctor_id,
        'respiratory_rate': 16,
        'heart_rate': 72,
        'oxygen_saturation': 98,
        'temperature': 37.0,
        'blood_pressure_systolic': 120,
        'blood_pressure_diastolic': 80,
        'consciousness_level': 'alert',
        'pain_score': 3,
        'chief_complaint': 'Chest pain',
        'symptoms': 'Shortness of breath, fatigue',
        'notes': 'Patient appears stable'
    }

@pytest.fixture(scope='function')
def create_test_patient(base_url, api_prefix, auth_headers, test_patient_data):
    """Create a test patient and return the ID"""
    patient_id = None
    response = requests.post(
        f"{base_url}{api_prefix}/database/patients",
        headers=auth_headers,
        json=test_patient_data
    )
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            patient_id = data.get('patient_id')
    
    yield patient_id
    
    # Cleanup - delete the patient
    if patient_id:
        try:
            requests.delete(
                f"{base_url}{api_prefix}/database/patients/{patient_id}",
                headers=auth_headers
            )
        except:
            pass