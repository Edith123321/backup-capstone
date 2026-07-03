# backend/api/v1/screening/database_routes.py
from flask import Blueprint, request, jsonify, make_response
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.database import db

database_bp = Blueprint('database', __name__, url_prefix='/api/v1/database')

# Helper function to add CORS headers
def cors_response(data, status=200):
    response = make_response(jsonify(data), status)
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Handle OPTIONS requests for all routes
@database_bp.route('/<path:path>', methods=['OPTIONS'])
@database_bp.route('/', methods=['OPTIONS'])
def handle_options(path=None):
    return cors_response({})

# ============ PATIENT ROUTES ============

@database_bp.route('/patients', methods=['OPTIONS'])
def patients_options():
    return cors_response({})

@database_bp.route('/patients', methods=['GET'])
def get_patients():
    """Get all patients for the current doctor"""
    doctor_id = request.args.get('doctor_id')
    if not doctor_id:
        return cors_response({'error': 'doctor_id required'}, 400)
    
    patients = db.get_patients_by_doctor(doctor_id)
    return cors_response({'success': True, 'patients': patients})

@database_bp.route('/patients', methods=['POST'])
def create_patient():
    """Create a new patient"""
    data = request.json
    doctor_id = data.get('doctor_id')
    
    if not doctor_id:
        return cors_response({'error': 'doctor_id required'}, 400)
    
    patient_id = db.create_patient(doctor_id, data)
    if patient_id:
        return cors_response({'success': True, 'patient_id': patient_id})
    return cors_response({'error': 'Failed to create patient'}, 500)

@database_bp.route('/patients/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get a specific patient"""
    patient = db.get_patient_by_id(patient_id)
    if patient:
        return cors_response({'success': True, 'patient': patient})
    return cors_response({'error': 'Patient not found'}, 404)

# ============ TRIAGE ROUTES ============

@database_bp.route('/triage', methods=['OPTIONS'])
def triage_options():
    return cors_response({})

@database_bp.route('/triage', methods=['POST'])
def create_triage():
    """Create a new triage record"""
    data = request.json
    doctor_id = data.get('doctor_id')
    
    if not doctor_id:
        return cors_response({'error': 'doctor_id required'}, 400)
    
    triage_id = db.create_triage(doctor_id, data)
    if triage_id:
        return cors_response({'success': True, 'triage_id': triage_id})
    return cors_response({'error': 'Failed to create triage'}, 500)

@database_bp.route('/triage/doctor/<doctor_id>', methods=['GET'])
def get_triage_by_doctor(doctor_id):
    """Get all triage records for a doctor"""
    triage_records = db.get_triage_by_doctor(doctor_id)
    return cors_response({'success': True, 'triage': triage_records})

@database_bp.route('/triage/patient/<patient_id>', methods=['GET'])
def get_triage_by_patient(patient_id):
    """Get all triage records for a patient"""
    triage_records = db.get_triage_by_patient(patient_id)
    return cors_response({'success': True, 'triage': triage_records})

# ============ HEART SOUND RECORDING ROUTES ============

@database_bp.route('/recordings', methods=['OPTIONS'])
def recordings_options():
    return cors_response({})

@database_bp.route('/recordings', methods=['POST'])
def save_recording():
    """Save a heart sound recording"""
    data = request.json
    doctor_id = data.get('doctor_id')
    
    if not doctor_id:
        return cors_response({'error': 'doctor_id required'}, 400)
    
    recording_id = db.save_heart_sound_recording(doctor_id, data)
    if recording_id:
        return cors_response({'success': True, 'recording_id': recording_id})
    return cors_response({'error': 'Failed to save recording'}, 500)

@database_bp.route('/recordings/patient/<patient_id>', methods=['GET'])
def get_recordings(patient_id):
    """Get all recordings for a patient"""
    recordings = db.get_recordings_by_patient(patient_id)
    return cors_response({'success': True, 'recordings': recordings})

# ============ IOT DEVICE ROUTES ============

@database_bp.route('/devices/register', methods=['POST'])
def register_device():
    """Register an IoT device"""
    data = request.json
    doctor_id = data.get('doctor_id')
    
    if not doctor_id:
        return cors_response({'error': 'doctor_id required'}, 400)
    
    device_id = db.register_iot_device(doctor_id, data)
    if device_id:
        return cors_response({'success': True, 'device_id': device_id})
    return cors_response({'error': 'Failed to register device'}, 500)

@database_bp.route('/devices/<doctor_id>', methods=['GET'])
def get_devices(doctor_id):
    """Get all devices for a doctor"""
    devices = db.get_doctor_devices(doctor_id)
    return cors_response({'success': True, 'devices': devices})

@database_bp.route('/devices/<device_id>/status', methods=['PUT'])
def update_device_status(device_id):
    """Update device status"""
    data = request.json
    status = data.get('status')
    
    if not status:
        return cors_response({'error': 'status required'}, 400)
    
    success = db.update_device_status(device_id, status)
    if success:
        return cors_response({'success': True})
    return cors_response({'error': 'Failed to update device'}, 500)

# ============ JONES TRIAGE CALCULATOR ============

@database_bp.route('/triage/calculate', methods=['POST'])
def calculate_triage():
    """Calculate triage level based on Jones Triage System"""
    data = request.json
    
    triage_level, triage_color, triage_score = db.calculate_jones_triage(data)
    
    return cors_response({
        'success': True,
        'triage_level': triage_level,
        'triage_color': triage_color,
        'triage_score': triage_score
    })