// frontend_web/src/components/Dashboard/PatientProfile.jsx
import React, { useState } from 'react';
import './PatientProfile.css';

const PatientProfile = ({ 
  patient, 
  triageRecords = [], 
  recordings = [], 
  onBack, 
  onNewTriage, 
  onNewRecording 
}) => {
  const [activeTab, setActiveTab] = useState('overview');

  if (!patient) {
    return (
      <div className="error-container">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <h3>Patient Not Found</h3>
        <p>The patient you're looking for doesn't exist.</p>
        <button className="btn-primary" onClick={onBack}>Back to Patients</button>
      </div>
    );
  }

  const handleNewTriage = () => {
    if (onNewTriage) {
      onNewTriage();
    }
  };

  const handleNewRecording = () => {
    if (onNewRecording) {
      onNewRecording();
    }
  };

  // Calculate stats
  const totalEncounters = triageRecords.length + recordings.length;
  const abnormalResults = triageRecords.filter(t => 
    t.triage_color === 'Red' || t.triage_color === 'Orange'
  ).length;
  const totalRecordings = recordings.length;

  return (
    <div className="patient-profile-container">
      {/* Header */}
      <div className="profile-header">
        <div className="patient-info">
          <div className="patient-avatar-large">
            {patient.name?.charAt(0) || 'P'}
          </div>
          <div className="patient-details">
            <h1>{patient.name || 'Unnamed Patient'}</h1>
            <div className="patient-meta">
              <span>ID: {patient.id}</span>
              <span className="divider">|</span>
              <span>{patient.age || '—'} years</span>
              <span className="divider">|</span>
              <span>{patient.gender || 'Not specified'}</span>
              <span className="divider">|</span>
              <span>{patient.contact || 'No contact'}</span>
            </div>
          </div>
        </div>
        <div className="profile-actions">
          <button className="btn-secondary" onClick={onBack}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            Back
          </button>
          <button className="btn-primary" onClick={handleNewTriage}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Triage
          </button>
          <button className="btn-primary" onClick={handleNewRecording}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            New Recording
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="profile-tabs">
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
          Recordings ({totalRecordings})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div>
          {/* Stats Grid */}
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{totalEncounters}</span>
              <span className="stat-label">Total Encounters</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{totalRecordings}</span>
              <span className="stat-label">RHD Screenings</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{abnormalResults}</span>
              <span className="stat-label">Abnormal Results</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{patient.age || '—'}</span>
              <span className="stat-label">Age</span>
            </div>
          </div>

          {/* Patient Information */}
          <div className="info-card" style={{ marginBottom: 24 }}>
            <h3 style={{ margin: '0 0 20px 0', color: '#1a1a2e', fontSize: '1.1rem' }}>
              Patient Information
            </h3>
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
            </div>
          </div>

          {/* Recent Activity */}
          <div className="recent-activity">
            <h3>Recent Activity</h3>
            {totalEncounters === 0 ? (
              <div className="activity-item">
                <div className="activity-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                </div>
                <div className="activity-content">
                  <span className="activity-title">No recent activity</span>
                  <span className="activity-date">—</span>
                </div>
              </div>
            ) : (
              // Show recent triage records
              triageRecords.slice(0, 5).map((triage, index) => (
                <div key={index} className="activity-item">
                  <div className="activity-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                      <path d="M2 17l10 5 10-5"/>
                      <path d="M2 12l10 5 10-5"/>
                    </svg>
                  </div>
                  <div className="activity-content">
                    <span className="activity-title">Triage Assessment</span>
                    <span className="activity-date">
                      {triage.created_at ? new Date(triage.created_at).toLocaleDateString() : 'Recent'}
                      {triage.triage_color && (
                        <span className={`triage-badge badge-${triage.triage_color.toLowerCase()}`} style={{ marginLeft: 12 }}>
                          {triage.triage_color}
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === 'encounters' && (
        <div className="triage-table">
          <div className="tab-header">
            <h2>Encounters</h2>
            <div className="tab-actions">
              <button className="btn-primary" onClick={handleNewTriage}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                New Triage
              </button>
            </div>
          </div>
          {triageRecords.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
              <p style={{ marginTop: 16 }}>No encounters recorded yet</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {triageRecords.map((triage, index) => (
                  <tr key={index}>
                    <td>{triage.created_at ? new Date(triage.created_at).toLocaleDateString() : '—'}</td>
                    <td>Triage Assessment</td>
                    <td>
                      <span className={`triage-badge badge-${triage.triage_color?.toLowerCase() || 'gray'}`}>
                        {triage.triage_color || 'Pending'}
                      </span>
                    </td>
                    <td>{triage.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'recordings' && (
        <div>
          <div className="tab-header">
            <h2>Heart Sound Recordings</h2>
            <div className="tab-actions">
              <button className="btn-primary" onClick={handleNewRecording}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                New Recording
              </button>
            </div>
          </div>
          {recordings.length === 0 ? (
            <div className="recordings-grid">
              <div className="recording-card" style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                <p style={{ marginTop: 16 }}>No recordings available</p>
              </div>
            </div>
          ) : (
            <div className="recordings-grid">
              {recordings.map((recording, index) => (
                <div key={index} className="recording-card">
                  <div className="recording-header">
                    <h4>Recording #{index + 1}</h4>
                    <span className={`triage-badge badge-${recording.status?.toLowerCase() || 'gray'}`}>
                      {recording.status || 'Pending'}
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
                      <span className="detail-label">Duration</span>
                      <span className="detail-value">{recording.duration || '—'}</span>
                    </div>
                  </div>
                  {recording.file_url && (
                    <audio controls>
                      <source src={recording.file_url} type="audio/wav" />
                      Your browser does not support the audio element.
                    </audio>
                  )}
                  <div className="recording-actions">
                    <button className="btn-secondary">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                      </svg>
                      Play
                    </button>
                    <button className="btn-secondary">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                      Download
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PatientProfile;