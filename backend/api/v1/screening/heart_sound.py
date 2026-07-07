import os
import sys

# Ensure this is set before any other imports
os.environ['NUMBA_DISABLE_JIT'] = '1'

import tempfile
import warnings
import numpy as np
import joblib 
import traceback
from scipy.signal import stft, butter, lfilter, find_peaks
from flask import request, jsonify, Blueprint

warnings.filterwarnings('ignore')

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# =========================
# CONFIG & PATHS
# =========================
heart_sound_bp = Blueprint('heart_sound', __name__)
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
MODEL_PATH = os.path.join(project_root, 'ai_model', 'models', 'mitral_classifier_v4')

# =========================
# PURE NUMPY FEATURE HELPERS (Numba-Safe)
# =========================

def get_zcr_numpy(y):
    """NumPy implementation of Zero Crossing Rate to bypass Numba crash."""
    return np.mean(np.abs(np.diff(np.sign(y)))) / 2

def get_tempo_numpy(y, sr):
    """Simple autocorrelation-based BPM estimation."""
    try:
        # Simple energy envelope
        env = np.abs(y)
        # Downsample envelope for speed
        resample_factor = 10
        env = env[::resample_factor]
        # Autocorrelate
        corr = np.correlate(env, env, mode='full')[len(env)-1:]
        # Find peak in heart-rate range (40-180 BPM)
        low = int(sr / resample_factor * 60 / 180)
        high = int(sr / resample_factor * 60 / 40)
        peak = np.argmax(corr[low:high]) + low
        return (sr / resample_factor) * 60 / peak
    except:
        return 110.0

# =========================
# FEATURE EXTRACTION
# =========================

def extract_features(filepath, sr=4000, duration=10.0):
    try:
        # 1. Load Audio
        y, _ = librosa.load(filepath, sr=sr, duration=duration)
        if len(y) < 1000: return None

        f_map = {}
        
        # 1. Basic statistics
        f_map['mean'] = np.mean(y)
        f_map['std'] = np.std(y)
        f_map['rms'] = np.sqrt(np.mean(y**2))
        f_map['peak'] = np.max(np.abs(y))
        
        # 2. Zero crossing rate (MANUAL NUMPY)
        f_map['zcr_mean'] = get_zcr_numpy(y)
        f_map['zcr_std'] = 0.0 # Placeholder to keep count at 51
        
        # 3. Spectral features
        # We use Librosa but skip the high-level wrappers that trigger Numba
        S = np.abs(librosa.stft(y, n_fft=1024, hop_length=256))
        S_db = librosa.amplitude_to_db(S, ref=np.max)
        
        f_map['spec_mean'] = np.mean(S_db)
        f_map['spec_std'] = np.std(S_db)
        f_map['spec_max'] = np.max(S_db)
        
        # Centroid & Bandwidth
        freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
        centroid = np.sum(freqs[:, None] * S, axis=0) / (np.sum(S, axis=0) + 1e-8)
        f_map['spec_centroid'] = np.mean(centroid)
        f_map['spec_centroid_std'] = np.std(centroid)
        
        bandwidth = np.sqrt(np.sum((freqs[:, None] - centroid[None, :])**2 * S, axis=0) / (np.sum(S, axis=0) + 1e-8))
        f_map['spec_bandwidth'] = np.mean(bandwidth)
        
        rolloff = np.argmax(np.cumsum(S, axis=0) >= 0.85 * np.sum(S, axis=0), axis=0)
        f_map['spec_rolloff'] = np.mean(rolloff) * sr / 1024
        
        # 4. MFCCs (Usually safe from Numba if called directly)
        mfccs = librosa.feature.mfcc(S=librosa.amplitude_to_db(S), sr=sr, n_mfcc=13)
        for i in range(13):
            f_map[f'mfcc_{i}'] = np.mean(mfccs[i])
            f_map[f'mfcc_{i}_std'] = np.std(mfccs[i])
            
        # 5. Mel Spectrogram
        mel = librosa.feature.melspectrogram(S=S**2, sr=sr, n_mels=64)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        f_map['mel_mean'] = np.mean(mel_db)
        f_map['mel_std'] = np.std(mel_db)
        f_map['mel_max'] = np.max(mel_db)
        f_map['mel_energy'] = np.sum(mel_db)
        
        # 6. Tempo (MANUAL NUMPY)
        f_map['tempo'] = get_tempo_numpy(y, sr)
            
        # 7. Envelope
        env = np.abs(y)
        env_smooth = np.convolve(env, np.ones(50)/50, mode='same')
        f_map['env_mean'] = np.mean(env_smooth)
        f_map['env_std'] = np.std(env_smooth)
        f_map['env_peak'] = np.max(env_smooth)
        f_map['env_peak_ratio'] = f_map['env_peak'] / (f_map['env_mean'] + 1e-8)
        
        # 8. Band Power
        fft_vals = np.abs(np.fft.rfft(y))**2
        fft_freqs = np.fft.rfftfreq(len(y), 1/sr)
        total_p = np.sum(fft_vals) + 1e-8
        for i, (low, high) in enumerate([(20, 80), (80, 200), (200, 400)]):
            mask = (fft_freqs >= low) & (fft_freqs < high)
            f_map[f'band_{i}_power'] = np.sum(fft_vals[mask]) / total_p

        # --- THE STRICT 51 LIST ---
        feature_order = [
            'mean', 'std', 'rms', 'peak', 'zcr_mean', 'zcr_std', 
            'spec_mean', 'spec_std', 'spec_max', 'spec_centroid', 'spec_centroid_std', 'spec_bandwidth', 'spec_rolloff',
            'mfcc_0', 'mfcc_0_std', 'mfcc_1', 'mfcc_1_std', 'mfcc_2', 'mfcc_2_std', 'mfcc_3', 'mfcc_3_std', 
            'mfcc_4', 'mfcc_4_std', 'mfcc_5', 'mfcc_5_std', 'mfcc_6', 'mfcc_6_std', 'mfcc_7', 'mfcc_7_std', 
            'mfcc_8', 'mfcc_8_std', 'mfcc_9', 'mfcc_9_std', 'mfcc_10', 'mfcc_10_std', 'mfcc_11', 'mfcc_11_std', 
            'mfcc_12', 'mfcc_12_std', 'mel_mean', 'mel_std', 'mel_max', 'mel_energy', 'tempo', 
            'env_mean', 'env_std', 'env_peak', 'env_peak_ratio', 'band_0_power', 'band_1_power', 'band_2_power'
        ]
        
        vector = [np.nan_to_num(f_map.get(k, 0.0)) for k in feature_order]
        return np.array(vector).reshape(1, -1)
        
    except Exception as e:
        print(f"❌ Extraction Crash: {str(e)}")
        return None

# =========================
# PREDICTION LOGIC
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = joblib.load(os.path.join(model_path, 'best_model.pkl'))
        self.scaler = joblib.load(os.path.join(model_path, 'scaler.pkl'))

    def predict(self, filepath):
        features = extract_features(filepath)
        if features is None: return None
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

@heart_sound_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model_loaded': True, 'feature_count': 51})

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    try:
        result = classifier.predict(tmp_path)
        if result is None: return jsonify({'error': 'Prediction failed'}), 500
        return jsonify({'success': True, **result})
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)