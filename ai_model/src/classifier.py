import os
import numpy as np
import pandas as pd
import librosa
import joblib
import matplotlib
# Force matplotlib to use non-interactive backend
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import warnings
warnings.filterwarnings('ignore')

class HeartSoundClassifier:
    """Heart sound classifier wrapper for the trained model"""
    
    def __init__(self, model_path='models/mitral_classifier_v4'):
        """Initialize the classifier with trained model"""
        self.model_path = model_path
        
        # Load model and scaler
        self.model = joblib.load(os.path.join(model_path, 'best_model.pkl'))
        self.scaler = joblib.load(os.path.join(model_path, 'scaler.pkl'))
        self.classes = ['Normal', 'RHD']
        self.sr = 4000
        self.feature_names = None
        
        print(f"✅ Classifier initialized!")
        print(f"   Model: {type(self.model).__name__}")
        print(f"   Classes: {self.classes}")
        print(f"   Model path: {model_path}")
    
    def extract_features(self, file_path):
        """Extract features from audio file"""
        try:
            # Load audio
            signal, _ = librosa.load(file_path, sr=self.sr, duration=10.0)
            
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
            try:
                spec = np.abs(librosa.stft(signal, n_fft=1024, hop_length=256))
                spec_db = librosa.amplitude_to_db(spec, ref=np.max)
                
                features['spec_mean'] = np.mean(spec_db)
                features['spec_std'] = np.std(spec_db)
                features['spec_max'] = np.max(spec_db)
                
                freqs = librosa.fft_frequencies(sr=self.sr, n_fft=1024)
                centroid = np.sum(freqs[:, None] * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8)
                features['spec_centroid'] = np.mean(centroid)
                features['spec_centroid_std'] = np.std(centroid)
                
                bandwidth = np.sqrt(np.sum((freqs[:, None] - centroid[None, :])**2 * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8))
                features['spec_bandwidth'] = np.mean(bandwidth)
                
                cumsum = np.cumsum(spec, axis=0)
                rolloff = np.argmax(cumsum >= 0.85 * cumsum[-1, :], axis=0)
                features['spec_rolloff'] = np.mean(rolloff) * self.sr / 1024
            except:
                features['spec_mean'] = 0
                features['spec_std'] = 0
                features['spec_max'] = 0
                features['spec_centroid'] = 0
                features['spec_centroid_std'] = 0
                features['spec_bandwidth'] = 0
                features['spec_rolloff'] = 0
            
            # 4. MFCC features
            try:
                mfccs = librosa.feature.mfcc(y=signal, sr=self.sr, n_mfcc=13, n_fft=1024)
                for i in range(13):
                    features[f'mfcc_{i}'] = np.mean(mfccs[i])
                    features[f'mfcc_{i}_std'] = np.std(mfccs[i])
            except:
                for i in range(13):
                    features[f'mfcc_{i}'] = 0
                    features[f'mfcc_{i}_std'] = 0
            
            # 5. Mel spectrogram summary
            try:
                mel_spec = librosa.feature.melspectrogram(y=signal, sr=self.sr, n_mels=64, n_fft=1024)
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
                tempo, _ = librosa.beat.beat_track(y=signal, sr=self.sr)
                features['tempo'] = float(tempo) if isinstance(tempo, np.ndarray) else tempo
            except:
                features['tempo'] = 0
            
            # 7. Envelope features
            envelope = np.abs(signal)
            envelope_smooth = np.convolve(envelope, np.ones(50)/50, mode='same')
            features['env_mean'] = np.mean(envelope_smooth)
            features['env_std'] = np.std(envelope_smooth)
            features['env_peak'] = np.max(envelope_smooth)
            features['env_peak_ratio'] = features['env_peak'] / (features['env_mean'] + 1e-8)
            
            # 8. Frequency band power ratios
            try:
                fft = np.fft.rfft(signal)
                freqs = np.fft.rfftfreq(len(signal), 1/self.sr)
                power = np.abs(fft)**2
                
                bands = [(20, 80), (80, 200), (200, 400)]
                total_power = np.sum(power) + 1e-8
                
                for i, (low, high) in enumerate(bands):
                    mask = (freqs >= low) & (freqs < high)
                    features[f'band_{i}_power'] = np.sum(power[mask]) / total_power
            except:
                for i in range(3):
                    features[f'band_{i}_power'] = 0
            
            return features
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def predict(self, file_path, return_all=False):
        """Predict class for a single audio file"""
        features = self.extract_features(file_path)
        
        if features is None:
            return None
        
        feature_df = pd.DataFrame([features])
        feature_df = feature_df.fillna(0)
        
        if self.feature_names is None:
            self.feature_names = feature_df.columns.tolist()
        
        X_scaled = self.scaler.transform(feature_df)
        
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0]
        
        predicted_class = self.classes[prediction]
        confidence = probability[prediction] * 100
        
        result = {
            'class': predicted_class,
            'class_id': int(prediction),
            'confidence': float(confidence),
            'prob_normal': float(probability[0]),
            'prob_rhd': float(probability[1]),
        }
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            feature_importance = pd.DataFrame({
                'Feature': self.feature_names,
                'Importance': importances
            }).sort_values('Importance', ascending=False)
            
            result['top_features'] = feature_importance.head(10).to_dict('records')
        
        return result
    
    def generate_visualization(self, file_path):
        """Generate visualization as base64 image"""
        result = self.predict(file_path, return_all=True)
        
        if result is None:
            return None
        
        signal, sr = librosa.load(file_path, sr=self.sr)
        
        # Create figure with non-interactive backend (Agg already set)
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Heart Sound Analysis', fontsize=16, fontweight='bold')
        
        # 1. Waveform
        axes[0, 0].plot(signal[:min(len(signal), 20000)])
        axes[0, 0].set_title('Waveform (20-400 Hz filtered)')
        axes[0, 0].set_xlabel('Sample')
        axes[0, 0].set_ylabel('Amplitude')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Mel Spectrogram
        mel_spec = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=64)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        im = axes[0, 1].imshow(mel_spec_db, aspect='auto', 
                              extent=[0, len(signal)/sr, 0, sr/2])
        axes[0, 1].set_title('Mel Spectrogram')
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].set_ylabel('Frequency (Hz)')
        plt.colorbar(im, ax=axes[0, 1])
        
        # 3. Prediction probabilities
        probs = [result['prob_normal'], result['prob_rhd']]
        colors = ['#2ecc71' if result['class'] == 'Normal' else '#95a5a6',
                 '#e74c3c' if result['class'] == 'RHD' else '#95a5a6']
        axes[1, 0].bar(['Normal', 'RHD'], probs, color=colors)
        axes[1, 0].set_title(f"Prediction: {result['class']} ({result['confidence']:.1f}%)")
        axes[1, 0].set_ylabel('Probability')
        axes[1, 0].set_ylim([0, 1])
        axes[1, 0].grid(True, alpha=0.3)
        for i, v in enumerate(probs):
            axes[1, 0].text(i, v + 0.02, f'{v:.2%}', ha='center', fontweight='bold')
        
        # 4. Summary
        axes[1, 1].axis('off')
        summary_text = f"""
        🫀 Heart Sound Analysis Result
        
        📊 Prediction: {result['class']}
        🎯 Confidence: {result['confidence']:.1f}%
        
        📈 Probabilities:
        • Normal: {result['prob_normal']:.2%}
        • RHD: {result['prob_rhd']:.2%}
        
        🔍 Model: Random Forest
        📁 File: {os.path.basename(file_path)}
        """
        axes[1, 1].text(0.1, 0.5, summary_text, 
                       transform=axes[1, 1].transAxes,
                       fontsize=12, verticalalignment='center',
                       fontfamily='monospace',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        axes[1, 1].set_title('Diagnosis Summary')
        
        plt.tight_layout()
        
        # Save to bytes
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)  # Explicitly close the figure to free memory
        
        return img_base64

# For testing
if __name__ == "__main__":
    # Test the classifier
    classifier = HeartSoundClassifier('../models/mitral_classifier_v4')
    print("\n Classifier ready for testing!")
