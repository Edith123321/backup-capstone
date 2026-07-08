# backend/api/v1/screening/encounter_routes.py
from flask import Blueprint, request, jsonify, make_response
import json
import tempfile
import os
import sys
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.database import db

# Try to import from heart_sound
try:
    from api.v1.screening.heart_sound import classifier, load_audio_safe
    CLASSIFIER_AVAILABLE = classifier is not None
    print(f"✅ Classifier loaded: {CLASSIFIER_AVAILABLE}")
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    classifier = None
    CLASSIFIER_AVAILABLE = False
    load_audio_safe = None

# Signal Quality Assessment — human-centered pre-check (see signal_quality.py).
try:
    from api.v1.screening.signal_quality import assess_signal_quality
except ImportError:
    try:
        from signal_quality import assess_signal_quality
    except ImportError:
        assess_signal_quality = None

# Allowed extensions
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff', 'mp4'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

encounter_bp = Blueprint('encounter', __name__)

# ===========================
# CORS HELPER FUNCTIONS
# ===========================

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
    return ALLOWED_ORIGINS[0]

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

# ===========================
# HELPER FUNCTIONS
# ===========================

def get_severity_grade(prediction, confidence, auscultation_point=None):
    """Get severity grade using the severity grading service"""
    try:
        from services.severity_grading import severity_grader
        result = severity_grader.grade_from_prediction(
            prediction=prediction,
            confidence=confidence,
            auscultation_point=auscultation_point
        )
        return result.to_dict()
    except Exception as e:
        print(f"⚠️ Severity grading error: {e}")
        return {
            'grade': 0,
            'label': 'Unknown',
            'color': '#94a3b8',
            'bg_color': '#f1f5f9',
            'confidence': confidence,
            'recommendation': 'Unable to determine severity'
        }

def generate_recommendation(ml_result, triage_level, triage_color, rhd_detected, severity_grade=None):
    """Generate combined recommendation"""
    if rhd_detected:
        confidence = ml_result.get('confidence', 0)
        severity = severity_grade or 0
        
        if triage_color in ['Red', 'Orange']:
            return {
                'priority': 'EMERGENCY',
                'message': '🚨 IMMEDIATE CARDIOLOGY REFERRAL REQUIRED',
                'action': 'Refer to emergency department immediately',
                'timeline': 'Immediate',
                'severity': severity
            }
        elif triage_color == 'Yellow':
            return {
                'priority': 'URGENT',
                'message': '⚠️ Schedule cardiology consultation within 1 week',
                'action': 'Book cardiology appointment',
                'timeline': 'Within 7 days',
                'severity': severity
            }
        elif triage_color == 'Green':
            if confidence > 0.7:
                return {
                    'priority': 'HIGH',
                    'message': '📋 High risk RHD detected - Follow up in 1 month',
                    'action': 'Schedule echocardiogram and cardiology follow-up',
                    'timeline': 'Within 30 days',
                    'severity': severity
                }
            else:
                return {
                    'priority': 'MEDIUM',
                    'message': '📋 RHD suspected - Follow up in 3 months',
                    'action': 'Monitor symptoms and schedule follow-up',
                    'timeline': 'Within 90 days',
                    'severity': severity
                }
        else:
            return {
                'priority': 'LOW',
                'message': '🔄 RHD suspected - Regular monitoring recommended',
                'action': 'Annual check-up with symptom monitoring',
                'timeline': 'Annual',
                'severity': severity
            }
    
    if triage_color in ['Red', 'Orange']:
        return {
            'priority': 'EMERGENCY',
            'message': '🏥 Emergency care required',
            'action': 'Immediate medical attention needed',
            'timeline': 'Immediate',
            'severity': 0
        }
    elif triage_color == 'Yellow':
        return {
            'priority': 'URGENT',
            'message': '⚠️ Medical evaluation recommended',
            'action': 'Schedule doctor appointment',
            'timeline': 'Within 1 week',
            'severity': 0
        }
    else:
        return {
            'priority': 'ROUTINE',
            'message': '✅ No immediate concerns',
            'action': 'Annual health check-up',
            'timeline': 'Annual',
            'severity': 0
        }

def clinical_red_flag_override(ml_result, triage_color, triage_level=None):
    """
    Scenario 7 — Conflicting Data / Clinical Red-Flag Override.

    The ultimate human-centered safety net: the AI is an aid, not the final word.
    If the clinical triage (Jones criteria) is HIGH RISK but the AI reports a
    normal rhythm, we must NOT let a nurse trust the AI and send a sick child
    home. We surface an explicit, un-ignorable override telling them to refer
    regardless of the AI result.

    Returns an override dict when the conflict exists, otherwise None.
    """
    prediction = str(ml_result.get('prediction', '')).strip().lower()
    ai_says_normal = prediction in ('normal', 'no audio', 'unavailable', 'error', 'no', '')
    high_risk_triage = str(triage_color).strip().lower() in ('red', 'orange')

    if high_risk_triage and ai_says_normal:
        return {
            'active': True,
            'priority': 'OVERRIDE',
            'title': '⚠️ Clinical override: refer regardless of AI',
            'message': (
                'The AI detected a normal rhythm, but the clinical symptoms are '
                'HIGH RISK (Jones triage: '
                f'{triage_level or triage_color}). Do NOT rely on the AI result — '
                'refer this patient to a specialist regardless.'
            ),
            'action': 'Refer to a specialist / cardiologist regardless of AI result',
            'reason': 'triage_high_risk_ai_normal',
        }
    return None


# ===========================
# ROUTES
# ===========================

@encounter_bp.route('/encounter', methods=['POST', 'OPTIONS'])
def create_encounter():
    """Complete SAKA Encounter Endpoint"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        print("🔍 Encounter endpoint called")
        
        # Parse request
        if request.is_json:
            data = request.get_json()
            doctor_id = data.get('doctor_id')
            patient_data = data.get('patient', {})
            triage_data = data.get('triage', {})
            audio_file = None
            auscultation_point = data.get('auscultation_point')
            auscultation_label = data.get('auscultation_label')
        else:
            doctor_id = request.form.get('doctor_id')
            try:
                patient_data = json.loads(request.form.get('patient', '{}'))
            except:
                patient_data = {}
            try:
                triage_data = json.loads(request.form.get('triage', '{}'))
            except:
                triage_data = {}
            audio_file = request.files.get('file') if 'file' in request.files else None
            auscultation_point = request.form.get('auscultation_point')
            auscultation_label = request.form.get('auscultation_label')
        
        print(f"📋 Doctor ID: {doctor_id}")
        print(f"📋 Audio file: {audio_file.filename if audio_file else 'None'}")
        print(f"📋 Auscultation Point: {auscultation_point}")
        
        if not doctor_id:
            return create_cors_response({'error': 'doctor_id required'}, 400)
        
        # === STEP 1: Create or Get Patient ===
        patient_id = patient_data.get('id')
        if not patient_id:
            patient_id = db.create_patient(doctor_id, patient_data)
            if not patient_id:
                return create_cors_response({'error': 'Failed to create patient'}, 500)
        print(f"✅ Patient ID: {patient_id}")
        
        # === STEP 2: Calculate Jones Triage ===
        # Get triage calculation - returns tuple (level, color, score)
        triage_level, triage_color, triage_score = db.calculate_jones_triage(triage_data)
        print(f"✅ Triage: {triage_level} ({triage_color}) - Score: {triage_score}")
        
        # Create triage record
        triage_record_data = {
            'patient_id': patient_id,
            **triage_data,
            'triage_level': triage_level,
            'triage_color': triage_color,
            'triage_score': triage_score
        }
        db.create_triage(doctor_id, triage_record_data)
        
        # === STEP 3: Process Audio with ML ===
        ml_result = {
            'prediction': 'No Audio',
            'confidence': 0,
            'probabilities': {'Normal': 0, 'RHD': 0}
        }
        severity = None
        recording_id = None
        sqa_dict = None   # signal-quality report, populated when audio is present

        if audio_file and audio_file.filename != '':
            print(f"🎵 Processing audio: {audio_file.filename}")
            
            # Check file type
            if not allowed_file(audio_file.filename):
                return create_cors_response({
                    'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
                }, 400)
            
            filepath = None
            try:
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    audio_file.save(tmp_file.name)
                    filepath = tmp_file.name
                print(f"📁 Temp file: {filepath}")

                # === SIGNAL QUALITY ASSESSMENT (human-centered gate) ===
                # If the recording isn't a gradeable heartbeat we skip the AI and
                # record WHY — but we still keep the triage work (a bad recording
                # must never discard a completed clinical assessment).
                sqa_dict = None
                sqa_blocked = False
                if assess_signal_quality is not None and load_audio_safe is not None:
                    try:
                        _y, _sr = load_audio_safe(filepath)
                        if _y is not None:
                            _sqa = assess_signal_quality(_y, sr=4000)
                            sqa_dict = _sqa.to_dict()
                            sqa_blocked = _sqa.blocked
                            if sqa_blocked:
                                print(f"🚫 SQA blocked audio: {_sqa.code} — {_sqa.title}")
                    except Exception as _sqa_err:
                        print(f"⚠️ SQA error (continuing): {_sqa_err}")

                # Run ML prediction (skip if the signal was rejected)
                if sqa_blocked:
                    ml_result = {
                        'prediction': 'Signal Rejected',
                        'confidence': 0,
                        'probabilities': {'Normal': 0, 'RHD': 0},
                        'error': sqa_dict.get('message') if sqa_dict else 'Poor signal quality'
                    }
                elif CLASSIFIER_AVAILABLE and classifier is not None:
                    try:
                        print("🧠 Running ML prediction...")
                        # Call predict without arguments - it takes only the filepath
                        result = classifier.predict(filepath)
                        
                        if result:
                            ml_result = {
                                'prediction': result['class'],
                                'confidence': result['confidence'],
                                'probabilities': {
                                    'Normal': result['prob_normal'],
                                    'RHD': result['prob_rhd']
                                }
                            }
                            print(f"✅ ML Result: {ml_result['prediction']} ({ml_result['confidence']:.2f})")
                            
                            # Get severity grade
                            severity = get_severity_grade(
                                prediction=ml_result['prediction'],
                                confidence=ml_result['confidence'],
                                auscultation_point=auscultation_point
                            )
                            print(f"✅ Severity: Grade {severity['grade']} - {severity['label']}")
                        else:
                            print("⚠️ ML returned None")
                            ml_result = {
                                'prediction': 'Error',
                                'confidence': 0,
                                'probabilities': {'Normal': 0, 'RHD': 0},
                                'error': 'Prediction failed'
                            }
                    except Exception as ml_error:
                        print(f"❌ ML prediction error: {str(ml_error)}")
                        import traceback
                        traceback.print_exc()
                        ml_result = {
                            'prediction': 'Error',
                            'confidence': 0,
                            'probabilities': {'Normal': 0, 'RHD': 0},
                            'error': str(ml_error)
                        }
                else:
                    print("⚠️ Classifier not available")
                    ml_result = {
                        'prediction': 'Unavailable',
                        'confidence': 0,
                        'probabilities': {'Normal': 0, 'RHD': 0},
                        'error': 'Classifier not loaded'
                    }
                
                # Save recording to database
                try:
                    recording_data = {
                        'patient_id': patient_id,
                        'doctor_id': doctor_id,
                        'prediction': ml_result.get('prediction', 'Unknown'),
                        'confidence': ml_result.get('confidence', 0),
                        'probabilities': ml_result.get('probabilities', {}),
                        'severity_grade': severity.get('grade', 0) if severity else 0,
                        'severity_label': severity.get('label', 'Unknown') if severity else 'Unknown',
                        'auscultation_point': auscultation_point,
                        'auscultation_label': auscultation_label,
                        'recording_date': datetime.now().isoformat(),
                        'notes': f"Encounter processed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                    recording_id = db.save_heart_sound_recording(doctor_id, recording_data)
                    print(f"✅ Recording saved with ID: {recording_id}")
                except Exception as db_error:
                    print(f"⚠️ Failed to save recording: {db_error}")
                
            except Exception as audio_error:
                print(f"❌ Audio processing error: {str(audio_error)}")
                import traceback
                traceback.print_exc()
                return create_cors_response({
                    'error': f'Audio processing failed: {str(audio_error)}',
                    'partial_success': True,
                    'patient_id': patient_id,
                    'triage': {
                        'level': triage_level,
                        'color': triage_color,
                        'score': triage_score
                    }
                }, 500)
            finally:
                # Clean up temp file
                if filepath and os.path.exists(filepath):
                    try:
                        os.unlink(filepath)
                        print(f"🗑️ Temp file cleaned up")
                    except:
                        pass
        
        # === STEP 4: Auto-update RHD Status ===
        rhd_detected = False
        follow_up_days = None
        
        if ml_result.get('prediction') == 'RHD' and ml_result.get('confidence', 0) > 0.3:
            rhd_detected = True
            try:
                db.update_patient_rhd_from_prediction(
                    patient_id,
                    ml_result['prediction'],
                    ml_result['confidence']
                )
                print(f"✅ Updated RHD status for patient {patient_id}")
            except Exception as e:
                print(f"⚠️ Failed to update RHD status: {e}")
            
            if ml_result['confidence'] > 0.7:
                follow_up_days = 30
            elif ml_result['confidence'] > 0.5:
                follow_up_days = 60
            else:
                follow_up_days = 90
        
        # === STEP 5: Generate Recommendation ===
        recommendation = generate_recommendation(
            ml_result,
            triage_level,
            triage_color,
            rhd_detected,
            severity.get('grade') if severity else 0
        )

        # Scenario 7 — clinical red-flag override. If triage is high-risk but the
        # AI says normal, this un-ignorable override tells the nurse to refer
        # regardless of the AI. It takes priority over the AI recommendation.
        clinical_override = clinical_red_flag_override(
            ml_result, triage_color, triage_level
        )
        if clinical_override:
            print(f"⚠️ Clinical override active: {clinical_override['reason']}")

        # === STEP 6: Return Response ===
        response = {
            'success': True,
            'patient_id': patient_id,
            'recording_id': recording_id,
            'triage': {
                'level': triage_level,
                'color': triage_color,
                'score': triage_score
            },
            'ml_prediction': {
                'prediction': ml_result.get('prediction', 'No Audio'),
                'confidence': ml_result.get('confidence', 0),
                'probabilities': ml_result.get('probabilities', {'Normal': 0, 'RHD': 0}),
                'error': ml_result.get('error')
            },
            'severity': severity,
            'signal_quality': sqa_dict,
            'clinical_override': clinical_override,
            'auscultation': {
                'point': auscultation_point,
                'label': auscultation_label
            },
            'rhd_status': {
                'detected': rhd_detected,
                'follow_up_days': follow_up_days,
                'requires_follow_up': rhd_detected
            },
            'recommendation': recommendation,
            'message': '✅ Encounter completed successfully!'
        }
        
        print("✅ Returning response")
        return create_cors_response(response)
        
    except Exception as e:
        print(f"❌ Encounter error: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_cors_response({'error': str(e)}, 500)


@encounter_bp.route('/encounter/patient/<patient_id>', methods=['GET', 'OPTIONS'])
def get_patient_encounters(patient_id):
    """Get all encounters for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        # Get patient details
        patient = db.get_patient_by_id(patient_id)
        if not patient:
            return create_cors_response({'error': 'Patient not found'}, 404)
        
        # Get recordings and triage
        recordings = db.get_recordings_by_patient(patient_id)
        triage = db.get_triage_by_patient(patient_id)
        
        # Get severity history
        severity_history = db.get_severity_history(patient_id)
        
        return create_cors_response({
            'success': True,
            'patient': patient,
            'recordings': recordings,
            'triage': triage,
            'severity_history': severity_history,
            'stats': {
                'total_recordings': len(recordings),
                'total_triage': len(triage),
                'has_rhd': patient.get('rhd_status') in ['suspected', 'confirmed']
            }
        })
        
    except Exception as e:
        print(f"❌ Error getting encounters: {str(e)}")
        return create_cors_response({'error': str(e)}, 500)


@encounter_bp.route('/encounter/patient/<patient_id>/latest', methods=['GET', 'OPTIONS'])
def get_latest_encounter(patient_id):
    """Get the latest encounter for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        recordings = db.get_recordings_by_patient(patient_id)
        
        if not recordings:
            return create_cors_response({
                'success': True,
                'has_encounter': False,
                'message': 'No encounters found'
            })
        
        latest = recordings[0]
        triage = db.get_triage_by_patient(patient_id)
        latest_triage = triage[0] if triage else None
        
        return create_cors_response({
            'success': True,
            'has_encounter': True,
            'latest_recording': latest,
            'latest_triage': latest_triage,
            'date': latest.get('recording_date') or latest.get('created_at')
        })
        
    except Exception as e:
        print(f"❌ Error getting latest encounter: {str(e)}")
        return create_cors_response({'error': str(e)}, 500)


@encounter_bp.route('/encounter/status', methods=['GET', 'OPTIONS'])
def get_encounter_status():
    """Get status of encounter system"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    return create_cors_response({
        'status': 'healthy',
        'classifier_available': CLASSIFIER_AVAILABLE,
        'database_available': db is not None,
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'timestamp': datetime.now().isoformat()
    })