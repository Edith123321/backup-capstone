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
# FEATURE EXTRACTION
# =========================

def extract_features(filepath, target_sr=22050, duration=10):
    """
    Extract Mel-spectrogram features from audio file
    Returns feature vector for model
    """
    try:
        if LIBROSA_AVAILABLE:
            # Load audio
            y, sr = librosa.load(filepath, sr=target_sr, duration=duration)
            
            # If audio is too short, pad it
            if len(y) < target_sr * 2:  # Less than 2 seconds
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
            
            # Clean up to free memory
            del y, sr, mel_spec, mel_spec_db
            
            return features.reshape(1, -1)
        
        elif SCIPY_AVAILABLE:
            # Fallback using scipy
            with wave.open(filepath, 'rb') as wf:
                n_frames = wf.getnframes()
                framerate = wf.getframerate()
                
                # Read audio
                max_frames = min(n_frames, int(framerate * duration))
                audio_data = wf.readframes(max_frames)
                
                if wf.getsampwidth() == 2:
                    dtype = np.int16
                else:
                    dtype = np.int16
                
                y = np.frombuffer(audio_data, dtype=dtype).astype(np.float32) / 32767.0
                
                # Simple spectrogram
                f, t, Sxx = spectrogram(y, framerate, nperseg=256, noverlap=128)
                
                # Log scale
                Sxx_db = 10 * np.log10(Sxx + 1e-10)
                
                # Resize to 128x128
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
            
            print(f"🔍 Looking for model at: {model_file}")
            print(f"🔍 Looking for scaler at: {scaler_file}")
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                print(f"📂 Loading model...")
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                # Get feature names if available
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
            
            # Extract features
            features = extract_features(filepath)
            if features is None:
                print("❌ Feature extraction failed")
                return None
            
            print(f"📊 Features shape: {features.shape}")
            
            # Scale features
            try:
                features_scaled = self.scaler.transform(features)
                print(f"📊 Scaled features shape: {features_scaled.shape}")
            except Exception as e:
                print(f"❌ Scaling error: {e}")
                # Try without scaling if it fails
                features_scaled = features
            
            # Predict
            try:
                prediction = self.model.predict(features_scaled)
                probabilities = self.model.predict_proba(features_scaled)
                
                # Get class names
                if hasattr(self.model, 'classes_'):
                    class_names = self.model.classes_
                    if len(class_names) == 2:
                        # Map to our classes
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
                
        except Exception as e:
            print(f"❌ Predict error: {str(e)}")
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
    return jsonify({
        'status': 'healthy',
        'model_loaded': classifier is not None,
        'librosa_available': LIBROSA_AVAILABLE,
        'scipy_available': SCIPY_AVAILABLE,
        'model_path': MODEL_PATH,
        'model_files_exist': os.path.exists(os.path.join(MODEL_PATH, 'best_model.pkl')) if MODEL_PATH else False
    })

@heart_sound_bp.route('/info', methods=['GET'])
def info():
    if classifier is None:
        return jsonify({'error': 'Classifier not loaded'}), 503
    
    return jsonify({
        'model_type': type(classifier.model).__name__ if classifier.model else None,
        'classes': classifier.classes,
        'sample_rate': classifier.sr,
        'feature_names': classifier.feature_names[:10] if classifier.feature_names else None,
        'feature_count': len(classifier.feature_names) if classifier.feature_names else None
    })

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    """Predict heart sound from uploaded audio"""
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
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            file.save(tmp_file.name)
            filepath = tmp_file.name
        
        try:
            result = classifier.predict(filepath, return_all=True)
            
            if result is None:
                return jsonify({
                    'error': 'Failed to process audio file',
                    'message': 'Could not extract features from audio'
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
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': f'Prediction failed: {str(e)}'
            }), 500
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
                
    except MemoryError:
        print("❌ Memory error during prediction")
        return jsonify({'error': 'Insufficient memory for audio processing'}), 503
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500