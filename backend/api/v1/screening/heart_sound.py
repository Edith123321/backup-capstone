# backend/api/v1/screening/heart_sound.py
import os
import sys

# Disable numba JIT to save memory
os.environ['NUMBA_DISABLE_JIT'] = '1'
os.environ['NUMBA_CACHE_DIR'] = '/tmp/numba_cache'

import uuid
import tempfile
import traceback
from flask import request, jsonify, Blueprint
from werkzeug.utils import secure_filename
import numpy as np
import pickle
import json
import warnings
import wave
warnings.filterwarnings('ignore')

# Try to import librosa
try:
    import librosa
    LIBROSA_AVAILABLE = True
    print(f"✅ librosa version: {librosa.__version__}")
except ImportError as e:
    print(f"⚠️ librosa import error: {e}")
    LIBROSA_AVAILABLE = False

# Try to import scipy
try:
    from scipy.signal import spectrogram
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# =========================
# FIND MODEL PATH - FIXED
# =========================

# Get the absolute path of this file
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)  # backend/api/v1/screening

# Go up to project root: backend/api/v1/screening -> backend/api/v1 -> backend/api -> backend -> project_root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))

MODEL_PATH = os.path.join(project_root, 'ai_model', 'models', 'mitral_classifier_v4')

print("=" * 50)
print("🔍 HEART SOUND CLASSIFIER INITIALIZATION")
print("=" * 50)
print(f"📁 Current file: {current_file}")
print(f"📁 Current dir: {current_dir}")
print(f"📁 Project root: {project_root}")
print(f"📁 Model path: {MODEL_PATH}")
print(f"📁 Path exists: {os.path.exists(MODEL_PATH)}")

if os.path.exists(MODEL_PATH):
    print(f"📁 Files in model path: {os.listdir(MODEL_PATH)}")
else:
    # Try alternative paths
    possible_paths = [
        '/opt/render/project/src/ai_model/models/mitral_classifier_v4',
        '/opt/render/project/src/ai_model/models/mitral_classifier_v4',
        os.path.join(os.getcwd(), 'ai_model', 'models', 'mitral_classifier_v4'),
        os.path.join(os.path.dirname(project_root), 'ai_model', 'models', 'mitral_classifier_v4'),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            MODEL_PATH = p
            print(f"✅ Found model at alternative path: {MODEL_PATH}")
            print(f"📁 Files: {os.listdir(MODEL_PATH)}")
            break
print("=" * 50)

# =========================
# FEATURE EXTRACTION
# =========================

def extract_features(filepath, target_sr=22050, duration=10):
    """Extract Mel-spectrogram features from audio file"""
    try:
        if LIBROSA_AVAILABLE:
            # Load audio
            y, sr = librosa.load(filepath, sr=target_sr, duration=duration)
            
            # If audio is too short, pad it
            if len(y) < target_sr * 2:
                print(f"⚠️ Audio too short ({len(y)/target_sr:.2f}s), padding...")
                y = np.pad(y, (0, target_sr * duration - len(y)))
            
            # Extract Mel-spectrogram
            n_mels = 128
            hop_length = 512
            n_fft = 2048
            
            mel_spec = librosa.feature.melspectrogram(
                y=y,
                sr=sr,
                n_mels=n_mels,
                n_fft=n_fft,
                hop_length=hop_length,
                fmax=8000
            )
            
            # Convert to log scale (dB)
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            
            # Flatten and ensure consistent length
            features = mel_spec_db.flatten()
            
            # Target length: 128 * 128 = 16384
            target_length = 128 * 128
            if len(features) < target_length:
                features = np.pad(features, (0, target_length - len(features)))
            else:
                features = features[:target_length]
            
            # Clean up
            del y, sr, mel_spec, mel_spec_db
            
            return features.reshape(1, -1)
        
        elif SCIPY_AVAILABLE:
            # Fallback using scipy
            with wave.open(filepath, 'rb') as wf:
                n_frames = wf.getnframes()
                framerate = wf.getframerate()
                
                max_frames = min(n_frames, int(framerate * duration))
                audio_data = wf.readframes(max_frames)
                
                if wf.getsampwidth() == 2:
                    dtype = np.int16
                else:
                    dtype = np.int16
                
                y = np.frombuffer(audio_data, dtype=dtype).astype(np.float32) / 32767.0
                
                f, t, Sxx = spectrogram(y, framerate, nperseg=256, noverlap=128)
                Sxx_db = 10 * np.log10(Sxx + 1e-10)
                
                from scipy.ndimage import zoom
                target_shape = (128, 128)
                zoom_factors = (target_shape[0] / Sxx_db.shape[0], target_shape[1] / Sxx_db.shape[1])
                features = zoom(Sxx_db, zoom_factors, order=1)
                
                return features.flatten().reshape(1, -1)
        else:
            print("❌ No audio processing library available")
            return None
            
    except MemoryError:
        print("❌ Memory error during feature extraction")
        return None
    except Exception as e:
        print(f"❌ Feature extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# =========================
# CLASSIFIER CLASS
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.sr = 22050
        self.classes = ['Normal', 'RHD']
        self.feature_names = None
        self.load_model()
    
    def load_model(self):
        """Load model and scaler"""
        try:
            model_file = os.path.join(self.model_path, 'best_model.pkl')
            scaler_file = os.path.join(self.model_path, 'scaler.pkl')
            
            print(f"📂 Loading model from: {model_file}")
            print(f"📂 Loading scaler from: {scaler_file}")
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                if hasattr(self.model, 'feature_names_in_'):
                    self.feature_names = self.model.feature_names_in_
                    print(f"📊 Feature count: {len(self.feature_names)}")
                
                print("✅ Model loaded successfully")
                return True
            else:
                print(f"❌ Model files not found")
                print(f"   best_model.pkl exists: {os.path.exists(model_file)}")
                print(f"   scaler.pkl exists: {os.path.exists(scaler_file)}")
                return False
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def predict(self, filepath, return_all=True):
        """Predict heart sound class"""
        try:
            if self.model is None or self.scaler is None:
                print("⚠️ Model not loaded")
                return None
            
            features = extract_features(filepath)
            if features is None:
                print("❌ Feature extraction failed")
                return None
            
            print(f"📊 Features shape: {features.shape}")
            
            try:
                features_scaled = self.scaler.transform(features)
                print(f"📊 Scaled features shape: {features_scaled.shape}")
            except Exception as e:
                print(f"❌ Scaling error: {e}")
                features_scaled = features
            
            prediction = self.model.predict(features_scaled)
            probabilities = self.model.predict_proba(features_scaled)
            
            if hasattr(self.model, 'classes_'):
                class_names = self.model.classes_
                if len(class_names) == 2:
                    pred_class = class_names[prediction[0]]
                    prob_normal = float(probabilities[0][0])
                    prob_rhd = float(probabilities[0][1])
                else:
                    pred_class = 'Normal' if prediction[0] == 0 else 'RHD'
                    prob_normal = float(probabilities[0][0]) if len(probabilities[0]) > 0 else 0
                    prob_rhd = float(probabilities[0][1]) if len(probabilities[0]) > 1 else 0
            else:
                pred_class = 'Normal' if prediction[0] == 0 else 'RHD'
                prob_normal = float(probabilities[0][0]) if len(probabilities[0]) > 0 else 0
                prob_rhd = float(probabilities[0][1]) if len(probabilities[0]) > 1 else 0
            
            print(f"✅ Prediction: {pred_class} (Normal: {prob_normal:.3f}, RHD: {prob_rhd:.3f})")
            
            if return_all:
                return {
                    'class': pred_class,
                    'confidence': float(max(probabilities[0])),
                    'prob_normal': prob_normal,
                    'prob_rhd': prob_rhd,
                    'probabilities': probabilities[0].tolist()
                }
            else:
                return pred_class
                
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_visualization(self, filepath):
        return None

# =========================
# BLUEPRINT SETUP
# =========================

heart_sound_bp = Blueprint('heart_sound', __name__, url_prefix='/api/v1/screening')

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize classifier
classifier = None
try:
    if os.path.exists(MODEL_PATH):
        model_file = os.path.join(MODEL_PATH, 'best_model.pkl')
        scaler_file = os.path.join(MODEL_PATH, 'scaler.pkl')
        if os.path.exists(model_file) and os.path.exists(scaler_file):
            classifier = HeartSoundClassifier(MODEL_PATH)
            print("✅ Classifier initialized successfully")
        else:
            print(f"❌ Model files missing")
            print(f"   best_model.pkl: {os.path.exists(model_file)}")
            print(f"   scaler.pkl: {os.path.exists(scaler_file)}")
    else:
        print(f"❌ Model path not found: {MODEL_PATH}")
except Exception as e:
    print(f"❌ Failed to initialize classifier: {e}")
    import traceback
    traceback.print_exc()

# =========================
# ROUTES
# =========================

@heart_sound_bp.route('/health', methods=['GET'])
def health():
    model_file = os.path.join(MODEL_PATH, 'best_model.pkl')
    scaler_file = os.path.join(MODEL_PATH, 'scaler.pkl')
    return jsonify({
        'status': 'healthy',
        'model_loaded': classifier is not None,
        'librosa_available': LIBROSA_AVAILABLE,
        'scipy_available': SCIPY_AVAILABLE,
        'model_path': MODEL_PATH,
        'model_files_exist': os.path.exists(model_file) and os.path.exists(scaler_file),
        'best_model_exists': os.path.exists(model_file),
        'scaler_exists': os.path.exists(scaler_file)
    })

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    try:
        if classifier is None:
            return jsonify({
                'error': 'Classifier not loaded',
                'model_loaded': False
            }), 503
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        print(f"🎵 Processing: {file.filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            file.save(tmp_file.name)
            filepath = tmp_file.name
        
        try:
            result = classifier.predict(filepath, return_all=True)
            
            if result is None:
                return jsonify({
                    'error': 'Failed to process audio file'
                }), 500
            
            response = {
                'success': True,
                'filename': file.filename,
                'prediction': result['class'],
                'confidence': result['confidence'],
                'probabilities': {
                    'Normal': result['prob_normal'],
                    'RHD': result['prob_rhd']
                }
            }
            
            print(f"✅ Returning prediction: {response['prediction']}")
            return jsonify(response)
            
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
                
    except MemoryError:
        print("❌ Memory error")
        return jsonify({'error': 'Insufficient memory'}), 503
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500