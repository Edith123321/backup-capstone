// frontend_web/src/components/Dashboard/UploadHeartSound.jsx
import React, { useState, useRef } from 'react';
import { databaseApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './DashboardLayout.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://capstone-be-yxzd.onrender.com';

const UploadHeartSound = ({ isOpen, onClose, onUploadComplete, patients, preSelectedPatient }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  
  // Prediction states
  const [prediction, setPrediction] = useState(null);
  const [isPredicting, setIsPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState('');
  
  const [formData, setFormData] = useState({
    patient_id: preSelectedPatient?.id || '',
    recording_date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  // Update form when preSelectedPatient changes
  React.useEffect(() => {
    if (preSelectedPatient) {
      setFormData(prev => ({
        ...prev,
        patient_id: preSelectedPatient.id
      }));
    }
  }, [preSelectedPatient]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Validate file type
      const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/ogg'];
      const validExtensions = ['.wav', '.mp3', '.ogg', '.flac', '.m4a'];
      const fileExtension = selectedFile.name.toLowerCase().substring(selectedFile.name.lastIndexOf('.'));
      
      if (!validTypes.includes(selectedFile.type) && !validExtensions.includes(fileExtension)) {
        setError('Please upload a valid audio file (WAV, MP3, OGG, FLAC, or M4A)');
        return;
      }
      
      // Validate file size (max 50MB)
      if (selectedFile.size > 50 * 1024 * 1024) {
        setError('File size must be less than 50MB');
        return;
      }
      
      setFile(selectedFile);
      setError('');
      setSuccess(false);
      setPrediction(null);
      setPredictionError('');
    }
  };

  // Run prediction on the uploaded file
  const analyzeHeartSound = async () => {
    if (!file) {
      setPredictionError('Please select a file first');
      return;
    }

    setIsPredicting(true);
    setPredictionError('');
    setPrediction(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/api/v1/screening/predict`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        setPrediction({
          class: result.prediction,
          confidence: result.confidence,
          probabilities: result.probabilities,
          visualization: result.visualization
        });
        
        // If RHD detected with high confidence, show alert
        if (result.prediction === 'RHD' && result.confidence > 0.5) {
          setPredictionError(`⚠️ RHD detected with ${(result.confidence * 100).toFixed(1)}% confidence`);
        } else if (result.prediction === 'RHD') {
          setPredictionError(`⚠️ RHD suspected with ${(result.confidence * 100).toFixed(1)}% confidence - Further review recommended`);
        }
      } else {
        setPredictionError(result.error || 'Failed to analyze heart sound');
      }
    } catch (error) {
      console.error('Prediction error:', error);
      setPredictionError('Failed to connect to prediction service');
    } finally {
      setIsPredicting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.patient_id) {
      setError('Please select a patient');
      return;
    }
    
    if (!file) {
      setError('Please select an audio file');
      return;
    }

    // Run prediction first if not already done
    if (!prediction && !isPredicting) {
      await analyzeHeartSound();
      // If prediction failed, don't proceed with upload
      if (!prediction && predictionError) {
        return;
      }
    }

    setLoading(true);
    setError('');
    setSuccess(false);
    setUploadProgress(0);

    try {
      // Create FormData for file upload
      const uploadData = new FormData();
      uploadData.append('patient_id', formData.patient_id);
      uploadData.append('doctor_id', user.id);
      uploadData.append('recording_date', formData.recording_date);
      uploadData.append('notes', formData.notes);
      uploadData.append('file', file);
      
      // Add prediction data if available
      if (prediction) {
        uploadData.append('prediction', prediction.class);
        uploadData.append('confidence', String(prediction.confidence));
        uploadData.append('probabilities', JSON.stringify(prediction.probabilities));
        uploadData.append('rhd_risk_score', String((prediction.probabilities?.RHD || 0) * 100));
        uploadData.append('rhd_recommendation', 
          prediction.class === 'RHD' 
            ? `RHD detected with ${(prediction.confidence * 100).toFixed(1)}% confidence - Refer to cardiologist`
            : 'No RHD detected - Continue routine monitoring'
        );
      }

      // Use XMLHttpRequest for actual progress tracking
      const response = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            setUploadProgress(progress);
          }
        });

        // Handle response
        xhr.addEventListener('load', () => {
          try {
            const response = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(response);
            } else {
              reject(new Error(response.error || 'Upload failed'));
            }
          } catch (e) {
            reject(new Error('Failed to parse server response'));
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('Network error occurred'));
        });

        xhr.addEventListener('abort', () => {
          reject(new Error('Upload was cancelled'));
        });

        // Open and send the request
        const apiUrl = import.meta.env.VITE_API_URL || 'https://capstone-be-yxzd.onrender.com';
        xhr.open('POST', `${apiUrl}/api/v1/database/recordings`);
        xhr.withCredentials = true;
        
        // Add authorization header if token exists
        const token = localStorage.getItem('token');
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }
        
        xhr.send(uploadData);
      });

      console.log('Upload response:', response);
      
      // Check if upload was successful
      if (response && response.success !== false) {
        setUploadProgress(100);
        setSuccess(true);
        setError('');
        
        // Reset form after successful upload
        setFile(null);
        setPrediction(null);
        setFormData({
          patient_id: preSelectedPatient?.id || '',
          recording_date: new Date().toISOString().split('T')[0],
          notes: ''
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        
        // Notify parent component
        if (onUploadComplete) {
          onUploadComplete();
        }
        
        // Close modal after delay
        setTimeout(() => {
          onClose();
        }, 3000);
      } else {
        setError(response?.error || 'Failed to upload recording');
        setUploadProgress(0);
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'An error occurred. Please try again.');
      setUploadProgress(0);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    // Reset state when closing
    setError('');
    setSuccess(false);
    setUploadProgress(0);
    setPrediction(null);
    setPredictionError('');
    setIsPredicting(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Heart Sound Recording</h2>
          <button className="modal-close" onClick={handleClose}>×</button>
        </div>

        {error && (
          <div className="modal-error">
            <span className="error-icon">!</span>
            {error}
          </div>
        )}

        {success && (
          <div className="modal-success">
            <span className="success-icon">✓</span>
            <div>
              <div>Recording uploaded successfully!</div>
              {prediction && (
                <div className={`prediction-badge-small ${prediction.class === 'RHD' ? 'rhd' : 'normal'}`}>
                  {prediction.class === 'RHD' ? '⚠️ RHD Detected' : '✅ Normal Heart Sound'}
                  <span className="confidence-small">
                    {(prediction.confidence * 100).toFixed(1)}% confidence
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Patient</label>
              <select
                name="patient_id"
                value={formData.patient_id}
                onChange={handleChange}
                required
                disabled={!!preSelectedPatient}
              >
                <option value="">Select a patient</option>
                {patients.map(patient => (
                  <option key={patient.id} value={patient.id}>
                    {patient.name} (ID: {patient.id})
                  </option>
                ))}
              </select>
              {preSelectedPatient && (
                <div className="form-hint">
                  Patient: {preSelectedPatient.name} (ID: {preSelectedPatient.id})
                </div>
              )}
            </div>

            <div className="form-group">
              <label>Recording Date</label>
              <input
                type="date"
                name="recording_date"
                value={formData.recording_date}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Audio File</label>
              <div className="file-upload-wrapper">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".wav,.mp3,.ogg,.flac,.m4a,audio/*"
                  required
                  className="file-input"
                  disabled={loading || success}
                />
                <div className="file-upload-area">
                  {file ? (
                    <div className="file-info">
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                    </div>
                  ) : (
                    <div className="file-placeholder">
                      <span>Click or drag to upload audio file</span>
                      <span className="file-hint">Supported: WAV, MP3, OGG, FLAC, M4A (Max 50MB)</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Prediction Section */}
            {file && !prediction && !isPredicting && !success && (
              <div className="form-group prediction-action">
                <button
                  type="button"
                  className="btn-predict"
                  onClick={analyzeHeartSound}
                  disabled={loading || success}
                >
                  🔬 Analyze for RHD
                </button>
                <span className="form-hint">Run AI analysis to detect RHD</span>
              </div>
            )}

            {isPredicting && (
              <div className="predicting-indicator">
                <div className="spinner"></div>
                <span>Analyzing heart sound for RHD...</span>
              </div>
            )}

            {predictionError && (
              <div className={`prediction-error ${predictionError.includes('RHD') ? 'rhd-warning' : ''}`}>
                <span className="error-icon">⚠️</span>
                {predictionError}
              </div>
            )}

            {prediction && !success && (
              <div className="prediction-result">
                <div className={`prediction-banner ${prediction.class === 'RHD' ? 'rhd' : 'normal'}`}>
                  <div className="prediction-icon">
                    {prediction.class === 'RHD' ? '🫀' : '💚'}
                  </div>
                  <div className="prediction-info">
                    <div className="prediction-label">
                      {prediction.class === 'RHD' ? 'RHD DETECTED' : 'NORMAL HEART SOUND'}
                    </div>
                    <div className="prediction-confidence">
                      {(prediction.confidence * 100).toFixed(1)}% confidence
                    </div>
                  </div>
                </div>

                <div className="prediction-probabilities">
                  <div className="prob-bar">
                    <span className="prob-label">Normal</span>
                    <div className="prob-track">
                      <div 
                        className="prob-fill normal"
                        style={{ width: `${((prediction.probabilities?.Normal || 0) * 100).toFixed(1)}%` }}
                      />
                    </div>
                    <span className="prob-value">
                      {((prediction.probabilities?.Normal || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="prob-bar">
                    <span className="prob-label">RHD</span>
                    <div className="prob-track">
                      <div 
                        className="prob-fill rhd"
                        style={{ width: `${((prediction.probabilities?.RHD || 0) * 100).toFixed(1)}%` }}
                      />
                    </div>
                    <span className="prob-value">
                      {((prediction.probabilities?.RHD || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {prediction.class === 'RHD' && (
                  <div className="rhd-recommendation">
                    <span className="recommendation-icon">📋</span>
                    <span>
                      {prediction.confidence > 0.7 
                        ? 'High risk RHD detected. Immediate cardiology referral recommended.'
                        : 'RHD suspected. Further evaluation by cardiologist recommended.'
                      }
                    </span>
                  </div>
                )}
              </div>
            )}

            {(uploadProgress > 0 || loading) && (
              <div className="upload-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <span className="progress-text">
                  {uploadProgress === 100 ? 'Upload complete!' : `${uploadProgress}% uploaded`}
                </span>
              </div>
            )}

            <div className="form-group">
              <label>Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                rows="2"
                placeholder="Add any notes about this recording..."
                disabled={loading || success}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary" 
              disabled={loading || !file || !formData.patient_id || success || isPredicting}
            >
              {loading ? 'Uploading...' : success ? 'Uploaded!' : 'Upload Recording'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadHeartSound;