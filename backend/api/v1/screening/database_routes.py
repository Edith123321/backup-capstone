# backend/api/v1/screening/database_routes.py
from flask import Blueprint, request, jsonify, make_response
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.database import db

database_bp = Blueprint('database', __name__)

# ===========================
# CORS HELPER FUNCTIONS
# ===========================

# List of allowed origins
ALLOWED_ORIGINS = [
    'https://backup-capstone-mbq6.onrender.com',
    'https://capstone-be-yxzd.onrender.com',
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5000'
]

def get_allowed_origin():
    """Get the appropriate allowed origin based on request"""
    origin = request.headers.get('Origin', '')
    if origin in ALLOWED_ORIGINS:
        return origin
    return ALLOWED_ORIGINS[0]  # Default to first allowed origin

def create_cors_response(data, status=200):
    """Create a response with proper CORS headers"""
    response = make_response(jsonify(data), status)
    origin = get_allowed_origin()
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

def handle_options():
    """Handle OPTIONS preflight requests"""
    response = make_response('', 200)
    origin = get_allowed_origin()
    response.headers['Access-Control-Allow-Origin'] = origin
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
    """Get all patients for a doctor"""
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
    """Create a new patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        patient_id = db.create_patient(doctor_id, data)

        if patient_id:
            return create_cors_response({
                'success': True,
                'patient_id': patient_id,
                'message': 'Patient created successfully'
            })

        return create_cors_response({'error': 'Failed to create patient'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/<patient_id>', methods=['GET', 'OPTIONS'])
def get_patient(patient_id):
    """Get a specific patient by ID"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        patient = db.get_patient_by_id(patient_id)

        if patient:
            return create_cors_response({'success': True, 'patient': patient})

        return create_cors_response({'error': 'Patient not found'}, 404)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/<patient_id>', methods=['PUT', 'OPTIONS'])
def update_patient(patient_id):
    """Update patient information"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        
        if not data:
            return create_cors_response({'error': 'No data provided'}, 400)

        success = db.update_patient(patient_id, data)

        if success:
            return create_cors_response({
                'success': True,
                'message': 'Patient updated successfully'
            })

        return create_cors_response({'error': 'Failed to update patient'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/<patient_id>', methods=['DELETE', 'OPTIONS'])
def delete_patient(patient_id):
    """Delete a patient and all associated records"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        success = db.delete_patient(patient_id)

        if success:
            return create_cors_response({
                'success': True,
                'message': 'Patient deleted successfully'
            })

        return create_cors_response({'error': 'Failed to delete patient'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/<patient_id>/summary', methods=['GET', 'OPTIONS'])
def get_patient_summary(patient_id):
    """Get comprehensive patient summary"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        summary = db.get_patient_summary(patient_id)

        if 'error' in summary:
            return create_cors_response({'error': summary['error']}, 404)

        return create_cors_response({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/<patient_id>/rhd-status', methods=['PUT', 'OPTIONS'])
def update_patient_rhd_status(patient_id):
    """Update patient RHD status"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        
        if not data:
            return create_cors_response({'error': 'No data provided'}, 400)
            
        success = db.update_patient_rhd_status(patient_id, data)
        
        if success:
            return create_cors_response({
                'success': True,
                'message': 'RHD status updated successfully'
            })
        
        return create_cors_response({'error': 'Failed to update RHD status'}, 500)
        
    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/rhd-status/<rhd_status>', methods=['GET', 'OPTIONS'])
def get_patients_by_rhd_status(rhd_status):
    """Get patients filtered by RHD status"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        doctor_id = request.args.get('doctor_id')
        
        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)
        
        patients = db.get_patients_by_rhd_status(doctor_id, rhd_status)
        
        return create_cors_response({
            'success': True,
            'patients': patients
        })
        
    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/patients/rhd-summary', methods=['GET', 'OPTIONS'])
def get_rhd_summary():
    """Get RHD summary statistics"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        doctor_id = request.args.get('doctor_id')
        
        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)
        
        patients = db.get_patients_by_doctor(doctor_id)
        
        summary = {
            'total': len(patients),
            'confirmed': 0,
            'suspected': 0,
            'none': 0,
            'unknown': 0,
            'patients': patients
        }
        
        for patient in patients:
            status = patient.get('rhd_status', 'unknown')
            if status in summary:
                summary[status] += 1
        
        return create_cors_response({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# TRIAGE ROUTES
# =======================

@database_bp.route('/triage', methods=['POST', 'OPTIONS'])
def create_triage():
    """Create a new triage record"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        triage_id = db.create_triage(doctor_id, data)

        if triage_id:
            return create_cors_response({
                'success': True,
                'triage_id': triage_id,
                'message': 'Triage created successfully'
            })

        return create_cors_response({'error': 'Failed to create triage'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/triage/doctor/<doctor_id>', methods=['GET', 'OPTIONS'])
def get_triage_by_doctor(doctor_id):
    """Get all triage records for a doctor"""
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
    """Get all triage records for a patient"""
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


@database_bp.route('/triage/calculate', methods=['POST', 'OPTIONS'])
def calculate_triage():
    """Calculate triage level using Jones Triage System"""
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


@database_bp.route('/triage/<triage_id>', methods=['DELETE', 'OPTIONS'])
def delete_triage(triage_id):
    """Delete a triage record"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        # This would need to be implemented in database.py
        # For now, we'll return a placeholder
        return create_cors_response({
            'success': False,
            'error': 'Delete triage not implemented'
        }, 501)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# RECORDINGS ROUTES
# =======================

@database_bp.route('/recordings', methods=['POST', 'OPTIONS'])
def save_recording():
    """Save a heart sound recording"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        # Handle file upload
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
                'notes': request.form.get('notes', ''),
                'prediction': request.form.get('prediction'),
                'confidence': request.form.get('confidence', 0, float),
                'severity_grade': request.form.get('severity_grade', 0, int),
                'severity_label': request.form.get('severity_label'),
                'auscultation_point': request.form.get('auscultation_point'),
                'auscultation_label': request.form.get('auscultation_label')
            }

            recording_id = db.save_heart_sound_recording(doctor_id, recording_data)

            if recording_id:
                return create_cors_response({
                    'success': True,
                    'recording_id': recording_id,
                    'message': 'Recording saved successfully'
                })

            return create_cors_response({'error': 'Failed to save recording'}, 500)

        # JSON fallback
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        recording_id = db.save_heart_sound_recording(doctor_id, data)

        if recording_id:
            return create_cors_response({
                'success': True,
                'recording_id': recording_id,
                'message': 'Recording saved successfully'
            })

        return create_cors_response({'error': 'Failed to save recording'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/recordings/patient/<patient_id>', methods=['GET', 'OPTIONS'])
def get_recordings(patient_id):
    """Get all recordings for a patient"""
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


@database_bp.route('/recordings/<recording_id>', methods=['DELETE', 'OPTIONS'])
def delete_recording(recording_id):
    """Delete a recording"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        # This would need to be implemented in database.py
        return create_cors_response({
            'success': False,
            'error': 'Delete recording not implemented'
        }, 501)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# SEVERITY ROUTES
# =======================

@database_bp.route('/severity/history/<patient_id>', methods=['GET', 'OPTIONS'])
def get_severity_history(patient_id):
    """Get severity history for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        limit = request.args.get('limit', 20, type=int)
        history = db.get_severity_history(patient_id, limit)

        return create_cors_response({
            'success': True,
            'patient_id': patient_id,
            'history': history,
            'count': len(history)
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/severity/trend/<patient_id>', methods=['GET', 'OPTIONS'])
def get_severity_trend(patient_id):
    """Get severity trend analysis for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        trend = db.get_severity_trend(patient_id)

        return create_cors_response({
            'success': True,
            'patient_id': patient_id,
            'trend': trend
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/severity/stats/<doctor_id>', methods=['GET', 'OPTIONS'])
def get_severity_stats(doctor_id):
    """Get severity statistics for a doctor's patients"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        stats = db.get_severity_stats(doctor_id)

        return create_cors_response({
            'success': True,
            'doctor_id': doctor_id,
            'stats': stats
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# DEVICES ROUTES
# =======================

@database_bp.route('/devices/register', methods=['POST', 'OPTIONS'])
def register_device():
    """Register an IoT device"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        device_id = db.register_iot_device(doctor_id, data)

        if device_id:
            return create_cors_response({
                'success': True,
                'device_id': device_id,
                'message': 'Device registered successfully'
            })

        return create_cors_response({'error': 'Failed to register device'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/devices/<doctor_id>', methods=['GET', 'OPTIONS'])
def get_devices(doctor_id):
    """Get all IoT devices for a doctor"""
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
    """Update IoT device status"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        status = data.get('status')

        if not status:
            return create_cors_response({'error': 'status required'}, 400)

        success = db.update_device_status(device_id, status)

        if success:
            return create_cors_response({
                'success': True,
                'message': 'Device status updated successfully'
            })

        return create_cors_response({'error': 'Failed to update device'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/devices/<device_id>', methods=['GET', 'OPTIONS'])
def get_device(device_id):
    """Get a specific IoT device by ID"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        device = db.get_device_by_id(device_id)

        if device:
            return create_cors_response({
                'success': True,
                'device': device
            })

        return create_cors_response({'error': 'Device not found'}, 404)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# FOLLOW-UP REMINDER ROUTES
# =======================

@database_bp.route('/follow-up/reminders/<patient_id>', methods=['GET', 'OPTIONS'])
def get_follow_up_reminders(patient_id):
    """Get follow-up reminders for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        reminders = db.get_follow_up_reminders(patient_id)

        return create_cors_response({
            'success': True,
            'patient_id': patient_id,
            'reminders': reminders,
            'count': len(reminders)
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/follow-up/reminders', methods=['POST', 'OPTIONS'])
def create_follow_up_reminder():
    """Create a follow-up reminder"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        patient_id = data.get('patient_id')
        days = data.get('days')
        reason = data.get('reason')

        if not patient_id or not days:
            return create_cors_response({'error': 'patient_id and days required'}, 400)

        success = db.save_follow_up_reminder(patient_id, days, reason)

        if success:
            return create_cors_response({
                'success': True,
                'message': 'Follow-up reminder created successfully'
            })

        return create_cors_response({'error': 'Failed to create reminder'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)


@database_bp.route('/follow-up/reminders/<reminder_id>/complete', methods=['PUT', 'OPTIONS'])
def complete_follow_up_reminder(reminder_id):
    """Mark a follow-up reminder as completed"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        success = db.complete_follow_up(reminder_id)

        if success:
            return create_cors_response({
                'success': True,
                'message': 'Follow-up reminder completed'
            })

        return create_cors_response({'error': 'Failed to complete reminder'}, 500)

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# STATS ROUTES
# =======================

@database_bp.route('/stats/rhd', methods=['GET', 'OPTIONS'])
def get_stats_rhd():
    """Get RHD statistics for a doctor"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        doctor_id = request.args.get('doctor_id')

        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)

        stats = db.get_rhd_stats(doctor_id)

        return create_cors_response({
            'success': True,
            'doctor_id': doctor_id,
            'stats': stats
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)

# =======================
# BULK OPERATIONS
# =======================

@database_bp.route('/bulk/patients', methods=['POST', 'OPTIONS'])
def bulk_create_patients():
    """Create multiple patients at once"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        patients = data.get('patients', [])
        doctor_id = data.get('doctor_id')

        if not doctor_id or not patients:
            return create_cors_response({'error': 'doctor_id and patients required'}, 400)

        results = []
        for patient_data in patients:
            patient_id = db.create_patient(doctor_id, patient_data)
            results.append({
                'patient_data': patient_data,
                'patient_id': patient_id,
                'success': bool(patient_id)
            })

        return create_cors_response({
            'success': True,
            'results': results,
            'total': len(results),
            'created': sum(1 for r in results if r['success'])
        })

    except Exception as e:
        return create_cors_response({'error': str(e)}, 500)