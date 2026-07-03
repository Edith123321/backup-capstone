// frontend_web/src/components/Patient/PatientDetails.jsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './Patient.css';

const PatientDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);

  // Mock patient data - replace with API call
  useEffect(() => {
    const fetchPatient = async () => {
      // Simulate API call
      setTimeout(() => {
        const mockPatient = {
          id: id || '1',
          name: 'Sarah Kamau',
          age: 12,
          gender: 'Female',
          dateOfBirth: '2014-06-15',
          lastScreening: '2026-06-25',
          result: 'RHD',
          confidence: 97.2,
          screenings: [
            { date: '2026-06-25', result: 'RHD', confidence: 97.2 },
            { date: '2026-05-20', result: 'Normal', confidence: 95.8 },
            { date: '2026-04-15', result: 'Normal', confidence: 96.1 }
          ],
          notes: 'Patient presents with mild fever and chest pain. Family history of RHD.',
          doctor: 'Dr. Jane Smith',
          location: 'Nairobi, Kenya'
        };
        setPatient(mockPatient);
        setLoading(false);
      }, 500);
    };

    fetchPatient();
  }, [id]);

  if (loading) {
    return <div className="loading-container">Loading patient details...</div>;
  }

  if (!patient) {
    return <div className="error-container">Patient not found</div>;
  }

  return (
    <div className="patient-details-container">
      <div className="patient-details-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
        <h1>Patient Profile</h1>
      </div>

      <div className="patient-details-grid">
        {/* Patient Information */}
        <div className="patient-info-card">
          <div className="patient-avatar-large">
            {patient.name.charAt(0)}
          </div>
          <h2>{patient.name}</h2>
          <div className="patient-badges">
            <span className={`badge ${patient.result === 'RHD' ? 'rhd' : 'normal'}`}>
              {patient.result === 'RHD' ? '⚠️ RHD Detected' : '✅ Normal'}
            </span>
            <span className="badge confidence">
              {patient.confidence}% Confidence
            </span>
          </div>
          <div className="patient-details">
            <div className="detail-row">
              <span className="detail-label">Age</span>
              <span className="detail-value">{patient.age} years</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Gender</span>
              <span className="detail-value">{patient.gender}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Date of Birth</span>
              <span className="detail-value">{patient.dateOfBirth}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Last Screening</span>
              <span className="detail-value">{patient.lastScreening}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Location</span>
              <span className="detail-value">{patient.location}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Doctor</span>
              <span className="detail-value">{patient.doctor}</span>
            </div>
          </div>
        </div>

        {/* Screening History */}
        <div className="patient-history-card">
          <h3>📋 Screening History</h3>
          <div className="screening-timeline">
            {patient.screenings.map((screening, index) => (
              <div key={index} className="screening-item">
                <div className={`screening-status ${screening.result === 'RHD' ? 'rhd' : 'normal'}`}>
                  {screening.result === 'RHD' ? '⚠️' : '✅'}
                </div>
                <div className="screening-info">
                  <div className="screening-date">{screening.date}</div>
                  <div className="screening-result">
                    <span className={`badge ${screening.result === 'RHD' ? 'rhd' : 'normal'}`}>
                      {screening.result}
                    </span>
                    <span className="screening-confidence">{screening.confidence}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Clinical Notes */}
        <div className="patient-notes-card">
          <h3>📝 Clinical Notes</h3>
          <p>{patient.notes}</p>
          <div className="notes-actions">
            <button className="btn-primary">Add Note</button>
            <button className="btn-secondary">Schedule Follow-up</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientDetails;