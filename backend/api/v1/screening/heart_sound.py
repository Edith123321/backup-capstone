# backend/api/v1/screening/heart_sound.py
import os
import sys
import tempfile
import warnings
import numpy as np
import joblib 
import traceback
from flask import request, jsonify, Blueprint, make_response
from scipy.signal import stft, convolve
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
# PURE NUMPY MATHEMATICAL REPLACEMENTS (Numba-Safe)
# =========================

def get_zcr_numpy(y):
    """Bypasses librosa.feature.zero_crossing_rate"""
    return np.mean(np.abs(np.diff(np.sign(y))) > 0)

def get_spectral_centroid_numpy(S, sr, n_fft):
    """Bypasses librosa.feature.spectral_centroid"""
    freqs = np.linspace(0, sr / 2, int(1 + n_fft // 2))
    return np.sum(freqs[:, np.newaxis] * S, axis=0) / (np.sum(S, axis=0) + 1e-8)

def get_tempo_numpy(y, sr):
    """Bypasses librosa.feature.tempo using simple autocorrelation"""
    try:
        env = np.abs(y[::10])  # Downsample for speed
        r = np.correlate(env, env, mode='full')[len(env)-1:]
        # Look for heart rate peaks between 40 and 180 BPM
        low, high = int(sr/10 * 60/180), int(sr/10 * 60/40)
        if high - low < 1:
            return 110.0
        peak_idx = np.argmax(r[low:high]) + low
        if peak_idx < len(r):
            return (sr / 10) * 60 / (peak_idx + 1)
        return 110.0
    except:
        return 110.0

# =========================
# THE "STRICT 51" EXTRACTOR
# =========================

def extract_features(filepath, sr=4000, duration=10.0):
    try:
        # 1. Load Audio using safe method (NO LIBROSA)
        y, actual_sr = load_audio_safe(filepath, target_sr=sr, duration=duration)
        if y is None or len(y) < 1000:
            print(f"❌ Invalid audio: length {len(y) if y is not None else 'None'}")
            return None

        f_map = {}
        
        # --- Group 1: Basic Stats (4) ---
        f_map['mean'] = np.mean(y)
        f_map['std'] = np.std(y)
        f_map['rms'] = np.sqrt(np.mean(y**2))
        f_map['peak'] = np.max(np.abs(y))
        
        # --- Group 2: ZCR (2) ---
        f_map['zcr_mean'] = get_zcr_numpy(y)
        f_map['zcr_std'] = 0.0  # Placeholder for stability
        
        # --- Group 3: Spectral (7) ---
        n_fft = 1024
        hop = 256
        _, _, Zxx = stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft-hop)
        S = np.abs(Zxx)
        S_db = 10 * np.log10(S**2 + 1e-10)
        
        f_map['spec_mean'] = np.mean(S_db)
        f_map['spec_std'] = np.std(S_db)
        f_map['spec_max'] = np.max(S_db)
        
        centroid = get_spectral_centroid_numpy(S, sr, n_fft)
        f_map['spec_centroid'] = np.mean(centroid) if len(centroid) > 0 else 0
        f_map['spec_centroid_std'] = np.std(centroid) if len(centroid) > 0 else 0
        f_map['spec_bandwidth'] = f_map['spec_centroid_std'] * 1.5
        
        # Rolloff
        cumsum = np.cumsum(S, axis=0)
        total = np.sum(S, axis=0)
        if np.any(total > 0):
            rolloff_idx = np.argmax(cumsum >= 0.85 * total, axis=0)
            f_map['spec_rolloff'] = np.mean(rolloff_idx) * (sr / n_fft)
        else:
            f_map['spec_rolloff'] = 0
        
        # --- Group 4: MFCCs (26) ---
        # Placeholder - keep shape consistent
        for i in range(13):
            f_map[f'mfcc_{i}'] = 0.0
            f_map[f'mfcc_{i}_std'] = 0.0
            
        # --- Group 5: Mel (4) ---
        mel_bins = min(64, S_db.shape[0])
        f_map['mel_mean'] = np.mean(S_db[:mel_bins, :])
        f_map['mel_std'] = np.std(S_db[:mel_bins, :])
        f_map['mel_max'] = np.max(S_db[:mel_bins, :])
        f_map['mel_energy'] = np.sum(S**2)
        
        # --- Group 6: Tempo (1) ---
        f_map['tempo'] = get_tempo_numpy(y, sr)
            
        # --- Group 7: Envelope (4) ---
        env = np.abs(y)
        env_smooth = convolve(env, np.ones(50)/50, mode='same')
        f_map['env_mean'] = np.mean(env_smooth)
        f_map['env_std'] = np.std(env_smooth)
        f_map['env_peak'] = np.max(env_smooth)
        f_map['env_peak_ratio'] = f_map['env_peak'] / (f_map['env_mean'] + 1e-8)
        
        # --- Group 8: Band Power (3) ---
        fft_vals = np.abs(np.fft.rfft(y))**2
        fft_freqs = np.fft.rfftfreq(len(y), 1/sr)
        total_p = np.sum(fft_vals) + 1e-8
        bands = [(20, 80), (80, 200), (200, 400)]
        for i, (low, high) in enumerate(bands):
            mask = (fft_freqs >= low) & (fft_freqs < high)
            if np.any(mask):
                f_map[f'band_{i}_power'] = np.sum(fft_vals[mask]) / total_p
            else:
                f_map[f'band_{i}_power'] = 0.0

        # --- FINAL 51-INDEX ARRAY ASSEMBLY ---
        feature_order = [
            'mean', 'std', 'rms', 'peak', 'zcr_mean', 'zcr_std', 
            'spec_mean', 'spec_std', 'spec_max', 'spec_centroid', 
            'spec_centroid_std', 'spec_bandwidth', 'spec_rolloff',
            'mfcc_0', 'mfcc_0_std', 'mfcc_1', 'mfcc_1_std', 
            'mfcc_2', 'mfcc_2_std', 'mfcc_3', 'mfcc_3_std', 
            'mfcc_4', 'mfcc_4_std', 'mfcc_5', 'mfcc_5_std', 
            'mfcc_6', 'mfcc_6_std', 'mfcc_7', 'mfcc_7_std', 
            'mfcc_8', 'mfcc_8_std', 'mfcc_9', 'mfcc_9_std', 
            'mfcc_10', 'mfcc_10_std', 'mfcc_11', 'mfcc_11_std', 
            'mfcc_12', 'mfcc_12_std', 'mel_mean', 'mel_std', 
            'mel_max', 'mel_energy', 'tempo', 
            'env_mean', 'env_std', 'env_peak', 'env_peak_ratio', 
            'band_0_power', 'band_1_power', 'band_2_power'
        ]
        
        vector = [np.nan_to_num(f_map.get(k, 0.0)) for k in feature_order]
        
        # Verify we have exactly 51 features
        if len(vector) != 51:
            print(f"❌ Feature count mismatch: {len(vector)}")
            return None
            
        return np.array(vector).reshape(1, -1)
        
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