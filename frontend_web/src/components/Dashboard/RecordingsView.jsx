// frontend_web/src/components/Dashboard/RecordingView.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patientService, screeningService, databaseApi } from '../../services/api';
import './RecordingView.css';

// ============================================
// AUSCULTATION POINT OPTIONS
// ============================================
const AUSCULTATION_POINTS = {
  MV: { 
    id: 'MV', 
    label: 'Mitral Valve (MV)', 
    description: 'Apex / 5th intercostal space',
    icon: '🫀',
    color: '#3b82f6'
  },
  AV: { 
    id: 'AV', 
    label: 'Aortic Valve (AV)', 
    description: 'Right upper sternal border',
    icon: '❤️',
    color: '#ef4444'
  },
  PV: { 
    id: 'PV', 
    label: 'Pulmonary Valve (PV)', 
    description: 'Left upper sternal border',
    icon: '💙',
    color: '#8b5cf6'
  },
  TV: { 
    id: 'TV', 
    label: 'Tricuspid Valve (TV)', 
    description: 'Left lower sternal border',
    icon: '💚',
    color: '#22c55e'
  }
};

// ============================================
// SEVERITY GRADE HELPER
// ============================================
const getSeverityGrade = (prediction, confidence) => {
  if (!prediction || prediction === 'Unknown' || prediction === 'Pending') {
    return { grade: 'N/A', label: 'Pending', color: '#94a3b8', bg: '#f1f5f9' };
  }
  
  if (prediction === 'Normal') {
    if (confidence > 0.8) {
      return { grade: '0', label: 'Normal', color: '#22c55e', bg: '#dcfce7' };
    } else {
      return { grade: '1', label: 'Monitor', color: '#f59e0b', bg: '#fed7aa' };
    }
  }
  
  if (prediction === 'RHD') {
    if (confidence > 0.8) {
      return { grade: '2', label: 'Definite RHD', color: '#dc2626', bg: '#fee2e2' };
    } else if (confidence > 0.6) {
      return { grade: '2', label: 'Possible RHD', color: '#ea580c', bg: '#ffedd5' };
    } else {
      return { grade: '1', label: 'Monitor', color: '#f59e0b', bg: '#fed7aa' };
    }
  }
  
  return { grade: 'N/A', label: 'Unknown', color: '#94a3b8', bg: '#f1f5f9' };
};

// ============================================
// MAIN COMPONENT
// ============================================
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
  const [selectedPoint, setSelectedPoint] = useState('MV');
  const [showAnatomicalMap, setShowAnatomicalMap] = useState(false);

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

      // Get the selected auscultation point
      const auscultationPoint = AUSCULTATION_POINTS[selectedPoint];
      
      // Analyze the heart sound with auscultation point
      const result = await screeningService.predict(file, patientId, user?.doctor_id || user?.id);
      
      clearInterval(progressInterval);
      setUploadProgress(100);

      // Save recording to database with auscultation point
      if (result.success || result.prediction) {
        const recordingData = {
          patient_id: patientId,
          doctor_id: user?.doctor_id || user?.id,
          file_name: file.name,
          prediction: result.prediction || result.class || 'Unknown',
          confidence: result.confidence || 0,
          recording_date: new Date().toISOString(),
          auscultation_point: selectedPoint,
          auscultation_label: auscultationPoint.label,
          notes: `Uploaded and analyzed on ${new Date().toLocaleString()} - ${auscultationPoint.label}`
        };

        // Save via database API
        const saveResult = await databaseApi.saveRecording(recordingData);
        
        if (saveResult.success) {
          // Refresh recordings list
          await fetchData();
        }

        const severity = getSeverityGrade(result.prediction || result.class, result.confidence);
        
        setAnalysisResult({
          prediction: result.prediction || result.class || 'Unknown',
          confidence: result.confidence || 0,
          prob_normal: result.prob_normal || 0,
          prob_rhd: result.prob_rhd || 0,
          timestamp: new Date().toISOString(),
          file_name: file.name,
          auscultation_point: selectedPoint,
          auscultation_label: auscultationPoint.label,
          severity: severity
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

  // Get auscultation point display
  const getAuscultationDisplay = (pointId) => {
    const point = AUSCULTATION_POINTS[pointId];
    if (!point) return null;
    return (
      <span className="auscultation-badge" style={{ backgroundColor: point.color + '20', color: point.color }}>
        {point.icon} {point.label}
      </span>
    );
  };

  // Get prediction badge class
  const getPredictionBadge = (prediction) => {
    if (!prediction || prediction === 'Unknown' || prediction === 'Pending') return 'badge-gray';
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

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return '—';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return '—';
    }
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

  // Calculate stats
  const totalRecordings = recordings.length;
  const rhdDetected = recordings.filter(r => r.prediction === 'RHD').length;
  const normalRecordings = recordings.filter(r => r.prediction === 'Normal').length;
  const pendingRecordings = recordings.filter(r => !r.prediction || r.prediction === 'Unknown' || r.prediction === 'Pending').length;

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
          <span className="stat-number">{totalRecordings}</span>
          <span className="stat-label">Total Recordings</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{rhdDetected}</span>
          <span className="stat-label">RHD Detected</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{normalRecordings}</span>
          <span className="stat-label">Normal</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{pendingRecordings}</span>
          <span className="stat-label">Pending Analysis</span>
        </div>
      </div>

      {/* Auscultation Point Filter */}
      <div className="filter-section">
        <div className="filter-label">Filter by Auscultation Point:</div>
        <div className="filter-buttons">
          <button 
            className={`filter-btn ${selectedPoint === 'MV' ? 'active' : ''}`}
            onClick={() => setSelectedPoint('MV')}
          >
            <span style={{ color: AUSCULTATION_POINTS.MV.color }}>🫀</span> MV
          </button>
          <button 
            className={`filter-btn ${selectedPoint === 'AV' ? 'active' : ''}`}
            onClick={() => setSelectedPoint('AV')}
          >
            <span style={{ color: AUSCULTATION_POINTS.AV.color }}>❤️</span> AV
          </button>
          <button 
            className={`filter-btn ${selectedPoint === 'PV' ? 'active' : ''}`}
            onClick={() => setSelectedPoint('PV')}
          >
            <span style={{ color: AUSCULTATION_POINTS.PV.color }}>💙</span> PV
          </button>
          <button 
            className={`filter-btn ${selectedPoint === 'TV' ? 'active' : ''}`}
            onClick={() => setSelectedPoint('TV')}
          >
            <span style={{ color: AUSCULTATION_POINTS.TV.color }}>💚</span> TV
          </button>
          <button 
            className={`filter-btn ${selectedPoint === 'all' ? 'active' : ''}`}
            onClick={() => setSelectedPoint('all')}
          >
            All
          </button>
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
            {recordings
              .filter(r => selectedPoint === 'all' || r.auscultation_point === selectedPoint)
              .map((recording) => {
                const severity = getSeverityGrade(recording.prediction, recording.confidence);
                return (
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
                            {formatDate(recording.recording_date || recording.created_at)}
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

                    <div className="recording-meta">
                      {recording.auscultation_point && (
                        <span className="auscultation-badge" style={{ 
                          backgroundColor: AUSCULTATION_POINTS[recording.auscultation_point]?.color + '20',
                          color: AUSCULTATION_POINTS[recording.auscultation_point]?.color
                        }}>
                          {AUSCULTATION_POINTS[recording.auscultation_point]?.icon} 
                          {AUSCULTATION_POINTS[recording.auscultation_point]?.label || recording.auscultation_point}
                        </span>
                      )}
                      {recording.prediction && recording.prediction !== 'Pending' && (
                        <span 
                          className="severity-badge-small"
                          style={{ 
                            backgroundColor: severity.bg,
                            color: severity.color
                          }}
                        >
                          Grade {severity.grade}: {severity.label}
                        </span>
                      )}
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
                            <span className="detail-label">Severity Grade</span>
                            <span className="detail-value" style={{ color: severity.color }}>
                              {severity.label}
                            </span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Auscultation Point</span>
                            <span className="detail-value">
                              {recording.auscultation_point ? 
                                AUSCULTATION_POINTS[recording.auscultation_point]?.label || recording.auscultation_point 
                                : '—'}
                            </span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Date Recorded</span>
                            <span className="detail-value">
                              {formatDate(recording.recording_date || recording.created_at)}
                            </span>
                          </div>
                          {recording.notes && (
                            <div className="detail-item full-width">
                              <span className="detail-label">Notes</span>
                              <span className="detail-value">{recording.notes}</span>
                            </div>
                          )}
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
                          <button 
                            className="btn-secondary"
                            onClick={(e) => {
                              e.stopPropagation();
                              // Navigate to analysis
                              navigate(`/patient/${patientId}/analysis/${recording.id}`);
                            }}
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                              <circle cx="12" cy="12" r="3"/>
                            </svg>
                            View Analysis
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* Upload Modal with Auscultation Point Selection */}
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
              
              {/* Auscultation Point Selection */}
              <div className="auscultation-selector">
                <label className="selector-label">Auscultation Point:</label>
                <div className="selector-options">
                  {Object.values(AUSCULTATION_POINTS).map((point) => (
                    <button
                      key={point.id}
                      className={`selector-btn ${selectedPoint === point.id ? 'active' : ''}`}
                      onClick={() => setSelectedPoint(point.id)}
                      style={{
                        borderColor: selectedPoint === point.id ? point.color : '#e2e8f0',
                        backgroundColor: selectedPoint === point.id ? point.color + '20' : 'transparent'
                      }}
                    >
                      <span style={{ fontSize: '1.2rem' }}>{point.icon}</span>
                      <span>{point.id}</span>
                      <span className="selector-label-small">{point.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              
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
                  <p className="upload-hint" style={{ color: '#3b82f6', fontWeight: '500' }}>
                    Selected: {AUSCULTATION_POINTS[selectedPoint]?.label || 'None'}
                  </p>
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
            <p>
              <strong>Severity:</strong> Grade {analysisResult.severity.grade} - {analysisResult.severity.label}
            </p>
            <p>
              <strong>Auscultation:</strong> {analysisResult.auscultation_label}
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