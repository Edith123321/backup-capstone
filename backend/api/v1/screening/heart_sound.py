import os
import joblib  # Use joblib instead of pickle
import librosa
import numpy as np
import warnings
from flask import Blueprint, request, jsonify
import tempfile

# ... (Previous imports and PATH definitions remain the same) ...

# =========================
# FEATURE EXTRACTION - EXACT MATCH TO TRAINING
# =========================

def extract_features(filepath, sr=4000, duration=10.0):
    """
    EXTRACT FEATURES IN THE EXACT ORDER OF THE TRAINING DICTIONARY
    DO NOT USE sorted() AS IT BREAKS THE FEATURE INDEXING
    """
    try:
        signal, _ = librosa.load(filepath, sr=sr, duration=duration)
        if len(signal) < 1000: return None

        features = {}
        # 1. Basic Stats
        features['mean'] = np.mean(signal)
        features['std'] = np.std(signal)
        features['rms'] = np.sqrt(np.mean(signal**2))
        features['peak'] = np.max(np.abs(signal))
        
        # 2. ZCR
        zcr = librosa.feature.zero_crossing_rate(signal)[0]
        features['zcr_mean'] = np.mean(zcr)
        features['zcr_std'] = np.std(zcr)

        # 3. Spectral
        spec = np.abs(librosa.stft(signal, n_fft=1024, hop_length=256))
        spec_db = librosa.amplitude_to_db(spec, ref=np.max)
        features['spec_mean'] = np.mean(spec_db)
        features['spec_std'] = np.std(spec_db)
        features['spec_max'] = np.max(spec_db)
        
        freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
        centroid = np.sum(freqs[:, None] * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8)
        features['spec_centroid'] = np.mean(centroid)
        features['spec_centroid_std'] = np.std(centroid)
        features['spec_bandwidth'] = np.mean(np.sqrt(np.sum((freqs[:, None] - centroid[None, :])**2 * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8)))
        
        cumsum = np.cumsum(spec, axis=0)
        rolloff = np.argmax(cumsum >= 0.85 * cumsum[-1, :], axis=0)
        features['spec_rolloff'] = np.mean(rolloff) * sr / 1024

        # 4. MFCCs (Training Order: mfcc_i then mfcc_i_std)
        mfccs = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=13, n_fft=1024)
        for i in range(13):
            features[f'mfcc_{i}'] = np.mean(mfccs[i])
            features[f'mfcc_{i}_std'] = np.std(mfccs[i])

        # 5. Mel
        mel_spec = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=64, n_fft=1024)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        features['mel_mean'] = np.mean(mel_spec_db)
        features['mel_std'] = np.std(mel_spec_db)
        features['mel_max'] = np.max(mel_spec_db)
        features['mel_energy'] = np.sum(mel_spec_db)

        # 6. Tempo
        tempo, _ = librosa.beat.beat_track(y=signal, sr=sr)
        features['tempo'] = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)

        # 7. Envelope
        envelope = np.abs(signal)
        env_smooth = np.convolve(envelope, np.ones(50)/50, mode='same')
        features['env_mean'] = np.mean(env_smooth)
        features['env_std'] = np.std(env_smooth)
        features['env_peak'] = np.max(env_smooth)
        features['env_peak_ratio'] = features['env_peak'] / (features['env_mean'] + 1e-8)

        # 8. Band Power
        fft = np.fft.rfft(signal)
        pow_freqs = np.fft.rfftfreq(len(signal), 1/sr)
        power = np.abs(fft)**2
        total_p = np.sum(power) + 1e-8
        for i, (low, high) in enumerate([(20, 80), (80, 200), (200, 400)]):
            mask = (pow_freqs >= low) & (pow_freqs < high)
            features[f'band_{i}_power'] = np.sum(power[mask]) / total_p

        # IMPORTANT: Maintain dictionary order to match X_train columns
        return np.array(list(features.values())).reshape(1, -1)

    except Exception as e:
        print(f"Error extracting features: {e}")
        return None

# =========================
# UPDATED CLASSIFIER CLASS
# =========================

class HeartSoundClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.load_model()
    
    def load_model(self):
        try:
            # CHANGE: Use joblib.load to match your notebook's joblib.dump
            self.model = joblib.load(os.path.join(self.model_path, 'best_model.pkl'))
            self.scaler = joblib.load(os.path.join(self.model_path, 'scaler.pkl'))
            
            # Identify expected features from the scaler
            self.feature_count = self.scaler.n_features_in_
            print(f"✅ Model Loaded. Expected Features: {self.feature_count}")
            return True
        except Exception as e:
            print(f"❌ Load Error: {e}")
            return False

    def predict(self, filepath):
        try:
            features = extract_features(filepath)
            if features is None: return None
            
            # Ensure feature count matches model exactly
            if features.shape[1] != self.feature_count:
                print(f"⚠️ Feature count mismatch! Got {features.shape[1]}, Expected {self.feature_count}")
                # Optional: Force resize if minor mismatch, but usually indicates logic error
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
        except Exception as e:
            print(f"❌ Prediction Logic Error: {e}")
            return None