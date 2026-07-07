import os
import sys
import tempfile
import warnings
import numpy as np
import joblib 
from flask import request, jsonify, Blueprint

# FORCE NUMBA OFF to fix the 'get_call_template' error on Render
os.environ['NUMBA_DISABLE_JIT'] = '1'
warnings.filterwarnings('ignore')

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# =========================
# CONFIG & PATHS
# =========================
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff'}
heart_sound_bp = Blueprint('heart_sound', __name__)

current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
MODEL_PATH = os.path.join(project_root, 'ai_model', 'models', 'mitral_classifier_v4')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# FEATURE EXTRACTION (STABILIZED)
# =========================

def extract_features(filepath, sr=4000, duration=10.0):
    try:
        if not LIBROSA_AVAILABLE: return None
            
        signal, _ = librosa.load(filepath, sr=sr, duration=duration)
        if len(signal) < 1000: return None

        f_map = {}
        
        # 1. Basic statistics (4)
        f_map['mean'] = np.mean(signal)
        f_map['std'] = np.std(signal)
        f_map['rms'] = np.sqrt(np.mean(signal**2))
        f_map['peak'] = np.max(np.abs(signal))
        
        # 2. Zero crossing rate (2)
        zcr = librosa.feature.zero_crossing_rate(signal)[0]
        f_map['zcr_mean'] = np.mean(zcr)
        f_map['zcr_std'] = np.std(zcr)
        
        # 3. Spectral features (7)
        spec = np.abs(librosa.stft(signal, n_fft=1024, hop_length=256))
        spec_db = librosa.amplitude_to_db(spec, ref=np.max)
        f_map['spec_mean'] = np.mean(spec_db)
        f_map['spec_std'] = np.std(spec_db)
        f_map['spec_max'] = np.max(spec_db)
        
        freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
        centroid = np.sum(freqs[:, None] * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8)
        f_map['spec_centroid'] = np.mean(centroid)
        f_map['spec_centroid_std'] = np.std(centroid)
        
        bandwidth = np.sqrt(np.sum((freqs[:, None] - centroid[None, :])**2 * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8))
        f_map['spec_bandwidth'] = np.mean(bandwidth)
        
        cumsum = np.cumsum(spec, axis=0)
        rolloff = np.argmax(cumsum >= 0.85 * cumsum[-1, :], axis=0)
        f_map['spec_rolloff'] = np.mean(rolloff) * sr / 1024
        
        # 4. MFCCs (26: 13 mean + 13 std)
        mfccs = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=13, n_fft=1024)
        for i in range(13):
            f_map[f'mfcc_{i}'] = np.mean(mfccs[i])
            f_map[f'mfcc_{i}_std'] = np.std(mfccs[i])
            
        # 5. Mel spectrogram summary (4)
        mel_spec = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=64, n_fft=1024)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        f_map['mel_mean'] = np.mean(mel_spec_db)
        f_map['mel_std'] = np.std(mel_spec_db)
        f_map['mel_max'] = np.max(mel_spec_db)
        f_map['mel_energy'] = np.sum(mel_spec_db)
        
        # 6. Tempo (1) - REFACTORED TO AVOID NUMBA BUG
        try:
            onset_env = librosa.onset.onset_strength(y=signal, sr=sr)
            tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)[0]
            f_map['tempo'] = float(tempo)
        except:
            f_map['tempo'] = 1.0 # Default fallback
            
        # 7. Envelope (4)
        envelope = np.abs(signal)
        env_smooth = np.convolve(envelope, np.ones(50)/50, mode='same')
        f_map['env_mean'] = np.mean(env_smooth)
        f_map['env_std'] = np.std(env_smooth)
        f_map['env_peak'] = np.max(env_smooth)
        f_map['env_peak_ratio'] = f_map['env_peak'] / (f_map['env_mean'] + 1e-8)
        
        # 8. Band Power (3)
        fft = np.fft.rfft(signal)
        pow_freqs = np.fft.rfftfreq(len(signal), 1/sr)
        power = np.abs(fft)**2
        total_p = np.sum(power) + 1e-8
        for i, (low, high) in enumerate([(20, 80), (80, 200), (200, 400)]):
            mask = (pow_freqs >= low) & (pow_freqs < high)
            f_map[f'band_{i}_power'] = np.sum(power[mask]) / total_p

        # --- FINAL STEP: EXACT 51 FEATURE ORDERING ---
        # This list MUST match the columns used in your training notebook
        feature_order = [
            'mean', 'std', 'rms', 'peak', 
            'zcr_mean', 'zcr_std', 
            'spec_mean', 'spec_std', 'spec_max', 'spec_centroid', 'spec_centroid_std', 'spec_bandwidth', 'spec_rolloff',
            'mfcc_0', 'mfcc_0_std', 'mfcc_1', 'mfcc_1_std', 'mfcc_2', 'mfcc_2_std', 'mfcc_3', 'mfcc_3_std', 
            'mfcc_4', 'mfcc_4_std', 'mfcc_5', 'mfcc_5_std', 'mfcc_6', 'mfcc_6_std', 'mfcc_7', 'mfcc_7_std', 
            'mfcc_8', 'mfcc_8_std', 'mfcc_9', 'mfcc_9_std', 'mfcc_10', 'mfcc_10_std', 'mfcc_11', 'mfcc_11_std', 
            'mfcc_12', 'mfcc_12_std',
            'mel_mean', 'mel_std', 'mel_max', 'mel_energy',
            'tempo', 
            'env_mean', 'env_std', 'env_peak', 'env_peak_ratio',
            'band_0_power', 'band_1_power', 'band_2_power'
        ]
        
        vector = [f_map.get(k, 0.0) for k in feature_order]
        return np.array(vector).reshape(1, -1)
        
    except Exception as e:
        print(f"❌ Feature Extraction Error: {e}")
        return None

# =========================
# CLASSIFIER CLASS
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_count = 51 # Explicitly set to 51
        self.load_model()
    
    def load_model(self):
        try:
            m_file = os.path.join(self.model_path, 'best_model.pkl')
            s_file = os.path.join(self.model_path, 'scaler.pkl')
            if os.path.exists(m_file) and os.path.exists(s_file):
                self.model = joblib.load(m_file)
                self.scaler = joblib.load(s_file)
                print(f"✅ Scaler & Model Loaded. Expecting 51 features.")
                return True
            return False
        except Exception as e:
            print(f"❌ Model Load Error: {e}")
            return False

    def predict(self, filepath):
        if self.model is None or self.scaler is None: return None
        features = extract_features(filepath)
        if features is None: return None

        # Check for count mismatch
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
            return jsonify({'error': 'Prediction failed', 'message': 'Feature extraction or model mismatch'}), 500
            
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