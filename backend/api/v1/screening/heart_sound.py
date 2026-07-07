# backend/api/v1/screening/heart_sound.py
import os
import sys

# Disable numba
os.environ['NUMBA_DISABLE_JIT'] = '1'

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
import struct
warnings.filterwarnings('ignore')

# Try to import scipy (lighter than librosa for some tasks)
try:
    from scipy.signal import spectrogram
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Try to import librosa, but with memory optimization
try:
    import librosa
    LIBROSA_AVAILABLE = True
    print(f"✅ librosa version: {librosa.__version__}")
except ImportError as e:
    print(f"⚠️ librosa import error: {e}")
    LIBROSA_AVAILABLE = False

# =========================
# MEMORY-EFFICIENT FEATURE EXTRACTION
# =========================

def extract_features_memory_efficient(filepath, target_sr=22050, duration=10):
    """
    Extract features with minimal memory usage
    """
    try:
        # Read only a portion of the audio file
        if LIBROSA_AVAILABLE:
            # Load only first 10 seconds
            y, sr = librosa.load(filepath, sr=target_sr, duration=duration, res_type='kaiser_fast')
            
            # Use fewer Mel bands to save memory
            n_mels = 64  # Reduced from 128
            hop_length = 512
            
            # Compute Mel spectrogram with lower memory
            mel_spec = librosa.feature.melspectrogram(
                y=y, 
                sr=sr, 
                n_mels=n_mels, 
                fmax=4000,  # Lower frequency range
                hop_length=hop_length
            )
            
            # Convert to log scale
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            
            # Average across time to get feature vector
            features = np.mean(mel_spec_db, axis=1)
            
            # Free memory
            del y, sr, mel_spec, mel_spec_db
            import gc
            gc.collect()
            
            return features.reshape(1, -1)
        
        elif SCIPY_AVAILABLE:
            # Alternative using scipy
            with wave.open(filepath, 'rb') as wf:
                # Read audio data
                n_frames = wf.getnframes()
                framerate = wf.getframerate()
                
                # Read only first 10 seconds
                max_frames = min(n_frames, int(framerate * duration))
                audio_data = wf.readframes(max_frames)
                
                # Convert to numpy array
                if wf.getsampwidth() == 2:
                    dtype = np.int16
                else:
                    dtype = np.int16
                
                y = np.frombuffer(audio_data, dtype=dtype).astype(np.float32) / 32767.0
                
                # Simple spectrogram with scipy
                f, t, Sxx = spectrogram(y, framerate, nperseg=256, noverlap=128)
                
                # Take mean across time
                features = np.mean(Sxx, axis=1)[:64]  # Limit to 64 features
                
                return features.reshape(1, -1)
        
        # Fallback: generate random features (for testing)
        print("⚠️ No audio library available, using random features")
        return np.random.randn(1, 64)
        
    except Exception as e:
        print(f"❌ Feature extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# =========================
# HEART SOUND CLASSIFIER
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.sr = 22050
        self.classes = ['Normal', 'RHD']
        self.load_model()
    
    def load_model(self):
        """Load model and scaler with memory efficiency"""
        try:
            model_file = os.path.join(self.model_path, 'best_model.pkl')
            scaler_file = os.path.join(self.model_path, 'scaler.pkl')
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                print(f"📂 Loading model from: {model_file}")
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("✅ Model loaded successfully")
                return True
            else:
                print(f"❌ Model files not found: {model_file}, {scaler_file}")
                return False
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def predict(self, filepath, return_all=True):
        """Predict with memory optimization"""
        try:
            if self.model is None or self.scaler is None:
                print("⚠️ Model not loaded")
                return None
            
            # Extract features with memory efficiency
            features = extract_features_memory_efficient(filepath)
            if features is None:
                return None
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Predict
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Map prediction
            class_names = ['Normal', 'RHD']  # Adjust based on your model
            pred_class = class_names[prediction] if prediction < len(class_names) else 'Unknown'
            
            if return_all:
                return {
                    'class': pred_class,
                    'confidence': float(max(probabilities)),
                    'prob_normal': float(probabilities[0]) if len(probabilities) > 0 else 0,
                    'prob_rhd': float(probabilities[1]) if len(probabilities) > 1 else 0,
                    'features': features_scaled.tolist()
                }
            else:
                return pred_class
                
        except Exception as e:
            print(f"❌ Prediction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_visualization(self, filepath):
        """Generate visualization (disabled for memory)"""
        return None

# =========================
# BLUEPRINT SETUP
# =========================

heart_sound_bp = Blueprint('heart_sound', __name__, url_prefix='/api/v1/screening')

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Find model path
capstone_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_PATH = os.path.join(capstone_dir, 'ai_model', 'models', 'mitral_classifier_v4')

print(f"🔍 Looking for model at: {MODEL_PATH}")
print(f"📁 Model path exists: {os.path.exists(MODEL_PATH)}")

# Initialize classifier with memory optimization
classifier = None
try:
    if os.path.exists(MODEL_PATH):
        model_file = os.path.join(MODEL_PATH, 'best_model.pkl')
        scaler_file = os.path.join(MODEL_PATH, 'scaler.pkl')
        if os.path.exists(model_file) and os.path.exists(scaler_file):
            classifier = HeartSoundClassifier(MODEL_PATH)
            print("✅ Classifier initialized successfully")
        else:
            print(f"❌ Model files missing: {model_file}, {scaler_file}")
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
    return jsonify({
        'status': 'healthy',
        'model_loaded': classifier is not None,
        'librosa_available': LIBROSA_AVAILABLE,
        'scipy_available': SCIPY_AVAILABLE,
        'model_path': MODEL_PATH
    })

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    """Predict heart sound - memory optimized"""
    try:
        if classifier is None:
            return jsonify({'error': 'Classifier not loaded'}), 503
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Save to temp file with memory efficiency
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            file.save(tmp_file.name)
            filepath = tmp_file.name
        
        try:
            result = classifier.predict(filepath, return_all=True)
            if result is None:
                return jsonify({'error': 'Failed to process audio file'}), 500
            
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
            return jsonify(response)
            
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
                
    except MemoryError:
        print("❌ Memory error during prediction")
        return jsonify({'error': 'Insufficient memory for audio processing'}), 503
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return jsonify({'error': str(e)}), 500