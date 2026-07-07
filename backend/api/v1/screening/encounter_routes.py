# backend/api/v1/screening/encounter_routes.py
from flask import Blueprint, request, jsonify
import json
import tempfile
import os
import uuid
from werkzeug.utils import secure_filename
from services.database import db

# Try to import from heart_sound
try:
    from api.v1.screening.heart_sound import classifier, allowed_file, ALLOWED_EXTENSIONS
    CLASSIFIER_AVAILABLE = classifier is not None
    print(f"✅ Classifier loaded: {CLASSIFIER_AVAILABLE}")
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    classifier = None
    CLASSIFIER_AVAILABLE = False
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff'}
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

encounter_bp = Blueprint('encounter', __name__)

@encounter_bp.route('/encounter', methods=['POST', 'OPTIONS'])
def create_encounter():
    """Complete SAKA Encounter Endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        print("🔍 Encounter endpoint called")
        
        # Parse request
        if request.is_json:
            data = request.get_json()
            doctor_id = data.get('doctor_id')
            patient_data = data.get('patient', {})
            triage_data = data.get('triage', {})
            audio_file = None
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
        
        print(f"📋 Doctor ID: {doctor_id}")
        print(f"📋 Audio file: {audio_file.filename if audio_file else 'None'}")
        
        if not doctor_id:
            return jsonify({'error': 'doctor_id required'}), 400
        
        # === STEP 1: Create or Get Patient ===
        patient_id = patient_data.get('id')
        if not patient_id:
            patient_id = db.create_patient(doctor_id, patient_data)
            if not patient_id:
                return jsonify({'error': 'Failed to create patient'}), 500
        print(f"✅ Patient ID: {patient_id}")
        
        # === STEP 2: Calculate Jones Triage ===
        triage_score, triage_level, triage_color = db.calculate_jones_triage(triage_data)
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
        
        if audio_file and audio_file.filename != '':
            print(f"🎵 Processing audio: {audio_file.filename}")
            
            # Check file type
            if not allowed_file(audio_file.filename):
                return jsonify({
                    'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
                }), 400
            
            try:
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    audio_file.save(tmp_file.name)
                    filepath = tmp_file.name
                print(f"📁 Temp file: {filepath}")
                
                # Run ML prediction
                if CLASSIFIER_AVAILABLE and classifier is not None:
                    try:
                        print("🧠 Running ML prediction...")
                        result = classifier.predict(filepath, return_all=True)
                        
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
                        else:
                            print("⚠️ ML returned None")
                    except Exception as ml_error:
                        print(f"❌ ML prediction error: {str(ml_error)}")
                        import traceback
                        traceback.print_exc()
                        # Return a graceful error response
                        return jsonify({
                            'error': f'ML prediction failed: {str(ml_error)}',
                            'partial_success': True,
                            'patient_id': patient_id,
                            'triage': {
                                'level': triage_level,
                                'color': triage_color,
                                'score': triage_score
                            }
                        }), 500
                else:
                    print("⚠️ Classifier not available")
                    ml_result = {
                        'prediction': 'Unavailable',
                        'confidence': 0,
                        'probabilities': {'Normal': 0, 'RHD': 0},
                        'error': 'Classifier not loaded'
                    }
                
                # Save recording to database (even if ML failed)
                try:
                    recording_data = {
                        'patient_id': patient_id,
                        'prediction': ml_result.get('prediction', 'Unknown'),
                        'confidence': ml_result.get('confidence', 0),
                        'probabilities': ml_result.get('probabilities', {})
                    }
                    db.save_heart_sound_recording(doctor_id, recording_data)
                except Exception as db_error:
                    print(f"⚠️ Failed to save recording: {db_error}")
                
            except Exception as audio_error:
                print(f"❌ Audio processing error: {str(audio_error)}")
                import traceback
                traceback.print_exc()
                # Return graceful error
                return jsonify({
                    'error': f'Audio processing failed: {str(audio_error)}',
                    'partial_success': True,
                    'patient_id': patient_id,
                    'triage': {
                        'level': triage_level,
                        'color': triage_color,
                        'score': triage_score
                    }
                }), 500
            finally:
                # Clean up temp file
                if 'filepath' in locals() and os.path.exists(filepath):
                    os.unlink(filepath)
                    print(f"🗑️ Temp file cleaned up")
        
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
        
        print("✅ Returning response")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Encounter error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def generate_recommendation(ml_result, triage_level, triage_color, rhd_detected):
    """Generate combined recommendation"""
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
        else:
            return {
                'priority': 'LOW',
                'message': '🔄 RHD suspected - Regular monitoring recommended',
                'action': 'Annual check-up with symptom monitoring',
                'timeline': 'Annual'
            }
    
    if triage_color in ['Red', 'Orange']:
        return {
            'priority': 'EMERGENCY',
            'message': '🏥 Emergency care required',
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
            'message': '✅ No immediate concerns',
            'action': 'Annual health check-up',
            'timeline': 'Annual'
        }