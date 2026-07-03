// frontend_web/src/components/Dashboard/UploadHeartSound.jsx
import React, { useState, useRef } from 'react';
import { databaseApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './DashboardLayout.css';

const UploadHeartSound = ({ isOpen, onClose, onUploadComplete, patients, preSelectedPatient }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  
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
      if (!validTypes.includes(selectedFile.type)) {
        setError('Please upload a valid audio file (WAV, MP3, or OGG)');
        return;
      }
      
      // Validate file size (max 50MB)
      if (selectedFile.size > 50 * 1024 * 1024) {
        setError('File size must be less than 50MB');
        return;
      }
      
      setFile(selectedFile);
      setError('');
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

    setLoading(true);
    setError('');
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      const response = await databaseApi.uploadRecording({
        patient_id: formData.patient_id,
        doctor_id: user.id,
        recording_date: formData.recording_date,
        notes: formData.notes,
        file: file
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.success) {
        onUploadComplete();
        onClose();
        // Reset form
        setFile(null);
        setUploadProgress(0);
        setFormData({
          patient_id: preSelectedPatient?.id || '',
          recording_date: new Date().toISOString().split('T')[0],
          notes: ''
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        setError(response.error || 'Failed to upload recording');
        setUploadProgress(0);
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
      setUploadProgress(0);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Heart Sound Recording</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="modal-error">
            {error}
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
                  accept=".wav,.mp3,.ogg,audio/*"
                  required
                  className="file-input"
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
                      <span className="file-hint">Supported: WAV, MP3, OGG (Max 50MB)</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {uploadProgress > 0 && uploadProgress < 100 && (
              <div className="upload-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <span className="progress-text">{uploadProgress}% uploaded</span>
              </div>
            )}

            {uploadProgress === 100 && (
              <div className="upload-success">
                <span>✓ Upload complete!</span>
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
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary" 
              disabled={loading || !file || !formData.patient_id}
            >
              {loading ? 'Uploading...' : 'Upload Recording'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadHeartSound;