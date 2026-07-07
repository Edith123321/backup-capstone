# backend/api/v1/screening/heart_sound.py
import os
import sys
import tempfile
import warnings
import numpy as np
import joblib 
import traceback
from flask import request, jsonify, Blueprint, make_response
from scipy.io import wavfile
import soundfile as sf  # More reliable than librosa for loading
from datetime import datetime

# COMPLETELY DISABLE NUMBA - ENSURE IT NEVER LOADS
os.environ['NUMBA_DISABLE_JIT'] = '1'
os.environ['NUMBA_ENABLE_AVX'] = '0'  # Disable AVX optimizations
warnings.filterwarnings('ignore')

# =========================
# CONFIG & PATHS
# =========================
heart_sound_bp = Blueprint('heart_sound', __name__)
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
MODEL_PATH = os.path.join(project_root, 'ai_model', 'models', 'mitral_classifier_v4')

# =========================
# CORS HELPER FUNCTIONS
# =========================
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

# =========================
# SAFE AUDIO LOADING (NO LIBROSA)
# =========================

def load_audio_safe(filepath, target_sr=4000, duration=10.0):
    """Load audio without librosa to avoid Numba"""
    try:
        # Try soundfile first (supports many formats)
        try:
            y, sr = sf.read(filepath)
        except:
            # Fallback to scipy for WAV files
            sr, y = wavfile.read(filepath)
            if y.dtype == np.int16:
                y = y.astype(np.float32) / 32768.0
            elif y.dtype == np.int32:
                y = y.astype(np.float32) / 2147483648.0
        
        # Ensure mono
        if len(y.shape) > 1:
            y = np.mean(y, axis=1)
        
        # Resample if needed (simple interpolation)
        if sr != target_sr:
            from scipy import signal
            # Calculate number of samples for target duration
            target_len = int(target_sr * min(duration, len(y) / sr))
            # Resample using scipy
            y = signal.resample(y, target_len)
            sr = target_sr
        
        # Trim to duration
        max_samples = int(target_sr * duration)
        if len(y) > max_samples:
            y = y[:max_samples]
        
        return y, sr
    
    except Exception as e:
        print(f"❌ Audio loading error: {str(e)}")
        return None, None

# =========================
# THE "STRICT 51" EXTRACTOR (Numba-Safe)
# =========================
# Feature extraction is delegated to feature_extraction.py, a pure NumPy/SciPy
# port of the librosa pipeline the model was trained on (ai_model/src/classifier.py).
# It reproduces all 51 features — including the 26 MFCCs, mel summary and ZCR std
# that the previous inline extractor left as zeros — validated to 100% prediction
# parity with librosa on real recordings, without importing numba.
try:
    from feature_extraction import extract_feature_vector
except ImportError:
    from api.v1.screening.feature_extraction import extract_feature_vector


def extract_features(filepath, sr=4000, duration=10.0):
    try:
        y, actual_sr = load_audio_safe(filepath, target_sr=sr, duration=duration)
        if y is None or len(y) < 1000:
            print(f"❌ Invalid audio: length {len(y) if y is not None else 'None'}")
            return None
        return extract_feature_vector(y, sr=sr)
    except Exception as e:
        print(f"❌ Extraction Error: {str(e)}")
        traceback.print_exc()
        return None


# =========================
# CLASSIFIER CLASS
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        try:
            # Load with error handling
            self.model = joblib.load(os.path.join(model_path, 'best_model.pkl'))
            self.scaler = joblib.load(os.path.join(model_path, 'scaler.pkl'))
            print(f"✅ Model loaded successfully from {model_path}")
        except Exception as e:
            print(f"❌ Failed to load model: {str(e)}")
            raise

    def predict(self, filepath):
        features = extract_features(filepath)
        if features is None:
            return None
        
        try:
            features_scaled = self.scaler.transform(features)
            pred = self.model.predict(features_scaled)[0]
            prob = self.model.predict_proba(features_scaled)[0]
            return {
                'class': 'RHD' if pred == 1 else 'Normal',
                'confidence': float(np.max(prob)),
                'prob_normal': float(prob[0]) if len(prob) > 0 else 0,
                'prob_rhd': float(prob[1]) if len(prob) > 1 else 0
            }
        except Exception as e:
            print(f"❌ Prediction error: {str(e)}")
            traceback.print_exc()
            return None

# Initialize classifier
try:
    classifier = HeartSoundClassifier(MODEL_PATH)
except Exception as e:
    print(f"❌ Failed to initialize classifier: {str(e)}")
    classifier = None

# =========================
# HELPER FUNCTIONS
# =========================

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

# =========================
# ROUTES
# =========================

@heart_sound_bp.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return handle_options()
    
    return create_cors_response({
        'status': 'healthy' if classifier else 'error',
        'model_loaded': classifier is not None,
        'feature_count': 51,
        'timestamp': datetime.now().isoformat()
    })


@heart_sound_bp.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return handle_options()
    
    if not classifier:
        return create_cors_response({'error': 'Classifier not initialized'}, 500)
    
    if 'file' not in request.files:
        return create_cors_response({'error': 'No file uploaded'}, 400)
    
    file = request.files['file']
    if file.filename == '':
        return create_cors_response({'error': 'No file selected'}, 400)
    
    tmp_path = None
    try:
        # Get parameters from request
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        auscultation_point = request.form.get('auscultation_point')
        auscultation_label = request.form.get('auscultation_label')
        
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Predict
        result = classifier.predict(tmp_path)
        if result is None:
            return create_cors_response({'error': 'Prediction failed - invalid audio or feature extraction'}, 500)
        
        # Get severity grade
        severity = get_severity_grade(
            prediction=result['class'],
            confidence=result['confidence'],
            auscultation_point=auscultation_point
        )
        
        # Save recording to database if patient_id and doctor_id provided
        recording_id = None
        if patient_id and doctor_id:
            try:
                from services.database import db
                recording_data = {
                    'doctor_id': doctor_id,
                    'patient_id': patient_id,
                    'file': file,
                    'prediction': result['class'],
                    'confidence': result['confidence'],
                    'recording_date': request.form.get('recording_date'),
                    'notes': request.form.get('notes', ''),
                    'severity_grade': severity.get('grade', 0),
                    'severity_label': severity.get('label', 'Unknown'),
                    'auscultation_point': auscultation_point,
                    'auscultation_label': auscultation_label
                }
                recording_id = db.save_heart_sound_recording(doctor_id, recording_data)
                print(f"✅ Recording saved with ID: {recording_id}")
                
                # Update patient RHD status based on prediction
                if patient_id and result['class']:
                    try:
                        db.update_patient_rhd_from_prediction(
                            patient_id, 
                            result['class'], 
                            result['confidence']
                        )
                        print(f"✅ Updated RHD status for patient {patient_id}")
                    except Exception as e:
                        print(f"⚠️ Failed to update RHD status: {e}")
                        
            except Exception as e:
                print(f"⚠️ Failed to save recording: {str(e)}")
        
        # Return with consistent field names
        return create_cors_response({
            'success': True,
            'prediction': result['class'],
            'confidence': result['confidence'],
            'prob_normal': result.get('prob_normal', 0),
            'prob_rhd': result.get('prob_rhd', 0),
            'recording_id': recording_id,
            'severity': severity,
            'auscultation_point': auscultation_point,
            'auscultation_label': auscultation_label
        })
        
    except Exception as e:
        print(f"❌ Route error: {str(e)}")
        traceback.print_exc()
        return create_cors_response({'error': f'Server error: {str(e)}'}, 500)
        
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


@heart_sound_bp.route('/save-recording', methods=['POST', 'OPTIONS'])
def save_recording():
    """Save a recording to the database with prediction results"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        data = request.json
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        
        if not patient_id or not doctor_id:
            return create_cors_response({'error': 'patient_id and doctor_id required'}, 400)
        
        from services.database import db
        
        recording_data = {
            'doctor_id': doctor_id,
            'patient_id': patient_id,
            'prediction': data.get('prediction'),
            'confidence': data.get('confidence'),
            'file_url': data.get('file_url'),
            'recording_date': data.get('recording_date'),
            'notes': data.get('notes', ''),
            'severity_grade': data.get('severity_grade', 0),
            'severity_label': data.get('severity_label', 'Unknown'),
            'auscultation_point': data.get('auscultation_point'),
            'auscultation_label': data.get('auscultation_label')
        }
        
        recording_id = db.save_heart_sound_recording(doctor_id, recording_data)
        
        if recording_id:
            return create_cors_response({
                'success': True,
                'recording_id': recording_id,
                'message': 'Recording saved successfully'
            })
        
        return create_cors_response({'error': 'Failed to save recording'}, 500)
        
    except Exception as e:
        print(f"❌ Error saving recording: {str(e)}")
        return create_cors_response({'error': str(e)}, 500)


@heart_sound_bp.route('/recordings/<patient_id>', methods=['GET', 'OPTIONS'])
def get_patient_recordings(patient_id):
    """Get all recordings for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        from services.database import db
        recordings = db.get_recordings_by_patient(patient_id)
        
        return create_cors_response({
            'success': True,
            'recordings': recordings,
            'count': len(recordings)
        })
        
    except Exception as e:
        print(f"❌ Error fetching recordings: {str(e)}")
        return create_cors_response({'error': str(e)}, 500)


@heart_sound_bp.route('/recordings/<recording_id>', methods=['DELETE', 'OPTIONS'])
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


@heart_sound_bp.route('/validate', methods=['POST', 'OPTIONS'])
def validate_heart_sound():
    """Validate a heart sound file before full analysis"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        if 'file' not in request.files:
            return create_cors_response({'error': 'No file uploaded'}, 400)
        
        file = request.files['file']
        if file.filename == '':
            return create_cors_response({'error': 'No file selected'}, 400)
        
        # Validate file size (max 25MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 25 * 1024 * 1024:  # 25MB
            return create_cors_response({
                'valid': False,
                'error': 'File too large (max 25MB)'
            }, 400)
        
        # Validate file extension
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return create_cors_response({
                'valid': False,
                'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }, 400)
        
        # Try to load audio to validate
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            y, sr = load_audio_safe(tmp_path)
            if y is None or len(y) < 1000:
                return create_cors_response({
                    'valid': False,
                    'error': 'Invalid audio file or too short'
                }, 400)
            
            return create_cors_response({
                'valid': True,
                'duration': len(y) / sr,
                'sample_rate': sr,
                'samples': len(y),
                'message': 'Audio file validated successfully'
            })
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return create_cors_response({'error': str(e)}, 500)


@heart_sound_bp.route('/history/<patient_id>', methods=['GET', 'OPTIONS'])
def get_screening_history(patient_id):
    """Get screening history for a patient"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    try:
        from services.database import db
        recordings = db.get_recordings_by_patient(patient_id)
        triage = db.get_triage_by_patient(patient_id)
        
        # Combine and sort by date
        history = []
        
        for rec in recordings:
            history.append({
                'type': 'recording',
                'id': rec.get('id'),
                'date': rec.get('recording_date') or rec.get('created_at'),
                'prediction': rec.get('prediction'),
                'confidence': rec.get('confidence'),
                'severity_grade': rec.get('severity_grade'),
                'severity_label': rec.get('severity_label'),
                'auscultation_point': rec.get('auscultation_point')
            })
        
        for tri in triage:
            history.append({
                'type': 'triage',
                'id': tri.get('id'),
                'date': tri.get('created_at'),
                'triage_color': tri.get('triage_color'),
                'triage_level': tri.get('triage_level'),
                'triage_score': tri.get('triage_score')
            })
        
        # Sort by date descending
        history.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return create_cors_response({
            'success': True,
            'history': history,
            'total': len(history),
            'patient_id': patient_id
        })
        
    except Exception as e:
        print(f"❌ Error fetching history: {str(e)}")
        return create_cors_response({'error': str(e)}, 500)


@heart_sound_bp.route('/info', methods=['GET', 'OPTIONS'])
def get_model_info():
    """Get information about the AI model"""
    if request.method == 'OPTIONS':
        return handle_options()
    
    return create_cors_response({
        'model_loaded': classifier is not None,
        'feature_count': 51,
        'model_path': MODEL_PATH,
        'supported_formats': ['.wav', '.mp3', '.m4a', '.flac'],
        'sample_rate': 4000,
        'duration': 10.0,
        'features': [
            'Basic Stats (4)',
            'ZCR (2)',
            'Spectral (7)',
            'MFCCs (26)',
            'Mel (4)',
            'Tempo (1)',
            'Envelope (4)',
            'Band Power (3)'
        ]
    })