from flask import Blueprint, request, jsonify
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.database import db

database_bp = Blueprint('database', __name__, url_prefix='/api/v1/database')


# ============ PATIENT ROUTES ============

@database_bp.route('/patients', methods=['GET'])
def get_patients():
    doctor_id = request.args.get('doctor_id')

    if not doctor_id:
        return jsonify({'error': 'doctor_id required'}), 400

    patients = db.get_patients_by_doctor(doctor_id)

    return jsonify({
        'success': True,
        'patients': patients
    })


@database_bp.route('/patients', methods=['POST'])
def create_patient():
    data = request.json
    doctor_id = data.get('doctor_id')

    if not doctor_id:
        return jsonify({'error': 'doctor_id required'}), 400

    patient_id = db.create_patient(doctor_id, data)

    if patient_id:
        return jsonify({'success': True, 'patient_id': patient_id})

    return jsonify({'error': 'Failed to create patient'}), 500


@database_bp.route('/patients/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    patient = db.get_patient_by_id(patient_id)

    if patient:
        return jsonify({'success': True, 'patient': patient})

    return jsonify({'error': 'Patient not found'}), 404


# ============ TRIAGE ROUTES ============

@database_bp.route('/triage', methods=['POST'])
def create_triage():
    data = request.json
    doctor_id = data.get('doctor_id')

    if not doctor_id:
        return jsonify({'error': 'doctor_id required'}), 400

    triage_id = db.create_triage(doctor_id, data)

    if triage_id:
        return jsonify({'success': True, 'triage_id': triage_id})

    return jsonify({'error': 'Failed to create triage'}), 500


@database_bp.route('/triage/doctor/<doctor_id>', methods=['GET'])
def get_triage_by_doctor(doctor_id):
    triage_records = db.get_triage_by_doctor(doctor_id)

    return jsonify({
        'success': True,
        'triage': triage_records
    })


@database_bp.route('/triage/patient/<patient_id>', methods=['GET'])
def get_triage_by_patient(patient_id):
    triage_records = db.get_triage_by_patient(patient_id)

    return jsonify({
        'success': True,
        'triage': triage_records
    })


# ============ RECORDINGS ============

@database_bp.route('/recordings', methods=['POST'])
def save_recording():
    data = request.json
    doctor_id = data.get('doctor_id')

    if not doctor_id:
        return jsonify({'error': 'doctor_id required'}), 400

    recording_id = db.save_heart_sound_recording(doctor_id, data)

    if recording_id:
        return jsonify({'success': True, 'recording_id': recording_id})

    return jsonify({'error': 'Failed to save recording'}), 500


@database_bp.route('/recordings/patient/<patient_id>', methods=['GET'])
def get_recordings(patient_id):
    recordings = db.get_recordings_by_patient(patient_id)

    return jsonify({
        'success': True,
        'recordings': recordings
    })


# ============ DEVICES ============

@database_bp.route('/devices/register', methods=['POST'])
def register_device():
    data = request.json
    doctor_id = data.get('doctor_id')

    if not doctor_id:
        return jsonify({'error': 'doctor_id required'}), 400

    device_id = db.register_iot_device(doctor_id, data)

    if device_id:
        return jsonify({'success': True, 'device_id': device_id})

    return jsonify({'error': 'Failed to register device'}), 500


@database_bp.route('/devices/<doctor_id>', methods=['GET'])
def get_devices(doctor_id):
    devices = db.get_doctor_devices(doctor_id)

    return jsonify({
        'success': True,
        'devices': devices
    })


@database_bp.route('/devices/<device_id>/status', methods=['PUT'])
def update_device_status(device_id):
    data = request.json
    status = data.get('status')

    if not status:
        return jsonify({'error': 'status required'}), 400

    success = db.update_device_status(device_id, status)

    if success:
        return jsonify({'success': True})

    return jsonify({'error': 'Failed to update device'}), 500


# ============ TRIAGE CALCULATOR ============

@database_bp.route('/triage/calculate', methods=['POST'])
def calculate_triage():
    data = request.json

    triage_level, triage_color, triage_score = db.calculate_jones_triage(data)

    return jsonify({
        'success': True,
        'triage_level': triage_level,
        'triage_color': triage_color,
        'triage_score': triage_score
    })