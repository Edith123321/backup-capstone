from flask import Blueprint, request, jsonify, make_response
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.database import db

database_bp = Blueprint('database', __name__)

# ===========================
# CORS HELPER FUNCTIONS
# ===========================

def create_cors_response(data, status=200):
    """Create a response with proper CORS headers"""
    response = make_response(jsonify(data), status)
    response.headers['Access-Control-Allow-Origin'] = 'https://backup-capstone-mbq6.onrender.com'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

def handle_options():
    """Handle OPTIONS preflight requests"""
    response = make_response('', 200)
    response.headers['Access-Control-Allow-Origin'] = 'https://backup-capstone-mbq6.onrender.com'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

# =======================
# PATIENT ROUTES
# =======================

@database_bp.route('/patients', methods=['GET', 'OPTIONS'])
def get_patients():
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        doctor_id = request.args.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        patients = db.get_patients_by_doctor(doctor_id)

        return create_cors_response({
            'success': True,
            'patients': patients
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients', methods=['POST', 'OPTIONS'])
def create_patient():
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        patient_id = db.create_patient(doctor_id, data)

        if patient_id:
            return create_cors_response({'success': True, 'patient_id': patient_id})

        return create_cors_response({'error': 'Failed to create patient'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/<patient_id>', methods=['GET', 'OPTIONS'])
def get_patient(patient_id):
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        patient = db.get_patient_by_id(patient_id)

        if patient:
            return create_cors_response({'success': True, 'patient': patient})

        return create_cors_response({'error': 'Patient not found'}, 404)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


# =======================
# TRIAGE ROUTES
# =======================

@database_bp.route('/triage', methods=['POST', 'OPTIONS'])
def create_triage():
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        triage_id = db.create_triage(doctor_id, data)

        if triage_id:
            return create_cors_response({'success': True, 'triage_id': triage_id})

        return create_cors_response({'error': 'Failed to create triage'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/triage/doctor/<doctor_id>', methods=['GET', 'OPTIONS'])
def get_triage_by_doctor(doctor_id):
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        triage_records = db.get_triage_by_doctor(doctor_id)

        return create_cors_response({
            'success': True,
            'triage': triage_records
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/triage/patient/<patient_id>', methods=['GET', 'OPTIONS'])
def get_triage_by_patient(patient_id):
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        triage_records = db.get_triage_by_patient(patient_id)

        return create_cors_response({
            'success': True,
            'triage': triage_records
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


# =======================
# RECORDINGS
# =======================

@database_bp.route('/recordings', methods=['POST', 'OPTIONS'])
def save_recording():
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        if request.files and 'file' in request.files:
            file = request.files.get('file')
            doctor_id = request.form.get('doctor_id')

            if not doctor_id:
                return create_cors_response({'error': 'doctor_id required'}, 400)

            recording_data = {
                'doctor_id': doctor_id,
                'patient_id': request.form.get('patient_id'),
                'file': file,
                'recording_date': request.form.get('recording_date'),
                'notes': request.form.get('notes', '')
            }

            recording_id = db.save_heart_sound_recording(doctor_id, recording_data)

            if recording_id:
                return create_cors_response({'success': True, 'recording_id': recording_id})

            return create_cors_response({'error': 'Failed to save recording'}, 500)

        # JSON fallback
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        recording_id = db.save_heart_sound_recording(doctor_id, data)

        if recording_id:
            return create_cors_response({'success': True, 'recording_id': recording_id})

        return create_cors_response({'error': 'Failed to save recording'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/recordings/patient/<patient_id>', methods=['GET', 'OPTIONS'])
def get_recordings(patient_id):
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        recordings = db.get_recordings_by_patient(patient_id)

        return create_cors_response({
            'success': True,
            'recordings': recordings
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


# =======================
# DEVICES
# =======================

@database_bp.route('/devices/register', methods=['POST', 'OPTIONS'])
def register_device():
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        device_id = db.register_iot_device(doctor_id, data)

        if device_id:
            return create_cors_response({'success': True, 'device_id': device_id})

        return create_cors_response({'error': 'Failed to register device'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/devices/<doctor_id>', methods=['GET', 'OPTIONS'])
def get_devices(doctor_id):
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        devices = db.get_doctor_devices(doctor_id)

        return create_cors_response({
            'success': True,
            'devices': devices
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/devices/<device_id>/status', methods=['PUT', 'OPTIONS'])
def update_device_status(device_id):
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        status = data.get('status')

        if not status:
            return create_cors_response({'error': 'status required'}, 400)

        success = db.update_device_status(device_id, status)

        if success:
            return create_cors_response({'success': True})

        return create_cors_response({'error': 'Failed to update device'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


# =======================
# TRIAGE CALCULATOR
# =======================

@database_bp.route('/triage/calculate', methods=['POST', 'OPTIONS'])
def calculate_triage():
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json

        if not data:
            return create_cors_response({'error': 'No data provided'}, 400)

        triage_level, triage_color, triage_score = db.calculate_jones_triage(data)

        return create_cors_response({
            'success': True,
            'triage_level': triage_level,
            'triage_color': triage_color,
            'triage_score': triage_score
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)