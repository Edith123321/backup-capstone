from flask import Blueprint, request, jsonify
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.database import db

# ❗ REMOVE url_prefix HERE
database_bp = Blueprint('database', __name__)


# =======================
# PATIENT ROUTES
# =======================

@database_bp.route('/database/patients', methods=['GET', 'OPTIONS'])
def get_patients():
    try:
        doctor_id = request.args.get('doctor_id')

        if not doctor_id:
            return jsonify({'error': 'doctor_id required'}), 400

        patients = db.get_patients_by_doctor(doctor_id)

        return jsonify({
            'success': True,
            'patients': patients
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@database_bp.route('/database/patients', methods=['POST', 'OPTIONS'])
def create_patient():
    try:
        data = request.json
        doctor_id = data.get('doctor_id')

        if not doctor_id:
            return jsonify({'error': 'doctor_id required'}), 400

        patient_id = db.create_patient(doctor_id, data)

        return jsonify({'success': True, 'patient_id': patient_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@database_bp.route('/database/triage/doctor/<doctor_id>', methods=['GET', 'OPTIONS'])
def get_triage_by_doctor(doctor_id):
    try:
        triage_records = db.get_triage_by_doctor(doctor_id)

        return jsonify({
            'success': True,
            'triage': triage_records
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@database_bp.route('/database/triage/patient/<patient_id>', methods=['GET', 'OPTIONS'])
def get_triage_by_patient(patient_id):
    try:
        triage_records = db.get_triage_by_patient(patient_id)

        return jsonify({
            'success': True,
            'triage': triage_records
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500