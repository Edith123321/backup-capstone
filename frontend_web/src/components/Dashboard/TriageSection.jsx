// frontend_web/src/components/Dashboard/TriageSection.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi, screeningService } from '../../services/api';
import './DashboardLayout.css';

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
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    if (triageRecords && triageRecords.length > 0) {
      setLocalTriage(triageRecords);
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
      }
    } catch (error) {
      console.error('Error fetching triage:', error);
      setError('Failed to load triage records');
    } finally {
      setLoading(false);
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
        
        // Stop all tracks
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
      // Create a File object from the blob
      const audioFile = new File([audioBlob], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
      
      // Upload and analyze
      const prediction = await screeningService.predict(audioFile);
      
      if (prediction.success) {
        setPredictionResult(prediction);
        
        // Save recording to database
        await databaseApi.saveRecording({
          patient_id: selectedPatient,
          doctor_id: user.id,
          file_path: audioFile.name,
          duration: recordingDuration,
          prediction: prediction.prediction,
          confidence: prediction.confidence / 100,
          probabilities: prediction.probabilities,
          analyzed: true,
          recording_data: JSON.stringify(prediction)
        });
        
        // Refresh triage data
        if (onRefresh) onRefresh();
        await fetchTriageData();
        
        // Close recording after successful upload
        setTimeout(() => {
          setShowRecording(null);
          setAudioBlob(null);
          setAudioURL(null);
          setPredictionResult(null);
        }, 3000);
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
          <h3>🚨 Triage Patients</h3>
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
          <h3>🚨 Triage Patients</h3>
        </div>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  return (
    <div className="triage-section">
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
          {localTriage.map((patient) => (
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
                <div className="triage-time">
                  {patient.created_at ? new Date(patient.created_at).toLocaleString() : 'N/A'}
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
                            onClick={() => startRecording(patient.id)}
                          >
                             Start Recording
                          </button>
                        ) : (
                          <button 
                            className="btn-stop-recording"
                            onClick={stopRecording}
                          >
                            ⏹️ Stop Recording
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
                        </div>
                      </div>
                      <div className="recording-actions-upload">
                        <button 
                          className="btn-upload-recording"
                          onClick={uploadRecording}
                          disabled={isUploading}
                        >
                          {isUploading ? 'Uploading...' : ' Upload & Analyze'}
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
                      <div className="prediction-confidence">
                        Confidence: {predictionResult.confidence.toFixed(1)}%
                      </div>
                      <div className="probability-bars">
                        <div className="prob-bar">
                          <span>Normal</span>
                          <div className="bar-track">
                            <div 
                              className="bar-fill normal" 
                              style={{ width: `${predictionResult.probabilities.Normal * 100}%` }}
                            />
                          </div>
                          <span>{(predictionResult.probabilities.Normal * 100).toFixed(1)}%</span>
                        </div>
                        <div className="prob-bar">
                          <span>RHD</span>
                          <div className="bar-track">
                            <div 
                              className="bar-fill rhd" 
                              style={{ width: `${predictionResult.probabilities.RHD * 100}%` }}
                            />
                          </div>
                          <span>{(predictionResult.probabilities.RHD * 100).toFixed(1)}%</span>
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
          ))}
        </div>
      )}
    </div>
  );
};

export default TriageSection;