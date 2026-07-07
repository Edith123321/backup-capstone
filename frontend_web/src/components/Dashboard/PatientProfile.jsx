import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patientService, screeningService } from '../../services/api';
import './PatientProfile.css';

const PatientProfile = () => {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  
  // State Management
  const [patient, setPatient] = useState(null);
  const [triageRecords, setTriageRecords] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  /**
   * FIX: RESET MECHANISM
   * This clears the state every time the ID in the URL changes.
   * This forces React to show the loading spinner and prevents showing old data.
   */
  useEffect(() => {
    console.log("🔄 Navigation detected. Loading Patient ID:", patientId);
    setPatient(null);
    setTriageRecords([]);
    setRecordings([]);
    setError(null);
    setLoading(true);
    setAnalysisResult(null);
    setActiveTab('overview');
  }, [patientId]);

  /**
   * DATA FETCHING LOGIC
   */
  const fetchPatientData = useCallback(async () => {
    if (authLoading || !isAuthenticated) return;
    if (!patientId) return;

    try {
      // API call to the unified backend
      const data = await patientService.getPatientDetails(patientId);
      
      if (data && data.patient) {
        setPatient(data.patient);
        setTriageRecords(data.triage || []);
        setRecordings(data.recordings || []);
        setError(null);
      } else {
        setError('Patient not found in the Saka database.');
      }
    } catch (err) {
      console.error('❌ Profile Fetch Error:', err);
      setError(err.message || 'Failed to load patient records from server.');
    } finally {
      setLoading(false);
    }
  }, [patientId, isAuthenticated, authLoading]);

  // Trigger fetch on mount or when ID/Auth changes
  useEffect(() => {
    fetchPatientData();
  }, [fetchPatientData]);

  /**
   * ANALYSIS HANDLERS (The AI "Brain" Integration)
   */
  const handleAnalyzeHeartSound = async (file) => {
    if (!file) return;
    setAnalyzing(true);
    setAnalysisResult(null);

    try {
      console.log("🧠 Sending audio to AI Model for Patient:", patientId);
      const predictResult = await screeningService.predict(file);
      
      setAnalysisResult({
        prediction: predictResult,
        timestamp: new Date().toISOString()
      });

      // Refresh data so the new recording appears in the list
      await fetchPatientData();
    } catch (err) {
      console.error("❌ Analysis Error:", err);
      alert(`AI Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) handleAnalyzeHeartSound(file);
  };

  /**
   * UI HELPERS
   */
  const getRHDStatusDisplay = (status) => {
    const statusMap = {
      'confirmed': { label: 'Confirmed RHD', color: '#dc2626', bg: '#fee2e2' },
      'suspected': { label: 'Suspected RHD', color: '#f59e0b', bg: '#fed7aa' },
      'none': { label: 'No RHD', color: '#22c55e', bg: '#dcfce7' },
      'unknown': { label: 'Unknown', color: '#94a3b8', bg: '#f1f5f9' }
    };
    return statusMap[status] || statusMap.unknown;
  };

  // 1. Loading State
  if (authLoading || (loading && !patient)) {
    return (
      <div className="profile-loading">
        <div className="loading-spinner"></div>
        <p>Synchronizing with Saka Backend...</p>
      </div>
    );
  }

  // 2. Auth/Error State
  if (!isAuthenticated) {
    return <div className="error-container"><h3>Please log in to access clinical data.</h3></div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <h3>Data Access Error</h3>
        <p>{error}</p>
        <button className="btn-primary" onClick={() => fetchPatientData()}>Retry Fetch</button>
        <button className="btn-secondary" onClick={() => navigate('/patients')}>Return to List</button>
      </div>
    );
  }

  // 3. Final Content View
  if (!patient) return null;
  const rhdStatus = getRHDStatusDisplay(patient.rhd_status || 'unknown');

  return (
    <div className="patient-profile-container fade-in">
      {/* HEADER SECTION */}
      <div className="profile-header">
        <div className="patient-info">
          <div className="patient-avatar-large">{patient.name?.charAt(0) || 'P'}</div>
          <div className="patient-details">
            <h1>{patient.name || 'Unnamed Patient'}</h1>
            <div className="patient-meta">
              <span>ID: {patient.id}</span>
              <span className="divider">|</span>
              <span>{patient.age || '—'} years</span>
              <span className="divider">|</span>
              <span style={{ color: rhdStatus.color, fontWeight: '600' }}>{rhdStatus.label}</span>
            </div>
          </div>
        </div>
        <div className="profile-actions">
          <button className="btn-secondary" onClick={() => navigate('/patients')}>Back</button>
          <button className="btn-primary" onClick={() => navigate(`/patient/${patientId}/triage/new`)}>New Triage</button>
          <div className="upload-wrapper">
             <input type="file" id="header-upload" accept=".wav" onChange={handleFileUpload} style={{display:'none'}} />
             <label htmlFor="header-upload" className="btn-primary">New Recording</label>
          </div>
        </div>
      </div>

      {/* TABS NAVIGATION */}
      <div className="profile-tabs">
        <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={`tab ${activeTab === 'encounters' ? 'active' : ''}`} onClick={() => setActiveTab('encounters')}>Encounters ({triageRecords.length})</button>
        <button className={`tab ${activeTab === 'recordings' ? 'active' : ''}`} onClick={() => setActiveTab('recordings')}>History ({recordings.length})</button>
        <button className={`tab ${activeTab === 'analysis' ? 'active' : ''}`} onClick={() => setActiveTab('analysis')}>AI Analysis</button>
      </div>

      {/* TAB CONTENT */}
      <div className="tab-content-area">
        {activeTab === 'overview' && (
          <div className="overview-grid">
            <div className="stats-grid">
              <div className="stat-card"><h3>{triageRecords.length + recordings.length}</h3><p>Total Encounters</p></div>
              <div className="stat-card"><h3>{recordings.length}</h3><p>AI Screenings</p></div>
              <div className="stat-card" style={{borderColor: rhdStatus.color}}><h3 style={{color: rhdStatus.color}}>{rhdStatus.label}</h3><p>Clinical Status</p></div>
            </div>
            
            <div className="info-card">
              <h3>Patient Demographics</h3>
              <div className="info-grid">
                <div className="info-item"><span className="label">Gender</span><span className="value">{patient.gender}</span></div>
                <div className="info-item"><span className="label">Contact</span><span className="value">{patient.contact || 'None'}</span></div>
                <div className="info-item"><span className="label">Location</span><span className="value">{patient.address || 'Gisozi, Kigali'}</span></div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'encounters' && (
          <div className="triage-table">
            {triageRecords.length === 0 ? <p className="empty-msg">No clinical triage history available.</p> : (
              <table>
                <thead><tr><th>Date</th><th>Triage Color</th><th>Notes</th></tr></thead>
                <tbody>
                  {triageRecords.map((t, i) => (
                    <tr key={i}>
                      <td>{new Date(t.created_at).toLocaleDateString()}</td>
                      <td><span className={`badge-${t.triage_color?.toLowerCase()}`}>{t.triage_color}</span></td>
                      <td>{t.notes || 'Routine checkup'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'recordings' && (
          <div className="recordings-grid">
            {recordings.length === 0 ? <p className="empty-msg">No heart sound recordings found.</p> : (
              recordings.map((r, i) => (
                <div key={i} className="recording-card">
                  <div className="rec-header">
                    <strong>{new Date(r.created_at).toLocaleDateString()}</strong>
                    <span className={r.prediction === 'RHD' ? 'badge-red' : 'badge-green'}>{r.prediction}</span>
                  </div>
                  <p>AI Confidence: {(r.confidence * 100).toFixed(1)}%</p>
                  {r.file_url && <audio controls src={r.file_url} />}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="analysis-pane">
            <div className="upload-box">
              <h3>Live RHD Classification</h3>
              <p>Upload a 10-second PCG sample from the Saka Stethoscope.</p>
              <input type="file" accept=".wav" onChange={handleFileUpload} disabled={analyzing} />
              {analyzing && <div className="analyzing-loader">Processing heart signatures...</div>}
            </div>

            {analysisResult && (
              <div className="result-display fade-in">
                <div className={`result-hero ${analysisResult.prediction.prediction === 'RHD' ? 'danger' : 'safe'}`}>
                  <h4>Result: {analysisResult.prediction.prediction}</h4>
                  <h2>{(analysisResult.prediction.confidence * 100).toFixed(1)}% Match</h2>
                </div>
                <div className="recommendation">
                   <strong>Clinical Guidance:</strong> {analysisResult.prediction.prediction === 'RHD' ? 'Immediate referral for Echocardiography required.' : 'No pathological murmurs detected. Resume annual screening.'}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientProfile;