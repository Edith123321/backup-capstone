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

# =========================
# FIND MODEL PATH
# =========================

current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
MODEL_PATH = os.path.join(project_root, 'ai_model', 'models', 'mitral_classifier_v4')

print("=" * 50)
print("🔍 HEART SOUND CLASSIFIER INITIALIZATION")
print("=" * 50)
print(f"📁 Model path: {MODEL_PATH}")
print(f"📁 Path exists: {os.path.exists(MODEL_PATH)}")

if os.path.exists(MODEL_PATH):
    print(f"📁 Files: {os.listdir(MODEL_PATH)}")
print("=" * 50)

# =========================
# FEATURE EXTRACTION - MATCHING TRAINING CODE
# =========================

def extract_features(filepath, sr=4000, duration=10.0):
    """
    Extract features matching the training code's HeartSoundFeatureExtractor
    This extracts the ~45 features used in training
    """
    try:
        print(f"🎵 Extracting features from: {filepath}")
        
        # Check file exists
        if not os.path.exists(filepath):
            print("❌ File not found")
            return None
        
        # Load audio (matching training: sr=4000, duration=10)
        try:
            signal, _ = librosa.load(filepath, sr=sr, duration=duration, res_type='kaiser_fast')
            print(f"✅ Loaded: {len(signal)} samples, {len(signal)/sr:.2f}s")
        except Exception as e:
            print(f"❌ Failed to load audio: {e}")
            return None
        
        # Check if audio is valid
        if len(signal) < 1000:
            print(f"❌ Audio too short: {len(signal)} samples")
            return None
        
        features = {}
        
        # 1. Basic statistics
        features['mean'] = np.mean(signal)
        features['std'] = np.std(signal)
        features['rms'] = np.sqrt(np.mean(signal**2))
        features['peak'] = np.max(np.abs(signal))
        
        # 2. Zero crossing rate
        try:
            zcr = librosa.feature.zero_crossing_rate(signal)[0]
            features['zcr_mean'] = np.mean(zcr)
            features['zcr_std'] = np.std(zcr)
        except:
            features['zcr_mean'] = 0
            features['zcr_std'] = 0
        
        # 3. Spectral features
        try:
            spec = np.abs(librosa.stft(signal, n_fft=1024, hop_length=256))
            spec_db = librosa.amplitude_to_db(spec, ref=np.max)
            
            features['spec_mean'] = np.mean(spec_db)
            features['spec_std'] = np.std(spec_db)
            features['spec_max'] = np.max(spec_db)
            
            freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
            centroid = np.sum(freqs[:, None] * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8)
            features['spec_centroid'] = np.mean(centroid)
            features['spec_centroid_std'] = np.std(centroid)
            
            bandwidth = np.sqrt(np.sum((freqs[:, None] - centroid[None, :])**2 * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8))
            features['spec_bandwidth'] = np.mean(bandwidth)
            
            cumsum = np.cumsum(spec, axis=0)
            rolloff = np.argmax(cumsum >= 0.85 * cumsum[-1, :], axis=0)
            features['spec_rolloff'] = np.mean(rolloff) * sr / 1024
        except:
            features['spec_mean'] = 0
            features['spec_std'] = 0
            features['spec_max'] = 0
            features['spec_centroid'] = 0
            features['spec_centroid_std'] = 0
            features['spec_bandwidth'] = 0
            features['spec_rolloff'] = 0
        
        # 4. MFCC features (13 coefficients with mean and std)
        try:
            mfccs = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=13, n_fft=1024)
            for i in range(13):
                features[f'mfcc_{i}'] = np.mean(mfccs[i])
                features[f'mfcc_{i}_std'] = np.std(mfccs[i])
        except:
            for i in range(13):
                features[f'mfcc_{i}'] = 0
                features[f'mfcc_{i}_std'] = 0
        
        # 5. Mel spectrogram summary
        try:
            mel_spec = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=64, n_fft=1024)
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            features['mel_mean'] = np.mean(mel_spec_db)
            features['mel_std'] = np.std(mel_spec_db)
            features['mel_max'] = np.max(mel_spec_db)
            features['mel_energy'] = np.sum(mel_spec_db)
        except:
            features['mel_mean'] = 0
            features['mel_std'] = 0
            features['mel_max'] = 0
            features['mel_energy'] = 0
        
        # 6. Tempo
        try:
            tempo, _ = librosa.beat.beat_track(y=signal, sr=sr)
            features['tempo'] = float(tempo) if isinstance(tempo, np.ndarray) else tempo
        except:
            features['tempo'] = 0
        
        # 7. Envelope features
        try:
            envelope = np.abs(signal)
            envelope_smooth = np.convolve(envelope, np.ones(50)/50, mode='same')
            features['env_mean'] = np.mean(envelope_smooth)
            features['env_std'] = np.std(envelope_smooth)
            features['env_peak'] = np.max(envelope_smooth)
            features['env_peak_ratio'] = features['env_peak'] / (features['env_mean'] + 1e-8)
        except:
            features['env_mean'] = 0
            features['env_std'] = 0
            features['env_peak'] = 0
            features['env_peak_ratio'] = 0
        
        # 8. Energy ratios (different frequency bands)
        try:
            fft = np.fft.rfft(signal)
            freqs = np.fft.rfftfreq(len(signal), 1/sr)
            power = np.abs(fft)**2
            
            bands = [(20, 80), (80, 200), (200, 400)]
            total_power = np.sum(power) + 1e-8
            
            for i, (low, high) in enumerate(bands):
                mask = (freqs >= low) & (freqs < high)
                features[f'band_{i}_power'] = np.sum(power[mask]) / total_power
        except:
            for i in range(3):
                features[f'band_{i}_power'] = 0
        
        # Convert to numpy array in the correct order
        feature_names = sorted(features.keys())
        feature_vector = np.array([features[name] for name in feature_names])
        
        print(f"✅ Extracted {len(feature_vector)} features")
        
        return feature_vector.reshape(1, -1)
        
    except MemoryError:
        print("❌ Memory error during feature extraction")
        return None
    except Exception as e:
        print(f"❌ Feature extraction error: {e}")
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
        self.sr = 4000  # Matching training
        self.classes = ['Normal', 'RHD']
        self.feature_count = None
        self.load_model()
    
    def load_model(self):
        """Load model and scaler"""
        try:
            model_file = os.path.join(self.model_path, 'best_model.pkl')
            scaler_file = os.path.join(self.model_path, 'scaler.pkl')
            
            print(f"📂 Loading model from: {model_file}")
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                # Get feature count from model
                if hasattr(self.model, 'n_features_in_'):
                    self.feature_count = self.model.n_features_in_
                    print(f"📊 Model expects {self.feature_count} features")
                
                print("✅ Model loaded successfully")
                return True
            else:
                print(f"❌ Model files not found")
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
            
            print(f"📊 Extracted features shape: {features.shape}")
            
            # Check feature count matches model
            if self.feature_count and features.shape[1] != self.feature_count:
                print(f"⚠️ Feature count mismatch: {features.shape[1]} vs {self.feature_count}")
                if features.shape[1] < self.feature_count:
                    features = np.pad(features, ((0, 0), (0, self.feature_count - features.shape[1])))
                else:
                    features = features[:, :self.feature_count]
                print(f"📊 Adjusted shape: {features.shape}")
            
            # Scale features
            try:
                features_scaled = self.scaler.transform(features)
                print(f"📊 Scaled features shape: {features_scaled.shape}")
            except Exception as e:
                print(f"❌ Scaling error: {e}")
                features_scaled = features
            
            # Predict
            try:
                prediction = self.model.predict(features_scaled)
                probabilities = self.model.predict_proba(features_scaled)
                
                print(f"✅ Prediction: {prediction[0]}")
                print(f"✅ Probabilities: {probabilities[0]}")
                
                # Map to class names
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
                
                print(f"🎯 Final: {pred_class} (Normal: {prob_normal:.3f}, RHD: {prob_rhd:.3f})")
                
                if return_all:
                    return {
                        'class': pred_class,
                        'confidence': float(max(probabilities[0])),
                        'prob_normal': prob_normal,
                        'prob_rhd': prob_rhd
                    }
                else:
                    return pred_class
                    
            except Exception as pred_error:
                print(f"❌ Prediction error: {pred_error}")
                import traceback
                traceback.print_exc()
                return None
                
        except Exception as e:
            print(f"❌ Predict error: {str(e)}")
            import traceback
            traceback.print_exc()
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
        'model_path': MODEL_PATH,
        'model_files_exist': os.path.exists(model_file) and os.path.exists(scaler_file),
        'feature_count': classifier.feature_count if classifier else None
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
                    'message': 'Feature extraction or prediction failed'
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
                'error': 'Prediction failed',
                'details': str(e)
            }), 500
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