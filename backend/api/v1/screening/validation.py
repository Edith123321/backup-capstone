# backend/api/v1/screening/validation.py
from flask import Blueprint, request, jsonify
import numpy as np
import librosa
import tempfile
import os

validation_bp = Blueprint('validation', __name__, url_prefix='/api/v1/screening')

@validation_bp.route('/validate', methods=['POST'])
def validate_heart_sound():
    """
    Validate that the uploaded audio contains a valid heart sound
    Returns:
        - is_valid: bool
        - quality_score: float (0-1)
        - issues: list of detected issues
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            file.save(tmp_file.name)
            filepath = tmp_file.name
        
        try:
            # Load audio
            signal, sr = librosa.load(filepath, sr=4000)
            
            # Perform validation checks
            validation_results = validate_signal(signal, sr)
            
            return jsonify(validation_results)
            
        finally:
            # Clean up temp file
            if os.path.exists(filepath):
                os.unlink(filepath)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def validate_signal(signal, sr):
    """
    Validate heart sound signal quality
    Returns dict with validation results
    """
    issues = []
    quality_score = 1.0
    
    # Check 1: Signal duration
    duration = len(signal) / sr
    if duration < 0.5:
        issues.append("Recording too short (< 0.5s)")
        quality_score *= 0.5
    
    # Check 2: Signal amplitude (RMS)
    rms = np.sqrt(np.mean(signal**2))
    if rms < 0.005:
        issues.append("Signal too quiet (low amplitude)")
        quality_score *= 0.6
    elif rms > 0.5:
        issues.append("Signal too loud (clipping detected)")
        quality_score *= 0.7
    
    # Check 3: Signal-to-noise ratio (SNR)
    # Using spectral flatness as proxy for noise
    spectral_flatness = np.exp(np.mean(np.log(np.abs(np.fft.rfft(signal)) + 1e-8)))
    if spectral_flatness > 0.5:
        issues.append("High noise content detected")
        quality_score *= 0.6
    
    # Check 4: Heart sound periodicity (using autocorrelation)
    autocorr = np.correlate(signal, signal, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    
    # Find peaks in autocorrelation
    peak_indices = []
    for i in range(1, len(autocorr) - 1):
        if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
            peak_indices.append(i)
    
    # Check if there's a regular pattern (heart sounds should have periodic peaks)
    if len(peak_indices) > 1:
        intervals = np.diff(peak_indices)
        interval_std = np.std(intervals)
        interval_mean = np.mean(intervals)
        
        # Heart rate should be between 40-200 bpm (0.3-1.5 Hz at 4kHz sample rate)
        # Expected interval range: 120-1500 samples at 4kHz (0.03-0.375s per beat)
        if interval_mean < 50 or interval_mean > 2000:
            issues.append("Heart rate outside expected range")
            quality_score *= 0.5
        elif interval_std / interval_mean > 0.5:
            issues.append("Irregular rhythm detected")
            quality_score *= 0.7
    else:
        issues.append("No regular heart sound pattern detected")
        quality_score *= 0.3
    
    # Check 5: Frequency content (heart sounds are typically 20-400 Hz)
    freqs = np.fft.rfftfreq(len(signal), 1/sr)
    power = np.abs(np.fft.rfft(signal))**2
    
    # Calculate power in heart sound range
    heart_mask = (freqs >= 20) & (freqs <= 400)
    heart_power = np.sum(power[heart_mask])
    total_power = np.sum(power) + 1e-8
    heart_power_ratio = heart_power / total_power
    
    if heart_power_ratio < 0.3:
        issues.append("Low heart sound frequency content")
        quality_score *= 0.4
    
    # Determine if valid
    is_valid = quality_score > 0.4 and len(issues) <= 3
    
    return {
        'is_valid': is_valid,
        'quality_score': round(quality_score, 3),
        'issues': issues,
        'duration': round(duration, 2),
        'rms': round(rms, 4),
        'heart_power_ratio': round(heart_power_ratio, 3),
        'heart_rate': calculate_heart_rate(signal, sr),
        'confidence': round(quality_score, 2)
    }


def calculate_heart_rate(signal, sr):
    """Estimate heart rate from signal"""
    try:
        # Use autocorrelation to find heart rate
        autocorr = np.correlate(signal, signal, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find peaks
        peak_indices = []
        for i in range(1, len(autocorr) - 1):
            if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
                peak_indices.append(i)
        
        if len(peak_indices) > 1:
            intervals = np.diff(peak_indices)
            avg_interval = np.mean(intervals)
            heart_rate = 60 * sr / avg_interval
            
            # Clamp to reasonable range
            heart_rate = max(30, min(200, heart_rate))
            return int(heart_rate)
        return None
    except:
        return None