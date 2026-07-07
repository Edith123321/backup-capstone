import os
import sys
import uuid
import tempfile
import traceback
import warnings
import numpy as np
import joblib 
from flask import request, jsonify, Blueprint
from werkzeug.utils import secure_filename

# Disable numba JIT to save memory on Render
os.environ['NUMBA_DISABLE_JIT'] = '1'
warnings.filterwarnings('ignore')

# Try to import librosa
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# =========================
# HELPER UTILS (Required by other routes)
# =========================
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# BLUEPRINT INITIALIZATION
# =========================
heart_sound_bp = Blueprint('heart_sound', __name__)

# =========================
# FIND MODEL PATH
# =========================
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
MODEL_PATH = os.path.join(project_root, 'ai_model', 'models', 'mitral_classifier_v4')

# =========================
# FEATURE EXTRACTION (ORDER-CRITICAL)
# =========================

def extract_features(filepath, sr=4000, duration=10.0):
    """
    Extracts features in the EXACT dictionary order of the training notebook.
    This ensures the array indices match the trained model's expectations.
    """
    try:
        if not LIBROSA_AVAILABLE:
            return None
            
        signal, _ = librosa.load(filepath, sr=sr, duration=duration)
        if len(signal) < 1000:
            return None

        features = {}
        
        # 1. Basic statistics
        features['mean'] = np.mean(signal)
        features['std'] = np.std(signal)
        features['rms'] = np.sqrt(np.mean(signal**2))
        features['peak'] = np.max(np.abs(signal))
        
        # 2. Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(signal)[0]
        features['zcr_mean'] = np.mean(zcr)
        features['zcr_std'] = np.std(zcr)
        
        # 3. Spectral features
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
        
        # 4. MFCC features 
        mfccs = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=13, n_fft=1024)
        for i in range(13):
            features[f'mfcc_{i}'] = np.mean(mfccs[i])
            features[f'mfcc_{i}_std'] = np.std(mfccs[i])
            
        # 5. Mel spectrogram summary
        mel_spec = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=64, n_fft=1024)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        features['mel_mean'] = np.mean(mel_spec_db)
        features['mel_std'] = np.std(mel_spec_db)
        features['mel_max'] = np.max(mel_spec_db)
        features['mel_energy'] = np.sum(mel_spec_db)
        
        # 6. Tempo
        try:
            tempo, _ = librosa.beat.beat_track(y=signal, sr=sr)
            features['tempo'] = float(tempo[0]) if isinstance(tempo, (np.ndarray, list)) else float(tempo)
        except:
            features['tempo'] = 0.0
            
        # 7. Envelope features
        envelope = np.abs(signal)
        envelope_smooth = np.convolve(envelope, np.ones(50)/50, mode='same')
        features['env_mean'] = np.mean(envelope_smooth)
        features['env_std'] = np.std(envelope_smooth)
        features['env_peak'] = np.max(envelope_smooth)
        features['env_peak_ratio'] = features['env_peak'] / (features['env_mean'] + 1e-8)
        
        # 8. Energy ratios
        fft = np.fft.rfft(signal)
        pow_freqs = np.fft.rfftfreq(len(signal), 1/sr)
        power = np.abs(fft)**2
        total_p = np.sum(power) + 1e-8
        for i, (low, high) in enumerate([(20, 80), (80, 200), (200, 400)]):
            mask = (pow_freqs >= low) & (pow_freqs < high)
            features[f'band_{i}_power'] = np.sum(power[mask]) / total_p

        # Return values in dict order (matches X_train columns)
        feature_vector = np.array([features[k] for k in features.keys()])
        return feature_vector.reshape(1, -1)
        
    except Exception as e:
        print(f"❌ Feature Extraction Error: {e}")
        return None

# =========================
# CLASSIFIER LOGIC
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_count = 0
        self.load_model()
    
    def load_model(self):
        try:
            m_file = os.path.join(self.model_path, 'best_model.pkl')
            s_file = os.path.join(self.model_path, 'scaler.pkl')
            
            if os.path.exists(m_file) and os.path.exists(s_file):
                self.model = joblib.load(m_file)
                self.scaler = joblib.load(s_file)
                self.feature_count = self.scaler.n_features_in_
                print(f"✅ Scaler & Model Loaded. Expecting {self.feature_count} features.")
                return True
            return False
        except Exception as e:
            print(f"❌ Model Load Error: {e}")
            return False

    def predict(self, filepath):
        if self.model is None or self.scaler is None:
            return None
            
        features = extract_features(filepath)
        if features is None:
            return None

        if features.shape[1] != self.feature_count:
            print(f"⚠️ Mismatch: Got {features.shape[1]}, Expected {self.feature_count}")
            return None

        features_scaled = self.scaler.transform(features)
        pred = self.model.predict(features_scaled)[0]
        prob = self.model.predict_proba(features_scaled)[0]
        
        return {
            'class': 'RHD' if pred == 1 else 'Normal',
            'confidence': float(np.max(prob)),
            'prob_normal': float(prob[0]),
            'prob_rhd': float(prob[1])
        }

# Global Instance
classifier = HeartSoundClassifier(MODEL_PATH)

# =========================
# ROUTES
# =========================

@heart_sound_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': classifier.model is not None,
        'feature_count': classifier.feature_count,
        'librosa_available': LIBROSA_AVAILABLE
    })

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    fd, path = tempfile.mkstemp(suffix='.wav')
    try:
        with os.fdopen(fd, 'wb') as tmp:
            file.save(tmp)
        
        result = classifier.predict(path)
        
        if result is None:
            return jsonify({'error': 'Prediction failed', 'message': 'Feature extraction error'}), 500
            
        return jsonify({
            'success': True,
            'prediction': result['class'],
            'confidence': result['confidence'],
            'probabilities': {
                'Normal': result['prob_normal'],
                'RHD': result['prob_rhd']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(path):
            os.remove(path)