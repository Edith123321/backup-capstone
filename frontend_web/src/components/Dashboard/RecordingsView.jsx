// frontend_web/src/components/Dashboard/RecordingView.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patientService, screeningService, databaseApi } from '../../services/api';
import './RecordingView.css';

const RecordingView = () => {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  
  const [patient, setPatient] = useState(null);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisResult, setAnalysisResult] = useState(null);

  // Fetch patient and recordings data
  const fetchData = useCallback(async () => {
    if (!isAuthenticated || !patientId) return;

    try {
      setLoading(true);
      setError(null);
      
      // Fetch patient details
      const patientData = await patientService.getPatientDetails(patientId);
      if (patientData?.patient) {
        setPatient(patientData.patient);
      }
      
      // Fetch recordings using the database API
      const recordingsResponse = await databaseApi.getRecordings(patientId);
      if (recordingsResponse.success) {
        setRecordings(recordingsResponse.recordings || []);
      } else {
        // Fallback to screening service
        const historyData = await screeningService.getHistory(patientId);
        if (historyData.success) {
          setRecordings(historyData.recordings || []);
        }
      }
      
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err.message || 'Failed to load recordings');
    } finally {
      setLoading(false);
    }
  }, [patientId, isAuthenticated]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle file upload and analysis
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/m4a', 'audio/x-m4a'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(wav|mp3|m4a)$/i)) {
      alert('Please upload a valid audio file (WAV, MP3, or M4A)');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setAnalysisResult(null);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);

      // Analyze the heart sound
      const result = await screeningService.predict(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);

      // Save recording to database
      if (result.success || result.prediction) {
        const recordingData = {
          patient_id: patientId,
          doctor_id: user?.doctor_id || user?.id,
          file_name: file.name,
          prediction: result.prediction || result.class || 'Unknown',
          confidence: result.confidence || 0,
          recording_date: new Date().toISOString(),
          notes: `Uploaded and analyzed on ${new Date().toLocaleString()}`
        };

        // Save via database API
        const saveResult = await databaseApi.saveRecording(recordingData);
        
        if (saveResult.success) {
          // Refresh recordings list
          await fetchData();
        }

        setAnalysisResult({
          prediction: result.prediction || result.class || 'Unknown',
          confidence: result.confidence || 0,
          prob_normal: result.prob_normal || 0,
          prob_rhd: result.prob_rhd || 0,
          timestamp: new Date().toISOString(),
          file_name: file.name
        });
      }

      setShowUploadModal(false);
      
    } catch (err) {
      console.error('Upload error:', err);
      alert(`Failed to process recording: ${err.message}`);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // Handle recording selection for playback
  const handleSelectRecording = (recording) => {
    setSelectedRecording(selectedRecording?.id === recording.id ? null : recording);
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Get prediction badge class
  const getPredictionBadge = (prediction) => {
    if (!prediction || prediction === 'Unknown') return 'badge-gray';
    return prediction === 'RHD' ? 'badge-red' : 'badge-green';
  };

  // Get RHD status display
  const getRHDStatusDisplay = (status) => {
    const statusMap = {
      'confirmed': { label: 'Confirmed RHD', color: '#dc2626', bg: '#fee2e2' },
      'suspected': { label: 'Suspected RHD', color: '#f59e0b', bg: '#fed7aa' },
      'none': { label: 'No RHD', color: '#22c55e', bg: '#dcfce7' },
      'unknown': { label: 'Unknown', color: '#94a3b8', bg: '#f1f5f9' }
    };
    return statusMap[status] || statusMap.unknown;
  };

  // Loading state
  if (authLoading || (loading && !patient)) {
    return (
      <div className="recording-loading">
        <div className="loading-spinner"></div>
        <p>Loading recordings...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠️</div>
        <h3>Unable to Load Recordings</h3>
        <p>{error}</p>
        <div className="error-actions">
          <button className="btn-primary" onClick={fetchData}>Retry</button>
          <button className="btn-secondary" onClick={() => navigate(`/patient/${patientId}`)}>
            Back to Patient
          </button>
        </div>
      </div>
    );
  }

  const rhdStatus = patient ? getRHDStatusDisplay(patient.rhd_status || 'unknown') : null;

  return (
    <div className="recording-view-container">
      {/* Header */}
      <div className="recording-header">
        <div className="header-left">
          <button 
            className="btn-secondary" 
            onClick={() => navigate(`/patient/${patientId}`)}
          >
            ← Back to Patient
          </button>
          <div className="patient-info">
            <div className="patient-avatar-small">
              {patient?.name?.charAt(0) || 'P'}
            </div>
            <div>
              <h2>{patient?.name || 'Patient'}</h2>
              <span className="patient-id">ID: {patientId}</span>
              {patient && (
                <span className="rhd-status" style={{ color: rhdStatus.color }}>
                  • {rhdStatus.label}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="header-actions">
          <button 
            className="btn-primary" 
            onClick={() => setShowUploadModal(true)}
            disabled={uploading || analyzing}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Upload Recording
          </button>
          <button className="btn-secondary" onClick={fetchData}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="stats-summary">
        <div className="stat-item">
          <span className="stat-number">{recordings.length}</span>
          <span className="stat-label">Total Recordings</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">
            {recordings.filter(r => r.prediction === 'RHD').length}
          </span>
          <span className="stat-label">RHD Detected</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">
            {recordings.filter(r => r.prediction === 'Normal').length}
          </span>
          <span className="stat-label">Normal</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">
            {recordings.filter(r => !r.prediction || r.prediction === 'Unknown').length}
          </span>
          <span className="stat-label">Pending Analysis</span>
        </div>
      </div>

      {/* Recordings List */}
      <div className="recordings-list">
        {recordings.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🎵</div>
            <h3>No Recordings Yet</h3>
            <p>Upload a heart sound recording to get AI-powered analysis.</p>
            <button 
              className="btn-primary" 
              onClick={() => setShowUploadModal(true)}
            >
              Upload Your First Recording
            </button>
          </div>
        ) : (
          <div className="recordings-grid">
            {recordings.map((recording) => (
              <div 
                key={recording.id} 
                className={`recording-card ${selectedRecording?.id === recording.id ? 'expanded' : ''}`}
                onClick={() => handleSelectRecording(recording)}
              >
                <div className="recording-card-header">
                  <div className="recording-info">
                    <div className="recording-icon">🎵</div>
                    <div>
                      <h4>{recording.file_name || `Recording ${recording.id?.slice(0, 6)}`}</h4>
                      <span className="recording-date">
                        {recording.recording_date 
                          ? new Date(recording.recording_date).toLocaleString()
                          : recording.created_at 
                            ? new Date(recording.created_at).toLocaleString()
                            : 'Date unknown'}
                      </span>
                    </div>
                  </div>
                  <div className="recording-status">
                    <span className={`triage-badge ${getPredictionBadge(recording.prediction)}`}>
                      {recording.prediction || 'Pending'}
                    </span>
                    {recording.confidence && (
                      <span className="confidence-badge">
                        {`${(recording.confidence * 100).toFixed(1)}%`}
                      </span>
                    )}
                  </div>
                </div>

                {selectedRecording?.id === recording.id && (
                  <div className="recording-details-expanded">
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="detail-label">File Name</span>
                        <span className="detail-value">{recording.file_name || '—'}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Prediction</span>
                        <span className={`detail-value ${recording.prediction === 'RHD' ? 'rhd-positive' : 'rhd-negative'}`}>
                          {recording.prediction || 'Pending'}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Confidence</span>
                        <span className="detail-value">
                          {recording.confidence ? `${(recording.confidence * 100).toFixed(1)}%` : '—'}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Date Recorded</span>
                        <span className="detail-value">
                          {recording.recording_date 
                            ? new Date(recording.recording_date).toLocaleString()
                            : '—'}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Notes</span>
                        <span className="detail-value">{recording.notes || '—'}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Recorded At</span>
                        <span className="detail-value">
                          {recording.created_at 
                            ? new Date(recording.created_at).toLocaleString()
                            : '—'}
                        </span>
                      </div>
                    </div>

                    {recording.file_url && (
                      <div className="audio-player-wrapper">
                        <audio controls className="audio-player">
                          <source src={recording.file_url} type="audio/wav" />
                          Your browser does not support the audio element.
                        </audio>
                      </div>
                    )}

                    <div className="recording-actions">
                      {recording.file_url && (
                        <a 
                          href={recording.file_url} 
                          download={recording.file_name || 'recording.wav'}
                          className="btn-secondary"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                          </svg>
                          Download
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => !uploading && setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Upload Heart Sound Recording</h3>
              <button 
                className="modal-close" 
                onClick={() => !uploading && setShowUploadModal(false)}
                disabled={uploading}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <p>Upload a PCG (Phonocardiogram) recording for AI-powered RHD detection.</p>
              
              {uploading ? (
                <div className="upload-progress">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p>{uploadProgress < 100 ? 'Uploading and analyzing...' : 'Processing complete!'}</p>
                </div>
              ) : (
                <div className="upload-zone">
                  <div className="upload-icon">📤</div>
                  <p>Click to select an audio file</p>
                  <p className="upload-hint">Supports WAV, MP3, M4A formats</p>
                  <input
                    type="file"
                    accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp3"
                    onChange={handleFileUpload}
                    className="file-input"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Analysis Result Notification */}
      {analysisResult && (
        <div className="analysis-notification">
          <div className={`notification-content ${analysisResult.prediction === 'RHD' ? 'notification-warning' : 'notification-success'}`}>
            <h4>Analysis Complete</h4>
            <p>
              <strong>Prediction:</strong> {analysisResult.prediction}
              <span className="notification-confidence">
                ({`${(analysisResult.confidence * 100).toFixed(1)}% confidence`})
              </span>
            </p>
            <p className="notification-file">{analysisResult.file_name}</p>
            <button 
              className="btn-close-notification"
              onClick={() => setAnalysisResult(null)}
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecordingView;