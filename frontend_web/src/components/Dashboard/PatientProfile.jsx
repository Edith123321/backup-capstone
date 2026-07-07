// frontend_web/src/components/Dashboard/PatientProfile.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patientService, screeningService } from '../../services/api';
import './PatientProfile.css';

const PatientProfile = () => {
  // ============================================
  // 1. HOOKS & ROUTING
  // ============================================
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();

  // ============================================
  // 2. STATE
  // ============================================
  const [patient, setPatient] = useState(null);
  const [triageRecords, setTriageRecords] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  // ============================================
  // 3. EFFECTS
  // ============================================
  
  // Reset state when patient ID changes
  useEffect(() => {
    setPatient(null);
    setTriageRecords([]);
    setRecordings([]);
    setError(null);
    setLoading(true);
    setAnalysisResult(null);
  }, [id]);

  // Fetch patient data
  const fetchPatientData = useCallback(async () => {
    if (authLoading || !isAuthenticated || !id) return;

    try {
      const data = await patientService.getPatientDetails(id);
      
      if (data?.patient) {
        setPatient(data.patient);
        setTriageRecords(data.triage || []);
        setRecordings(data.recordings || []);
        setError(null);
      } else {
        setError('Patient record could not be found.');
      }
    } catch (err) {
      console.error('Error fetching patient data:', err);
      setError(err.message || 'Error connecting to server.');
    } finally {
      setLoading(false);
    }
  }, [id, isAuthenticated, authLoading]);

  useEffect(() => {
    fetchPatientData();
  }, [fetchPatientData]);

  // ============================================
  // 4. HANDLERS
  // ============================================
  
  const handleAnalyzeHeartSound = async (file) => {
    if (!file) return;
    
    setAnalyzing(true);
    setAnalysisResult(null);

    try {
      const result = await screeningService.predict(file);
      
      setAnalysisResult({
        prediction: result,
        timestamp: new Date().toISOString()
      });

      await fetchPatientData();
    } catch (err) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      handleAnalyzeHeartSound(file);
    }
  };

  // ============================================
  // 5. HELPERS
  // ============================================
  
  const getRHDStatusDisplay = (status) => {
    const statusMap = {
      'confirmed': { label: 'Confirmed RHD', color: '#dc2626', bg: '#fee2e2' },
      'suspected': { label: 'Suspected RHD', color: '#f59e0b', bg: '#fed7aa' },
      'none': { label: 'No RHD', color: '#22c55e', bg: '#dcfce7' },
      'unknown': { label: 'Unknown', color: '#94a3b8', bg: '#f1f5f9' }
    };
    return statusMap[status] || statusMap.unknown;
  };

  const getRiskBadgeClass = (color) => {
    const classes = {
      'Red': 'badge-red',
      'Orange': 'badge-orange',
      'Yellow': 'badge-yellow',
      'Green': 'badge-green',
      'Blue': 'badge-blue'
    };
    return classes[color] || 'badge-gray';
  };

  // ============================================
  // 6. RENDER: LOADING
  // ============================================
  
  if (authLoading || (loading && !patient)) {
    return (
      <div className="profile-loading">
        <div className="loading-spinner"></div>
        <p>Loading patient profile...</p>
      </div>
    );
  }

  // ============================================
  // 7. RENDER: ERROR
  // ============================================
  
  if (error) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠️</div>
        <h3>Unable to Load Patient</h3>
        <p>{error}</p>
        <div className="error-actions">
          <button className="btn-primary" onClick={fetchPatientData}>
            Retry
          </button>
          <button className="btn-secondary" onClick={() => navigate('/patients')}>
            Back to Patients
          </button>
        </div>
      </div>
    );
  }

  // ============================================
  // 8. RENDER: MAIN
  // ============================================
  
  if (!patient) return null;

  const rhdStatus = getRHDStatusDisplay(patient.rhd_status || 'unknown');
  const totalEncounters = triageRecords.length + recordings.length;
  const abnormalResults = triageRecords.filter(t => 
    t.triage_color === 'Red' || t.triage_color === 'Orange'
  ).length;

  return (
    <div className="patient-profile-container">
      
      {/* ========== HEADER ========== */}
      <header className="profile-header">
        <div className="patient-info">
          <div className="patient-avatar-large">
            {patient.name?.charAt(0) || 'P'}
          </div>
          <div className="patient-details">
            <h1>{patient.name || 'Unnamed Patient'}</h1>
            <div className="patient-meta">
              <span className="meta-item">
                <strong>ID:</strong> {patient.id}
              </span>
              <span className="meta-divider">|</span>
              <span className="meta-item">
                <strong>Age:</strong> {patient.age || '—'} years
              </span>
              <span className="meta-divider">|</span>
              <span className="meta-item">
                <strong>Gender:</strong> {patient.gender || 'Not specified'}
              </span>
              <span className="meta-divider">|</span>
              <span 
                className="status-indicator" 
                style={{ color: rhdStatus.color }}
              >
                ● {rhdStatus.label}
              </span>
            </div>
          </div>
        </div>
        
        <div className="profile-actions">
          <button 
            className="btn-secondary" 
            onClick={() => navigate('/patients')}
          >
            ← Back
          </button>
          <button 
            className="btn-primary" 
            onClick={() => navigate(`/patient/${id}/triage/new`)}
          >
            + New Triage
          </button>
          <label className="btn-primary btn-upload">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Analyze Sound
            <input 
              type="file" 
              accept=".wav,.mp3,.m4a" 
              onChange={handleFileUpload}
              disabled={analyzing}
              hidden 
            />
          </label>
        </div>
      </header>

      {/* ========== TABS ========== */}
      <nav className="profile-tabs">
        <button 
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`tab ${activeTab === 'encounters' ? 'active' : ''}`}
          onClick={() => setActiveTab('encounters')}
        >
          Encounters ({totalEncounters})
        </button>
        <button 
          className={`tab ${activeTab === 'recordings' ? 'active' : ''}`}
          onClick={() => setActiveTab('recordings')}
        >
          Recordings ({recordings.length})
        </button>
        <button 
          className={`tab ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          AI Analysis
        </button>
      </nav>

      {/* ========== TAB CONTENT ========== */}
      <div className="tab-content">
        
        {/* --- OVERVIEW TAB --- */}
        {activeTab === 'overview' && (
          <section className="overview-section">
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-value">{totalEncounters}</span>
                <span className="stat-label">Total Encounters</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{recordings.length}</span>
                <span className="stat-label">Heart Sound Recordings</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{abnormalResults}</span>
                <span className="stat-label">Abnormal Results</span>
              </div>
              <div className="stat-card" style={{ borderColor: rhdStatus.color }}>
                <span className="stat-value" style={{ color: rhdStatus.color }}>
                  {rhdStatus.label}
                </span>
                <span className="stat-label">RHD Status</span>
              </div>
            </div>
            
            <div className="info-card">
              <h3 className="card-title">Patient Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">Full Name</span>
                  <span className="value">{patient.name || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Age</span>
                  <span className="value">{patient.age || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Gender</span>
                  <span className="value">{patient.gender || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Contact</span>
                  <span className="value">{patient.contact || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Address</span>
                  <span className="value">{patient.address || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Date of Birth</span>
                  <span className="value">{patient.dob || '—'}</span>
                </div>
                <div className="info-item">
                  <span className="label">RHD Status</span>
                  <span className="value" style={{ color: rhdStatus.color, fontWeight: '600' }}>
                    {rhdStatus.label}
                  </span>
                </div>
                <div className="info-item">
                  <span className="label">Doctor ID</span>
                  <span className="value">{patient.doctor_id || '—'}</span>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="recent-activity">
              <h3 className="card-title">Recent Activity</h3>
              {totalEncounters === 0 ? (
                <div className="activity-item">
                  <div className="activity-icon">📋</div>
                  <div className="activity-content">
                    <span className="activity-title">No recent activity</span>
                    <span className="activity-date">—</span>
                  </div>
                </div>
              ) : (
                [...triageRecords, ...recordings]
                  .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                  .slice(0, 5)
                  .map((item, index) => (
                    <div key={index} className="activity-item">
                      <div className="activity-icon">
                        {item.triage_color ? '🏥' : '🎵'}
                      </div>
                      <div className="activity-content">
                        <span className="activity-title">
                          {item.triage_color ? 'Triage Assessment' : 'Heart Sound Recording'}
                        </span>
                        <span className="activity-date">
                          {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Recent'}
                          {item.triage_color && (
                            <span className={`triage-badge ${getRiskBadgeClass(item.triage_color)}`}>
                              {item.triage_color}
                            </span>
                          )}
                          {item.prediction && (
                            <span className={`triage-badge ${item.prediction === 'RHD' ? 'badge-red' : 'badge-green'}`}>
                              {item.prediction}
                            </span>
                          )}
                        </span>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </section>
        )}

        {/* --- ENCOUNTERS TAB --- */}
        {activeTab === 'encounters' && (
          <section className="encounters-section">
            <div className="tab-header">
              <h2>Triage Encounters</h2>
              <button 
                className="btn-primary" 
                onClick={() => navigate(`/patient/${id}/triage/new`)}
              >
                + New Triage
              </button>
            </div>
            
            {triageRecords.length === 0 ? (
              <div className="empty-state">
                <p>No triage records found for this patient.</p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Risk Level</th>
                      <th>Score</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {triageRecords.map((triage, index) => (
                      <tr key={index}>
                        <td>{triage.created_at ? new Date(triage.created_at).toLocaleDateString() : '—'}</td>
                        <td>
                          <span className={`triage-badge ${getRiskBadgeClass(triage.triage_color)}`}>
                            {triage.triage_color || 'Pending'}
                          </span>
                        </td>
                        <td>{triage.triage_score || '—'}</td>
                        <td>{triage.notes || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {/* --- RECORDINGS TAB --- */}
        {activeTab === 'recordings' && (
          <section className="recordings-section">
            <div className="tab-header">
              <h2>Heart Sound Recordings</h2>
              <label className="btn-primary btn-upload">
                + Upload Recording
                <input 
                  type="file" 
                  accept=".wav,.mp3,.m4a" 
                  onChange={handleFileUpload}
                  disabled={analyzing}
                  hidden 
                />
              </label>
            </div>

            {recordings.length === 0 ? (
              <div className="empty-state">
                <p>No heart sound recordings available.</p>
              </div>
            ) : (
              <div className="recordings-grid">
                {recordings.map((recording, index) => (
                  <div key={index} className="recording-card">
                    <div className="recording-header">
                      <h4>Recording #{index + 1}</h4>
                      <span className={`triage-badge ${recording.prediction === 'RHD' ? 'badge-red' : 'badge-green'}`}>
                        {recording.prediction || 'Pending'}
                      </span>
                    </div>
                    <div className="recording-details">
                      <div className="detail-row">
                        <span className="detail-label">Date</span>
                        <span className="detail-value">
                          {recording.created_at ? new Date(recording.created_at).toLocaleDateString() : '—'}
                        </span>
                      </div>
                      <div className="detail-row">
                        <span className="detail-label">Confidence</span>
                        <span className="detail-value">
                          {recording.confidence ? `${(recording.confidence * 100).toFixed(1)}%` : '—'}
                        </span>
                      </div>
                    </div>
                    {recording.file_url && (
                      <audio controls className="audio-player">
                        <source src={recording.file_url} type="audio/wav" />
                      </audio>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* --- ANALYSIS TAB --- */}
        {activeTab === 'analysis' && (
          <section className="analysis-section">
            <div className="analysis-container">
              <div className="upload-zone">
                <h3>AI Heart Sound Analysis</h3>
                <p>Upload a PCG sample from the IoT stethoscope for automated valvular analysis.</p>
                <label className="upload-btn">
                  {analyzing ? 'Analyzing...' : 'Select Audio File'}
                  <input 
                    type="file" 
                    accept=".wav,.mp3,.m4a" 
                    onChange={handleFileUpload}
                    disabled={analyzing}
                    hidden 
                  />
                </label>
                {analyzing && (
                  <div className="analyzing-indicator">
                    <div className="pulse-loader"></div>
                    <span>Processing heart sound...</span>
                  </div>
                )}
              </div>

              {analysisResult && (
                <div className="analysis-result-card">
                  <div className={`analysis-header ${analysisResult.prediction?.prediction === 'RHD' ? 'bg-red' : 'bg-green'}`}>
                    <h4>Classification Result</h4>
                    <div className="result-value">
                      {analysisResult.prediction?.prediction || 'Unknown'}
                    </div>
                    <div className="confidence-score">
                      Confidence: {analysisResult.prediction?.confidence 
                        ? `${(analysisResult.prediction.confidence * 100).toFixed(1)}%` 
                        : '—'}
                    </div>
                  </div>
                  <div className="analysis-body">
                    <p className="recommendation">
                      <strong>Recommendation:</strong> 
                      {analysisResult.prediction?.prediction === 'RHD' 
                        ? ' Immediate referral for specialist echocardiography recommended.' 
                        : ' Findings normal. Schedule routine follow-up in 12 months.'}
                    </p>
                    <p className="timestamp">
                      Processed: {new Date(analysisResult.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

      </div>
    </div>
  );
};

export default PatientProfile;