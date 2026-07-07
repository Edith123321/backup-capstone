import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patientService, screeningService } from '../../services/api';
import './PatientProfile.css';

const PatientProfile = () => {
  // 1. Hook into the URL parameter ":id"
  const { id } = useParams(); 
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  
  // 2. Component State
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
   * This effect runs the moment the ID in the URL changes.
   * It wipes the old patient data so you don't see "Patient A" while "Patient B" is loading.
   */
  useEffect(() => {
    setPatient(null);
    setTriageRecords([]);
    setRecordings([]);
    setError(null);
    setLoading(true);
    setAnalysisResult(null);
    console.log("🚩 Navigation: Resetting view for Patient ID:", id);
  }, [id]);

  /**
   * DATA FETCHING
   */
  const fetchPatientData = useCallback(async () => {
    if (authLoading || !isAuthenticated) return;
    if (!id) return;

    try {
      console.log('🛰️ Fetching fresh data for:', id);
      const data = await patientService.getPatientDetails(id);
      
      if (data && data.patient) {
        setPatient(data.patient);
        setTriageRecords(data.triage || []);
        setRecordings(data.recordings || []);
        setError(null);
      } else {
        setError('Patient record could not be found.');
      }
    } catch (err) {
      console.error('❌ Data Fetch Error:', err);
      setError(err.message || 'Error connecting to Saka cloud services.');
    } finally {
      setLoading(false);
    }
  }, [id, isAuthenticated, authLoading]);

  // Execute fetch when component mounts or ID changes
  useEffect(() => {
    fetchPatientData();
  }, [fetchPatientData]);

  /**
   * AI ANALYSIS LOGIC
   */
  const handleAnalyzeHeartSound = async (file) => {
    if (!file) return;
    setAnalyzing(true);
    setAnalysisResult(null);

    try {
      // Direct call to your FastAPI/Flask prediction endpoint
      const result = await screeningService.predict(file);
      
      setAnalysisResult({
        prediction: result,
        timestamp: new Date().toISOString()
      });

      // Reload history to show the new recording
      await fetchPatientData();
    } catch (err) {
      alert(`AI Processing Failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  /**
   * UI RENDER HELPERS
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

  // View: Loading
  if (authLoading || (loading && !patient)) {
    return (
      <div className="profile-loading">
        <div className="loading-spinner"></div>
        <p>Loading Clinical Profile...</p>
      </div>
    );
  }

  // View: Error
  if (error) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠️</div>
        <h3>Unable to Load Patient</h3>
        <p>{error}</p>
        <button className="btn-primary" onClick={fetchPatientData}>Retry</button>
        <button className="btn-secondary" onClick={() => navigate('/patients')}>Back to Dashboard</button>
      </div>
    );
  }

  if (!patient) return null;

  const rhdStatus = getRHDStatusDisplay(patient.rhd_status || 'unknown');

  return (
    <div className="patient-profile-container fade-in">
      {/* HEADER: Patient Identity & Global Actions */}
      <div className="profile-header">
        <div className="patient-info">
          <div className="patient-avatar-large">{patient.name?.charAt(0)}</div>
          <div className="patient-details">
            <h1>{patient.name}</h1>
            <div className="patient-meta">
              <span><strong>ID:</strong> {patient.id}</span>
              <span className="divider">|</span>
              <span>{patient.age} Years</span>
              <span className="divider">|</span>
              <span className="status-indicator" style={{color: rhdStatus.color}}>
                ● {rhdStatus.label}
              </span>
            </div>
          </div>
        </div>
        
        <div className="profile-actions">
          <button className="btn-secondary" onClick={() => navigate('/patients')}>Dash</button>
          <button className="btn-primary" onClick={() => navigate(`/patient/${id}/triage/new`)}>New Triage</button>
          <label className="btn-primary btn-upload">
            Analyze Sound
            <input type="file" accept=".wav" onChange={(e) => handleAnalyzeHeartSound(e.target.files[0])} hidden />
          </label>
        </div>
      </div>

      {/* TABS NAVIGATION */}
      <div className="profile-tabs">
        <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={activeTab === 'encounters' ? 'active' : ''} onClick={() => setActiveTab('encounters')}>Triage History ({triageRecords.length})</button>
        <button className={activeTab === 'recordings' ? 'active' : ''} onClick={() => setActiveTab('recordings')}>PCG Recordings ({recordings.length})</button>
        <button className={activeTab === 'analysis' ? 'active' : ''} onClick={() => setActiveTab('analysis')}>AI Analysis</button>
      </div>

      {/* TAB CONTENT AREA */}
      <div className="tab-content">
        
        {activeTab === 'overview' && (
          <div className="overview-section">
            <div className="stats-grid">
              <div className="stat-card">
                <span className="label">Total Encounters</span>
                <span className="value">{triageRecords.length + recordings.length}</span>
              </div>
              <div className="stat-card">
                <span className="label">Last Prediction</span>
                <span className="value">{recordings[0]?.prediction || 'N/A'}</span>
              </div>
              <div className="stat-card">
                <span className="label">Clinic Location</span>
                <span className="value">{patient.address || 'Gisozi, Kigali'}</span>
              </div>
            </div>
            
            <div className="details-card">
              <h3>Vitals & Demographics</h3>
              <div className="details-grid">
                <p><strong>Gender:</strong> {patient.gender}</p>
                <p><strong>Contact:</strong> {patient.contact || 'Not provided'}</p>
                <p><strong>DOB:</strong> {patient.dob || 'N/A'}</p>
                <p><strong>Primary Doctor:</strong> {patient.doctor_id}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'encounters' && (
          <div className="list-view">
            {triageRecords.length === 0 ? <p className="empty-msg">No triage records found.</p> : (
              <table className="saka-table">
                <thead><tr><th>Date</th><th>Risk Level</th><th>Score</th></tr></thead>
                <tbody>
                  {triageRecords.map((t, i) => (
                    <tr key={i}>
                      <td>{new Date(t.created_at).toLocaleDateString()}</td>
                      <td><span className={`tag-${t.triage_color?.toLowerCase()}`}>{t.triage_color}</span></td>
                      <td>{t.triage_score}/100</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'recordings' && (
          <div className="recordings-list">
            {recordings.length === 0 ? <p className="empty-msg">No heart sounds recorded.</p> : (
              recordings.map((r, i) => (
                <div key={i} className="rec-item">
                  <div className="rec-info">
                    <strong>{new Date(r.created_at).toLocaleDateString()}</strong>
                    <span className={r.prediction === 'RHD' ? 'text-red' : 'text-green'}>
                      {r.prediction} ({(r.confidence * 100).toFixed(1)}%)
                    </span>
                  </div>
                  {r.file_url && <audio controls src={r.file_url} />}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="ai-analysis-container">
            <div className="upload-zone">
               <h3>Saka AI Real-time Triage</h3>
               <p>Upload a PCG sample from the IoT stethoscope to perform valvular analysis.</p>
               <input type="file" accept=".wav" onChange={(e) => handleAnalyzeHeartSound(e.target.files[0])} disabled={analyzing} />
               {analyzing && <div className="pulse-loader">Analyzing Heart Signatures...</div>}
            </div>

            {analysisResult && (
              <div className="analysis-card fade-in">
                <div className={`analysis-header ${analysisResult.prediction.prediction === 'RHD' ? 'bg-red' : 'bg-green'}`}>
                   <h4>Classification: {analysisResult.prediction.prediction}</h4>
                   <h1>{(analysisResult.prediction.confidence * 100).toFixed(1)}% Confidence</h1>
                </div>
                <div className="analysis-body">
                   <p><strong>Clinical Recommendation:</strong> {analysisResult.prediction.prediction === 'RHD' ? 'Immediate referral for specialist echocardiography recommended.' : 'Findings normal. Schedule routine follow-up in 12 months.'}</p>
                   <p className="timestamp">Processed at: {new Date(analysisResult.timestamp).toLocaleString()}</p>
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