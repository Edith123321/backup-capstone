import os
import sys
import tempfile
import warnings
import numpy as np
import joblib 
import traceback
from flask import request, jsonify, Blueprint
from scipy.signal import stft, convolve
from scipy.io import wavfile
import soundfile as sf  # More reliable than librosa for loading

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
# ROUTES
# =========================

@heart_sound_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy' if classifier else 'error',
        'model_loaded': classifier is not None,
        'feature_count': 51
    })

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    if not classifier:
        return jsonify({'error': 'Classifier not initialized'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    tmp_path = None
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Predict
        result = classifier.predict(tmp_path)
        if result is None:
            return jsonify({'error': 'Prediction failed - invalid audio or feature extraction'}), 500
        
        return jsonify({'success': True, **result})
        
    except Exception as e:
        print(f"❌ Route error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500
        
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass