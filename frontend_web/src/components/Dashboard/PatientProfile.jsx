// frontend_web/src/components/Dashboard/PatientProfile.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patientService, screeningService, databaseApi, reportService, prognosisService } from '../../services/api';
import Sidebar from './Sidebar';
import AnatomicalMap, { AnatomicalMapTrigger } from './AnatomicalMap';
import './DashboardLayout.css';
import './PatientProfile.css';

// ============================================
// SEVERITY GRADE HELPER
// ============================================
const getSeverityGrade = (prediction, confidence) => {
  if (!prediction || prediction === 'Unknown') {
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
// AUSCULTATION POINT DISPLAY
// ============================================
const AUSCULTATION_POINTS = {
  MV: { label: 'Mitral Valve', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.15)' },
  AV: { label: 'Aortic Valve', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  PV: { label: 'Pulmonary Valve', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)' },
  TV: { label: 'Tricuspid Valve', color: '#22c55e', bg: 'rgba(34, 197, 94, 0.15)' }
};

// ============================================
// MAIN COMPONENT
// ============================================
const PatientProfile = () => {
  // 1. HOOKS & ROUTING
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();

  // 2. STATE
  const [patient, setPatient] = useState(null);
  const [triageRecords, setTriageRecords] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showMap, setShowMap] = useState(false);
  const [selectedAuscultationPoint, setSelectedAuscultationPoint] = useState('MV');
  const [severityHistory, setSeverityHistory] = useState([]);
  const [prognosticRisk, setPrognosticRisk] = useState(null);
  const [followUpReminders, setFollowUpReminders] = useState([]);
  const [generatingReport, setGeneratingReport] = useState(false);

  // 3. EFFECTS
  // Reset state when patient ID changes
  useEffect(() => {
    setPatient(null);
    setTriageRecords([]);
    setRecordings([]);
    setError(null);
    setLoading(true);
    setAnalysisResult(null);
    setSeverityHistory([]);
    setPrognosticRisk(null);
    setFollowUpReminders([]);
  }, [id]);

  // Fetch patient data
  const fetchPatientData = useCallback(async () => {
    if (authLoading || !isAuthenticated || !id) return;

    try {
      setLoading(true);
      console.log('🔄 Fetching patient data for ID:', id);
      
      // Fetch patient details
      const data = await patientService.getPatientDetails(id);
      console.log('📊 Patient data received:', data);

      if (data?.patient) {
        setPatient(data.patient);
        setTriageRecords(data.triage || []);
        setRecordings(Array.isArray(data.recordings) ? data.recordings : []);
        setError(null);
        console.log(`✅ Loaded ${data.recordings?.length || 0} recordings`);
        
        // Fetch severity history
        try {
          const historyRes = await databaseApi.getSeverityHistory(id);
          if (historyRes.success) {
            setSeverityHistory(historyRes.history || []);
          }
        } catch (e) {
          console.warn('Could not fetch severity history:', e);
        }
        
        // Fetch prognostic risk (via the backend base URL, not the static host)
        try {
          const riskData = await prognosisService.getRisk(id);
          if (riskData.success) {
            setPrognosticRisk(riskData.prognosis);
          }
        } catch (e) {
          console.warn('Could not fetch prognostic risk:', e);
        }
        
        // Fetch follow-up reminders
        try {
          const reminderRes = await databaseApi.getFollowUpReminders(id);
          if (reminderRes.success) {
            setFollowUpReminders(reminderRes.reminders || []);
          }
        } catch (e) {
          console.warn('Could not fetch follow-up reminders:', e);
        }
      } else {
        setError('Patient record could not be found.');
      }
    } catch (err) {
      console.error('❌ Error fetching patient data:', err);
      setError(err.message || 'Error connecting to server.');
    } finally {
      setLoading(false);
    }
  }, [id, isAuthenticated, authLoading]);

  useEffect(() => {
    fetchPatientData();
  }, [fetchPatientData]);

  // 4. HANDLERS
  const handleAnalyzeHeartSound = async (file) => {
    if (!file) return;

    setAnalyzing(true);
    setAnalysisResult(null);
    setUploadProgress(0);

    try {
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);

      const doctorId = user?.doctor_id || user?.id;
      console.log('📤 Analyzing heart sound for patient:', id);
      
      // Include auscultation point
      const result = await screeningService.predict(
        file, 
        id, 
        doctorId,
        {
          auscultation_point: selectedAuscultationPoint,
          auscultation_label: AUSCULTATION_POINTS[selectedAuscultationPoint]?.label
        }
      );
      console.log('📊 Analysis result:', result);

      clearInterval(progressInterval);
      setUploadProgress(100);

      // Human-centered signal-quality gate: if the recording wasn't gradeable
      // (too short / too faint / not a heartbeat), show the guidance instead of
      // a misleading "Unknown" prediction.
      if (result.blocked) {
        const sq = result.signal_quality;
        alert(`${sq?.title || 'Recording not gradeable'}\n\n${sq?.message || result.error || 'Please re-record and try again.'}`);
        return;
      }
      // Surface soft warnings (noise / tachycardia / short) without blocking.
      (result.signal_quality?.warnings || []).forEach((w) =>
        console.warn('Signal note:', w.message)
      );

      const prediction = result.prediction || result.class || 'Unknown';
      const confidence = result.confidence || 0;
      const severity = getSeverityGrade(prediction, confidence);

      setAnalysisResult({
        prediction: {
          prediction: prediction,
          confidence: confidence,
          prob_normal: result.prob_normal || 0,
          prob_rhd: result.prob_rhd || 0,
          severity: severity,
          auscultation_point: selectedAuscultationPoint,
          auscultation_label: AUSCULTATION_POINTS[selectedAuscultationPoint]?.label
        },
        timestamp: new Date().toISOString(),
        recording_id: result.recording_id
      });

      await fetchPatientData();
      setActiveTab('recordings');

    } catch (err) {
      console.error('❌ Analysis error:', err);
      alert(`Analysis failed: ${err.message || 'Unknown error'}`);
    } finally {
      setAnalyzing(false);
      setUploadProgress(0);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/m4a', 'audio/x-m4a'];
      const validExtensions = ['.wav', '.mp3', '.m4a'];
      const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      if (!validTypes.includes(file.type) && !validExtensions.includes(fileExtension)) {
        alert('Please upload a valid audio file (WAV, MP3, or M4A)');
        return;
      }
      
      handleAnalyzeHeartSound(file);
    }
    event.target.value = '';
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const data = await reportService.generate({
        patient_id: id,
        symptoms: [],
        clinical_notes: 'Generated from patient profile',
        recommendations: [
          'Complete echocardiography',
          'Cardiology consultation within 30 days',
          'Continue monitoring symptoms'
        ]
      });

      if (data.success) {
        // Open the PDF on the backend (absolute URL, not the static host)
        window.open(reportService.downloadUrl(data.filename), '_blank');
      } else {
        alert('Failed to generate report: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report: ' + (error?.response?.data?.error || error.message));
    } finally {
      setGeneratingReport(false);
    }
  };

  // 5. HELPERS
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

  const getPredictionBadge = (prediction) => {
    if (!prediction || prediction === 'Unknown' || prediction === 'Pending') {
      return 'badge-gray';
    }
    return prediction === 'RHD' ? 'badge-red' : 'badge-green';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return '—';
    }
  };

  // 6. RENDER: LOADING
  if (authLoading || (loading && !patient)) {
    return (
      <div className="profile-loading">
        <div className="loading-spinner"></div>
        <p>Loading patient profile...</p>
      </div>
    );
  }

  // 7. RENDER: ERROR
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

  // 8. RENDER: MAIN
  if (!patient) return null;

  const rhdStatus = getRHDStatusDisplay(patient.rhd_status || 'unknown');
  const totalEncounters = triageRecords.length + recordings.length;
  const abnormalResults = triageRecords.filter(t =>
    t.triage_color === 'Red' || t.triage_color === 'Orange'
  ).length;
  const rhdRecordings = recordings.filter(r => r.prediction === 'RHD').length;
  const normalRecordings = recordings.filter(r => r.prediction === 'Normal').length;

  return (
    <div className="dashboard-layout-wrapper">
      <Sidebar user={user} />
      <div className="dashboard-content">
        <div className="dashboard-container">
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
          <AnatomicalMapTrigger
            selectedPoint={selectedAuscultationPoint}
            onClick={() => setShowMap(true)}
          />
          <button
            className="btn-primary"
            onClick={handleGenerateReport}
            disabled={generatingReport}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            {generatingReport ? 'Generating...' : 'Report'}
          </button>
        </div>
      </header>

      {/* ========== ANATOMICAL MAP ========== */}
      <AnatomicalMap
        selectedPoint={selectedAuscultationPoint}
        onPointSelect={(pointId) => {
          setSelectedAuscultationPoint(pointId);
          setShowMap(false);
        }}
        onClose={() => setShowMap(false)}
        isOpen={showMap}
        showLabels={true}
        interactive={true}
        size="medium"
      />

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
          className={`tab ${activeTab === 'prognosis' ? 'active' : ''}`}
          onClick={() => setActiveTab('prognosis')}
        >
          Prognosis
        </button>
      </nav>

      {/* ========== TAB CONTENT ========== */}
      <div className="tab-content">

        {/* --- OVERVIEW TAB --- */}
        {activeTab === 'overview' && (
          <section className="overview-section">
            {/* Stats remain the same */}
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
                <span className="stat-value">{rhdRecordings}</span>
                <span className="stat-label">RHD Detected</span>
              </div>
            </div>

            {/* Prognostic Risk Summary */}
            {prognosticRisk && (
              <div className="info-card" style={{ marginBottom: 20 }}>
                <h3 className="card-title">Prognostic Risk Assessment</h3>
                <div className="prognostic-summary">
                  <div className="prognostic-item">
                    <span className="prognostic-label">Risk Score</span>
                    <span className={`prognostic-value ${prognosticRisk?.prognosis?.risk_level?.toLowerCase() || 'unknown'}`}>
                      {prognosticRisk?.prognosis?.risk_score || '—'}%
                    </span>
                  </div>
                  <div className="prognostic-item">
                    <span className="prognostic-label">Risk Level</span>
                    <span className={`prognostic-value ${prognosticRisk?.prognosis?.risk_level?.toLowerCase() || 'unknown'}`}>
                      {prognosticRisk?.prognosis?.risk_level || 'Unknown'}
                    </span>
                  </div>
                  <div className="prognostic-item">
                    <span className="prognostic-label">Next State</span>
                    <span className="prognostic-value">
                      {prognosticRisk?.prognosis?.next_state_most_likely || '—'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Follow-up Reminders */}
            {followUpReminders.length > 0 && (
              <div className="info-card" style={{ marginBottom: 20 }}>
                <h3 className="card-title">Follow-up Reminders</h3>
                <div className="reminders-list">
                  {followUpReminders.map((reminder, idx) => (
                    <div key={idx} className="reminder-item">
                      <span className="reminder-days">{reminder.recommended_days} days</span>
                      <span className="reminder-reason">{reminder.reason}</span>
                      <span className="reminder-date">
                        {formatDate(reminder.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Severity Summary */}
            {recordings.length > 0 && (
              <div className="info-card" style={{ marginBottom: 20 }}>
                <h3 className="card-title">Severity Summary</h3>
                <div className="severity-summary">
                  {recordings.slice(0, 5).map((rec, idx) => {
                    const severity = getSeverityGrade(rec.prediction, rec.confidence);
                    const auscultation = rec.auscultation_point ? AUSCULTATION_POINTS[rec.auscultation_point] : null;
                    return (
                      <div key={idx} className="severity-item">
                        <span className="severity-date">
                          {formatDate(rec.recording_date || rec.created_at)}
                        </span>
                        <span 
                          className="severity-badge"
                          style={{ 
                            backgroundColor: severity.bg,
                            color: severity.color
                          }}
                        >
                          Grade {severity.grade}: {severity.label}
                        </span>
                        {auscultation && (
                          <span 
                            className="auscultation-badge"
                            style={{ 
                              backgroundColor: auscultation.bg,
                              color: auscultation.color
                            }}
                          >
                            {auscultation.label}
                          </span>
                        )}
                        <span className="severity-confidence">
                          {rec.confidence ? `${(rec.confidence * 100).toFixed(1)}%` : '—'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Patient Information */}
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
                  .sort((a, b) => {
                    const dateA = new Date(a.created_at || a.recording_date || 0);
                    const dateB = new Date(b.created_at || b.recording_date || 0);
                    return dateB - dateA;
                  })
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
                          {formatDate(item.created_at || item.recording_date)}
                          {item.triage_color && (
                            <span className={`triage-badge ${getRiskBadgeClass(item.triage_color)}`}>
                              {item.triage_color}
                            </span>
                          )}
                          {item.prediction && (
                            <span className={`triage-badge ${getPredictionBadge(item.prediction)}`}>
                              {item.prediction}
                            </span>
                          )}
                          {item.confidence && (
                            <span className="confidence-badge">
                              {`${(item.confidence * 100).toFixed(1)}%`}
                            </span>
                          )}
                          {item.auscultation_point && (
                            <span 
                              className="auscultation-badge-small"
                              style={{
                                backgroundColor: AUSCULTATION_POINTS[item.auscultation_point]?.bg || '#f1f5f9',
                                color: AUSCULTATION_POINTS[item.auscultation_point]?.color || '#94a3b8'
                              }}
                            >
                              {item.auscultation_point}
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
                        <td>{formatDate(triage.created_at)}</td>
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
              <div className="tab-actions">
                <AnatomicalMapTrigger
                  selectedPoint={selectedAuscultationPoint}
                  onClick={() => setShowMap(true)}
                  compact={true}
                />
                <label className="btn-primary btn-upload">
                  + Upload
                  <input
                    type="file"
                    accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp3"
                    onChange={handleFileUpload}
                    disabled={analyzing}
                    hidden
                  />
                </label>
              </div>
            </div>

            {analyzing && (
              <div className="upload-progress-container">
                <div className="upload-progress-bar">
                  <div 
                    className="upload-progress-fill" 
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p className="upload-progress-text">
                  {uploadProgress < 100 ? 'Uploading and analyzing...' : 'Processing complete!'}
                </p>
              </div>
            )}

            {recordings.length === 0 ? (
              <div className="empty-state">
                <p>No heart sound recordings available.</p>
                <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginTop: '8px' }}>
                  Upload a recording using the button above to get AI analysis.
                </p>
              </div>
            ) : (
              <div className="recordings-grid">
                {recordings.map((recording, index) => {
                  const severity = getSeverityGrade(recording.prediction, recording.confidence);
                  const auscultation = recording.auscultation_point ? AUSCULTATION_POINTS[recording.auscultation_point] : null;
                  return (
                    <div key={recording.id || index} className="recording-card">
                      <div className="recording-header">
                        <h4>Recording #{index + 1}</h4>
                        <div className="recording-badges">
                          <span className={`triage-badge ${getPredictionBadge(recording.prediction)}`}>
                            {recording.prediction || 'Pending'}
                          </span>
                          {recording.prediction && recording.prediction !== 'Pending' && (
                            <span 
                              className="severity-badge-small"
                              style={{ 
                                backgroundColor: severity.bg,
                                color: severity.color
                              }}
                            >
                              Grade {severity.grade}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="recording-details">
                        <div className="detail-row">
                          <span className="detail-label">Date</span>
                          <span className="detail-value">
                            {formatDate(recording.recording_date || recording.created_at)}
                          </span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">Confidence</span>
                          <span className="detail-value">
                            {recording.confidence !== null && recording.confidence !== undefined
                              ? `${(recording.confidence * 100).toFixed(1)}%`
                              : '—'}
                          </span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">Severity</span>
                          <span className="detail-value" style={{ color: severity.color }}>
                            {severity.label}
                          </span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">Auscultation</span>
                          <span className="detail-value">
                            {auscultation ? (
                              <span 
                                className="auscultation-badge"
                                style={{ 
                                  backgroundColor: auscultation.bg,
                                  color: auscultation.color,
                                  padding: '2px 8px',
                                  borderRadius: '12px',
                                  fontSize: '0.75rem'
                                }}
                              >
                                {auscultation.label}
                              </span>
                            ) : '—'}
                          </span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">File</span>
                          <span className="detail-value">{recording.file_name || '—'}</span>
                        </div>
                        {recording.notes && (
                          <div className="detail-row">
                            <span className="detail-label">Notes</span>
                            <span className="detail-value">{recording.notes}</span>
                          </div>
                        )}
                      </div>
                      {recording.file_url && (
                        <audio controls className="audio-player">
                          <source src={recording.file_url} type="audio/wav" />
                          Your browser does not support the audio element.
                        </audio>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* --- PROGNOSIS TAB --- */}
        {activeTab === 'prognosis' && (
          <section className="prognosis-section">
            <div className="prognosis-container">
              <h2>Prognostic Risk Assessment</h2>
              
              {!prognosticRisk ? (
                <div className="empty-state">
                  <p>No prognostic data available.</p>
                  <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginTop: '8px' }}>
                    More assessments needed for prognosis calculation.
                  </p>
                </div>
              ) : (
                <div className="prognosis-card">
                  <div className="prognosis-header">
                    <div className="prognosis-score">
                      <span className="score-label">Risk Score</span>
                      <span className={`score-value ${prognosticRisk?.prognosis?.risk_level?.toLowerCase() || 'unknown'}`}>
                        {prognosticRisk?.prognosis?.risk_score || '—'}%
                      </span>
                    </div>
                    <div className="prognosis-level">
                      <span className="level-label">Risk Level</span>
                      <span className={`level-value ${prognosticRisk?.prognosis?.risk_level?.toLowerCase() || 'unknown'}`}>
                        {prognosticRisk?.prognosis?.risk_level || 'Unknown'}
                      </span>
                    </div>
                    <div className="prognosis-confidence">
                      <span className="confidence-label">Confidence</span>
                      <span className="confidence-value">
                        {prognosticRisk?.prognosis?.confidence || '—'}%
                      </span>
                    </div>
                  </div>

                  <div className="prognosis-details">
                    <div className="detail-section">
                      <h4>Probabilities</h4>
                      <div className="probability-bars">
                        {Object.entries(prognosticRisk?.prognosis?.probabilities || {}).map(([state, prob]) => (
                          <div key={state} className="probability-item">
                            <span className="prob-label">{state}</span>
                            <div className="prob-bar-container">
                              <div 
                                className="prob-bar"
                                style={{ 
                                  width: `${(prob * 100)}%`,
                                  backgroundColor: prob > 0.3 ? '#00464F' : '#94a3b8'
                                }}
                              />
                            </div>
                            <span className="prob-value">{(prob * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="detail-section">
                      <h4>Recommendations</h4>
                      <ul className="recommendation-list">
                        {prognosticRisk?.prognosis?.recommendations?.map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="detail-section">
                      <h4>Next Most Likely State</h4>
                      <p className="next-state">
                        {prognosticRisk?.prognosis?.next_state_most_likely || 'Unknown'}
                      </p>
                    </div>

                    <div className="detail-section">
                      <h4>Treatment Effect</h4>
                      <p className="treatment-effect">
                        {prognosticRisk?.prognosis?.treatment_effect || '—'}% risk reduction
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

          </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientProfile;