// frontend_web/src/components/Dashboard/TriageSection.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi, screeningService } from '../../services/api';
import AnatomicalMap, { AnatomicalMapTrigger } from './AnatomicalMap';
import './DashboardLayout.css';

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
// AUSCULTATION POINTS
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
const TriageSection = ({ triageRecords = [], onRefresh, onPatientSelect }) => {
  const { user } = useAuth();
  const [localTriage, setLocalTriage] = useState(triageRecords);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRecording, setShowRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [selectedPoint, setSelectedPoint] = useState('MV');
  const [showMap, setShowMap] = useState(false);
  const [followUpReminders, setFollowUpReminders] = useState({});
  const [severityResults, setSeverityResults] = useState({});
  const [prognosticRisks, setPrognosticRisks] = useState({});
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    if (triageRecords && triageRecords.length > 0) {
      setLocalTriage(triageRecords);
      // Fetch additional data for each patient
      triageRecords.forEach(patient => {
        if (patient.patient_id) {
          fetchPatientData(patient.patient_id);
        }
      });
    } else if (user?.id) {
      fetchTriageData();
    }
  }, [triageRecords, user]);

  const fetchTriageData = async () => {
    if (!user?.id) return;
    
    try {
      setLoading(true);
      setError(null);
      const response = await databaseApi.getTriageByDoctor(user.id);
      if (response.success) {
        setLocalTriage(response.triage || []);
        // Fetch additional data for each patient
        (response.triage || []).forEach(patient => {
          if (patient.patient_id) {
            fetchPatientData(patient.patient_id);
          }
        });
      }
    } catch (error) {
      console.error('Error fetching triage:', error);
      setError('Failed to load triage records');
    } finally {
      setLoading(false);
    }
  };

  const fetchPatientData = async (patientId) => {
    try {
      // Fetch severity history
      const historyRes = await databaseApi.getSeverityHistory(patientId);
      if (historyRes.success && historyRes.history.length > 0) {
        setSeverityResults(prev => ({
          ...prev,
          [patientId]: historyRes.history[0]
        }));
      }

      // Fetch prognostic risk
      try {
        const riskRes = await fetch(`/api/v1/prognosis/risk/${patientId}`);
        if (riskRes.ok) {
          const riskData = await riskRes.json();
          if (riskData.success) {
            setPrognosticRisks(prev => ({
              ...prev,
              [patientId]: riskData.prognosis
            }));
          }
        }
      } catch (e) {
        console.warn('Could not fetch prognostic risk:', e);
      }

      // Fetch follow-up reminders
      try {
        const reminderRes = await databaseApi.getFollowUpReminders(patientId);
        if (reminderRes.success) {
          setFollowUpReminders(prev => ({
            ...prev,
            [patientId]: reminderRes.reminders
          }));
        }
      } catch (e) {
        console.warn('Could not fetch follow-up reminders:', e);
      }
    } catch (error) {
      console.error('Error fetching patient data:', error);
    }
  };

  const getColorClass = (color) => {
    const colors = {
      'Red': 'triage-red',
      'Orange': 'triage-orange',
      'Yellow': 'triage-yellow',
      'Green': 'triage-green',
      'Blue': 'triage-blue'
    };
    return colors[color] || 'triage-blue';
  };

  const startRecording = async (patientId) => {
    setSelectedPatient(patientId);
    setPredictionResult(null);
    setAudioBlob(null);
    setAudioURL(null);
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        setAudioURL(URL.createObjectURL(blob));
        setIsRecording(false);
        clearInterval(timerRef.current);
        setRecordingDuration(0);
        
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setRecordingDuration(0);
      
      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

      setShowRecording(patientId);
      
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Unable to access microphone. Please check your permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadRecording = async () => {
    if (!audioBlob || !selectedPatient) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      const audioFile = new File([audioBlob], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
      
      // Include auscultation point
      const prediction = await screeningService.predict(
        audioFile,
        selectedPatient,
        user.id,
        {
          auscultation_point: selectedPoint,
          auscultation_label: AUSCULTATION_POINTS[selectedPoint]?.label
        }
      );
      
      if (prediction.success || prediction.prediction) {
        const result = {
          prediction: prediction.prediction || prediction.class || 'Unknown',
          confidence: prediction.confidence || 0,
          probabilities: {
            Normal: prediction.prob_normal || 0,
            RHD: prediction.prob_rhd || 0
          }
        };
        
        // Calculate severity
        const severity = getSeverityGrade(result.prediction, result.confidence);
        
        setPredictionResult({
          ...result,
          severity: severity,
          auscultation_point: selectedPoint,
          auscultation_label: AUSCULTATION_POINTS[selectedPoint]?.label
        });
        
        // Save recording to database
        await databaseApi.saveRecording({
          patient_id: selectedPatient,
          doctor_id: user.id,
          file_name: audioFile.name,
          duration: recordingDuration,
          prediction: result.prediction,
          confidence: result.confidence,
          severity_grade: severity.grade,
          severity_label: severity.label,
          auscultation_point: selectedPoint,
          auscultation_label: AUSCULTATION_POINTS[selectedPoint]?.label,
          analyzed: true
        });
        
        if (onRefresh) onRefresh();
        await fetchTriageData();
        
        // Fetch updated patient data
        await fetchPatientData(selectedPatient);
        
        setTimeout(() => {
          setShowRecording(null);
          setAudioBlob(null);
          setAudioURL(null);
          setPredictionResult(null);
        }, 5000);
      }
    } catch (error) {
      console.error('Error uploading recording:', error);
      setError('Failed to upload and analyze recording');
    } finally {
      setIsUploading(false);
    }
  };

  const cancelRecording = () => {
    if (isRecording) {
      stopRecording();
    }
    setShowRecording(null);
    setAudioBlob(null);
    setAudioURL(null);
    setPredictionResult(null);
    setSelectedPatient(null);
    setIsRecording(false);
    setRecordingDuration(0);
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="triage-section">
        <div className="triage-header">
          <h3>Triage Patients</h3>
        </div>
        <div className="triage-loading">
          <div className="loading-spinner-small" />
          <p>Loading triage data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="triage-section">
        <div className="triage-header">
          <h3>Triage Patients</h3>
        </div>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  return (
    <div className="triage-section">
      {/* Anatomical Map */}
      <AnatomicalMap
        selectedPoint={selectedPoint}
        onPointSelect={(pointId) => {
          setSelectedPoint(pointId);
          setShowMap(false);
        }}
        onClose={() => setShowMap(false)}
        isOpen={showMap}
        showLabels={true}
        interactive={true}
        size="small"
      />

      <div className="triage-header">
        <h3>Triage Patients</h3>
        <span className="triage-count">{localTriage.length} patients</span>
      </div>

      {localTriage.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🏥</div>
          <p>No triage records yet</p>
          <p className="empty-hint">Start a new triage assessment for a patient</p>
        </div>
      ) : (
        <div className="triage-list">
          {localTriage.map((patient) => {
            const severity = patient.patient_id ? severityResults[patient.patient_id] : null;
            const prognosis = patient.patient_id ? prognosticRisks[patient.patient_id] : null;
            const reminders = (patient.patient_id ? followUpReminders[patient.patient_id] : []) || [];
            
            return (
              <div 
                key={patient.id} 
                className={`triage-item ${getColorClass(patient.triage_color)}`}
              >
                <div className="triage-info">
                  <div className="triage-patient">
                    <span 
                      className="patient-name"
                      onClick={() => onPatientSelect && onPatientSelect(patient)}
                      style={{ cursor: 'pointer' }}
                    >
                      {patient.patient_name || 'Unknown'}
                    </span>
                    <span className={`triage-badge ${getColorClass(patient.triage_color)}`}>
                      {patient.triage_color} - {patient.triage_level}
                    </span>
                  </div>
                  <div className="triage-details">
                    <span>Score: {patient.triage_score}</span>
                    <span>HR: {patient.heart_rate || '--'} bpm</span>
                    <span>SpO2: {patient.oxygen_saturation || '--'}%</span>
                  </div>
                  <div className="triage-meta">
                    <div className="triage-time">
                      {patient.created_at ? new Date(patient.created_at).toLocaleString() : 'N/A'}
                    </div>
                    {severity && (
                      <span 
                        className="severity-badge-small"
                        style={{
                          backgroundColor: severity.severity_label === 'Normal' ? '#dcfce7' : 
                                       severity.severity_label === 'Monitor' ? '#fed7aa' : '#fee2e2',
                          color: severity.severity_label === 'Normal' ? '#22c55e' :
                                 severity.severity_label === 'Monitor' ? '#f59e0b' : '#dc2626'
                        }}
                      >
                        Grade {severity.severity_grade}: {severity.severity_label}
                      </span>
                    )}
                    {prognosis && (
                      <span className={`prognosis-badge ${prognosis.prognosis?.risk_level?.toLowerCase() || 'unknown'}`}>
                        Risk: {prognosis.prognosis?.risk_level || '—'}
                      </span>
                    )}
                    {reminders.length > 0 && (
                      <span className="reminder-badge">
                        ⏰ {reminders.length} reminder{reminders.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
                <div className="triage-actions">
                  <button 
                    className="btn-view"
                    onClick={() => onPatientSelect && onPatientSelect(patient)}
                  >
                    View
                  </button>
                  <button 
                    className="btn-recording"
                    onClick={() => {
                      if (showRecording === patient.id) {
                        setShowRecording(null);
                      } else {
                        setShowRecording(patient.id);
                      }
                    }}
                  >
                    Record
                  </button>
                </div>

                {/* Recording Section */}
                {showRecording === patient.id && (
                  <div className="recording-section">
                    {/* Auscultation Point Selector */}
                    <div className="recording-auscultation">
                      <span className="auscultation-label">Auscultation Point:</span>
                      <AnatomicalMapTrigger
                        selectedPoint={selectedPoint}
                        onClick={() => setShowMap(true)}
                        compact={true}
                      />
                      <span 
                        className="auscultation-value"
                        style={{ color: AUSCULTATION_POINTS[selectedPoint]?.color }}
                      >
                        {AUSCULTATION_POINTS[selectedPoint]?.label || 'MV'}
                      </span>
                    </div>

                    {!predictionResult && !audioBlob && (
                      <div className="recording-controls">
                        <div className="recording-status">
                          {isRecording ? (
                            <span className="recording-active">
                              <span className="recording-dot" />
                              Recording... {formatDuration(recordingDuration)}
                            </span>
                          ) : (
                            <span className="recording-idle">Ready to record</span>
                          )}
                        </div>
                        <div className="recording-buttons">
                          {!isRecording ? (
                            <button 
                              className="btn-start-recording"
                              onClick={() => startRecording(patient.patient_id)}
                            >
                              Start Recording
                            </button>
                          ) : (
                            <button 
                              className="btn-stop-recording"
                              onClick={stopRecording}
                            >
                              Stop Recording
                            </button>
                          )}
                          <button 
                            className="btn-cancel-recording"
                            onClick={cancelRecording}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {audioBlob && !predictionResult && (
                      <div className="recording-preview">
                        <div className="audio-preview">
                          <audio controls src={audioURL} style={{ width: '100%' }} />
                          <div className="audio-info">
                            <span>Duration: {formatDuration(recordingDuration)}</span>
                            <span>Size: {(audioBlob.size / 1024).toFixed(1)} KB</span>
                            <span>Point: {AUSCULTATION_POINTS[selectedPoint]?.label || 'MV'}</span>
                          </div>
                        </div>
                        <div className="recording-actions-upload">
                          <button 
                            className="btn-upload-recording"
                            onClick={uploadRecording}
                            disabled={isUploading}
                          >
                            {isUploading ? 'Uploading...' : 'Upload & Analyze'}
                          </button>
                          <button 
                            className="btn-cancel-recording"
                            onClick={cancelRecording}
                            disabled={isUploading}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {predictionResult && (
                      <div className={`prediction-result ${predictionResult.prediction.toLowerCase()}`}>
                        <div className="prediction-header">
                          <span className="prediction-label">Analysis Complete!</span>
                          <span className={`prediction-value ${predictionResult.prediction.toLowerCase()}`}>
                            {predictionResult.prediction}
                          </span>
                        </div>
                        {predictionResult.severity && (
                          <div 
                            className="severity-display"
                            style={{
                              backgroundColor: predictionResult.severity.bg,
                              color: predictionResult.severity.color,
                              padding: '4px 12px',
                              borderRadius: '12px',
                              margin: '4px 0',
                              textAlign: 'center',
                              fontWeight: '600',
                              fontSize: '0.85rem'
                            }}
                          >
                            Grade {predictionResult.severity.grade}: {predictionResult.severity.label}
                          </div>
                        )}
                        <div className="prediction-confidence">
                          Confidence: {(predictionResult.confidence * 100).toFixed(1)}%
                        </div>
                        <div className="auscultation-result">
                          Point: {predictionResult.auscultation_label || 'MV'}
                        </div>
                        <div className="probability-bars">
                          <div className="prob-bar">
                            <span>Normal</span>
                            <div className="bar-track">
                              <div 
                                className="bar-fill normal" 
                                style={{ width: `${(predictionResult.probabilities?.Normal || 0) * 100}%` }}
                              />
                            </div>
                            <span>{((predictionResult.probabilities?.Normal || 0) * 100).toFixed(1)}%</span>
                          </div>
                          <div className="prob-bar">
                            <span>RHD</span>
                            <div className="bar-track">
                              <div 
                                className="bar-fill rhd" 
                                style={{ width: `${(predictionResult.probabilities?.RHD || 0) * 100}%` }}
                              />
                            </div>
                            <span>{((predictionResult.probabilities?.RHD || 0) * 100).toFixed(1)}%</span>
                          </div>
                        </div>
                        <button 
                          className="btn-close-recording"
                          onClick={cancelRecording}
                        >
                          Close
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default TriageSection;