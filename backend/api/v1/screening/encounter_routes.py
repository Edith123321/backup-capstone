# backend/api/v1/screening/encounter_routes.py
from flask import Blueprint, request, jsonify
import json
import tempfile
import os
import uuid
from werkzeug.utils import secure_filename
from services.database import db

# Import your classifier from heart_sound
from api.v1.screening.heart_sound import classifier, allowed_file, ALLOWED_EXTENSIONS

encounter_bp = Blueprint('encounter', __name__)

@encounter_bp.route('/encounter', methods=['POST', 'OPTIONS'])
def create_encounter():
    """
    Complete SAKA Encounter Endpoint
    Handles: Patient + Triage + Audio + ML Prediction + Auto-RHD Flag
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Parse request
        if request.is_json:
            data = request.get_json()
            doctor_id = data.get('doctor_id')
            patient_data = data.get('patient', {})
            triage_data = data.get('triage', {})
            audio_file = None
        else:
            # Multipart form
            doctor_id = request.form.get('doctor_id')
            
            # Parse JSON strings from form data
            try:
                patient_data = json.loads(request.form.get('patient', '{}'))
            except:
                patient_data = {}
            
            try:
                triage_data = json.loads(request.form.get('triage', '{}'))
            except:
                triage_data = {}
            
            audio_file = request.files.get('file') if 'file' in request.files else None
        
        if not doctor_id:
            return jsonify({'error': 'doctor_id required'}), 400
        
        # === STEP 1: Create or Get Patient ===
        patient_id = patient_data.get('id')
        if not patient_id:
            # Create new patient
            patient_id = db.create_patient(doctor_id, patient_data)
            if not patient_id:
                return jsonify({'error': 'Failed to create patient'}), 500
        
        # === STEP 2: Calculate Jones Triage ===
        triage_score, triage_level, triage_color = db.calculate_jones_triage(triage_data)
        
        # Create triage record
        triage_record_data = {
            'patient_id': patient_id,
            **triage_data,
            'triage_level': triage_level,
            'triage_color': triage_color,
            'triage_score': triage_score
        }
        triage_id = db.create_triage(doctor_id, triage_record_data)
        
        # === STEP 3: Process Audio with ML ===
        ml_result = {
            'prediction': 'No Audio',
            'confidence': 0,
            'probabilities': {'Normal': 0, 'RHD': 0},
            'visualization': None
        }
        
        if audio_file and audio_file.filename != '':
            # Check if file type is allowed
            if not allowed_file(audio_file.filename):
                return jsonify({
                    'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
                }), 400
            
            # Save to temp file for processing
            unique_id = str(uuid.uuid4())[:8]
            filename = secure_filename(audio_file.filename)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                audio_file.save(tmp_file.name)
                filepath = tmp_file.name
            
            try:
                # Use your classifier from heart_sound.py
                if classifier is not None:
                    result = classifier.predict(filepath, return_all=True)
                    
                    if result:
                        ml_result = {
                            'prediction': result['class'],
                            'confidence': result['confidence'],
                            'probabilities': {
                                'Normal': result['prob_normal'],
                                'RHD': result['prob_rhd']
                            },
                            'visualization': result.get('visualization'),
                            'top_features': result.get('top_features', [])
                        }
                        
                        # Save recording to database
                        recording_data = {
                            'patient_id': patient_id,
                            'prediction': result['class'],
                            'confidence': result['confidence'],
                            'probabilities': {
                                'Normal': result['prob_normal'],
                                'RHD': result['prob_rhd']
                            },
                            'file_path': None,  # We don't store the file permanently
                            'duration': 0,  # Could extract from audio
                            'quality_score': 0.8  # Default if not calculated
                        }
                        db.save_heart_sound_recording(doctor_id, recording_data)
                else:
                    # Classifier not loaded - return error but still save triage
                    return jsonify({
                        'error': 'ML Classifier not loaded. Please check model files.',
                        'partial_success': True,
                        'patient_id': patient_id,
                        'triage': {
                            'level': triage_level,
                            'color': triage_color,
                            'score': triage_score
                        }
                    }), 503
                    
            except Exception as e:
                print(f"❌ Audio processing error: {str(e)}")
                # Continue without ML prediction
                ml_result = {
                    'prediction': 'Error',
                    'confidence': 0,
                    'probabilities': {'Normal': 0, 'RHD': 0},
                    'error': str(e)
                }
            finally:
                # Clean up temp file
                if os.path.exists(filepath):
                    os.unlink(filepath)
        
        # === STEP 4: Auto-update RHD Status ===
        rhd_detected = False
        follow_up_days = None
        
        if ml_result.get('prediction') == 'RHD' and ml_result.get('confidence', 0) > 0.3:
            rhd_detected = True
            # Update patient RHD status
            db.update_patient_rhd_from_prediction(
                patient_id,
                ml_result['prediction'],
                ml_result['confidence']
            )
            
            # Set follow-up days based on confidence
            if ml_result['confidence'] > 0.7:
                follow_up_days = 30
            elif ml_result['confidence'] > 0.5:
                follow_up_days = 60
            else:
                follow_up_days = 90
        
        # === STEP 5: Generate Combined Recommendation ===
        recommendation = generate_recommendation(
            ml_result,
            triage_level,
            triage_color,
            rhd_detected
        )
        
        # === STEP 6: Return Response ===
        response = {
            'success': True,
            'patient_id': patient_id,
            'triage': {
                'level': triage_level,
                'color': triage_color,
                'score': triage_score
            },
            'ml_prediction': {
                'prediction': ml_result.get('prediction', 'No Audio'),
                'confidence': ml_result.get('confidence', 0),
                'probabilities': ml_result.get('probabilities', {'Normal': 0, 'RHD': 0})
            },
            'rhd_status': {
                'detected': rhd_detected,
                'follow_up_days': follow_up_days,
                'requires_follow_up': rhd_detected
            },
            'recommendation': recommendation,
            'message': '✅ Encounter completed successfully!'
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Encounter error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def generate_recommendation(ml_result, triage_level, triage_color, rhd_detected):
    """
    Generate combined recommendation from ML prediction and Jones Triage
    """
    # If RHD detected by ML
    if rhd_detected:
        confidence = ml_result.get('confidence', 0)
        
        if triage_color in ['Red', 'Orange']:
            return {
                'priority': 'EMERGENCY',
                'message': '🚨 IMMEDIATE CARDIOLOGY REFERRAL REQUIRED',
                'action': 'Refer to emergency department immediately',
                'timeline': 'Immediate'
            }
        elif triage_color == 'Yellow':
            return {
                'priority': 'URGENT',
                'message': '⚠️ Schedule cardiology consultation within 1 week',
                'action': 'Book cardiology appointment',
                'timeline': 'Within 7 days'
            }
        elif triage_color == 'Green':
            if confidence > 0.7:
                return {
                    'priority': 'HIGH',
                    'message': '📋 High risk RHD detected - Follow up in 1 month',
                    'action': 'Schedule echocardiogram and cardiology follow-up',
                    'timeline': 'Within 30 days'
                }
            else:
                return {
                    'priority': 'MEDIUM',
                    'message': '📋 RHD suspected - Follow up in 3 months',
                    'action': 'Monitor symptoms and schedule follow-up',
                    'timeline': 'Within 90 days'
                }
        else:  # Blue (non-urgent)
            return {
                'priority': 'LOW',
                'message': '🔄 RHD suspected - Regular monitoring recommended',
                'action': 'Annual check-up with symptom monitoring',
                'timeline': 'Annual'
            }
    
    # No RHD detected
    if triage_color in ['Red', 'Orange']:
        return {
            'priority': 'EMERGENCY',
            'message': '🏥 Emergency care required despite normal heart sound',
            'action': 'Immediate medical attention needed',
            'timeline': 'Immediate'
        }
    elif triage_color == 'Yellow':
        return {
            'priority': 'URGENT',
            'message': '⚠️ Medical evaluation recommended',
            'action': 'Schedule doctor appointment',
            'timeline': 'Within 1 week'
        }
    else:
        return {
            'priority': 'ROUTINE',
            'message': '✅ No immediate concerns. Continue regular health monitoring',
            'action': 'Annual health check-up',
            'timeline': 'Annual'
        }