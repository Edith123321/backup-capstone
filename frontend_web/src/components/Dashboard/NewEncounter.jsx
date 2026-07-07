// frontend_web/src/components/Dashboard/NewEncounter.jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import AnatomicalMap, { AnatomicalMapTrigger } from './AnatomicalMap';
import './Encounter.css';

// Material Icons
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import SearchIcon from '@mui/icons-material/Search';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import MicIcon from '@mui/icons-material/Mic';
import StopIcon from '@mui/icons-material/Stop';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import CloseIcon from '@mui/icons-material/Close';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import FavoriteIcon from '@mui/icons-material/Favorite';
import ReportIcon from '@mui/icons-material/Description';
import { CircularProgress } from '@mui/material';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://capstone-be-yxzd.onrender.com';

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
// MAIN COMPONENT
// ============================================
const NewEncounter = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [existingPatients, setExistingPatients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [selectedAuscultationPoint, setSelectedAuscultationPoint] = useState('MV');

  // Section 1: Patient Information
  const [patient, setPatient] = useState({
    name: '',
    age: '',
    gender: '',
    date_of_birth: '',
    contact: '',
    address: '',
    emergency_contact: '',
    medical_history: '',
    isNew: true,
    existingPatientId: null
  });

  // Section 2: Triage
  const [triage, setTriage] = useState({
    respiratory_rate: '',
    heart_rate: '',
    oxygen_saturation: '',
    temperature: '',
    blood_pressure_systolic: '',
    blood_pressure_diastolic: '',
    consciousness_level: 'alert',
    pain_score: '',
    chief_complaint: '',
    symptoms: '',
    notes: ''
  });

  // Section 3: Heart Sound Recording
  const [recording, setRecording] = useState({
    file: null,
    isRecording: false,
    recordingBlob: null,
    prediction: null,
    isProcessing: false,
    audioUrl: null,
    isValidHeartSound: null,
    qualityScore: null,
    validationIssues: [],
    duration: 0,
    severity: null,
    auscultation_point: 'MV',
    auscultation_label: 'Mitral Valve'
  });

  // Section 4: Results
  const [encounterResult, setEncounterResult] = useState(null);
  const [showReportButton, setShowReportButton] = useState(false);

  // Load existing patients
  useEffect(() => {
    if (user?.id) {
      loadExistingPatients();
    }
  }, [user]);

  const loadExistingPatients = async () => {
    try {
      const response = await databaseApi.getPatients(user.id);
      if (response.success) {
        setExistingPatients(response.patients || []);
      }
    } catch (error) {
      console.error('Error loading patients:', error);
    }
  };

  const filteredPatients = existingPatients.filter(p => 
    p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.contact?.includes(searchTerm)
  );

  const selectExistingPatient = (patientId) => {
    const selected = existingPatients.find(p => p.id === patientId);
    if (selected) {
      setPatient({
        ...patient,
        isNew: false,
        existingPatientId: patientId,
        name: selected.name || '',
        age: selected.age || '',
        gender: selected.gender || '',
        date_of_birth: selected.date_of_birth || '',
        contact: selected.contact || '',
        address: selected.address || '',
        emergency_contact: selected.emergency_contact || '',
        medical_history: selected.medical_history || ''
      });
      setSearchTerm(selected.name || '');
      setShowSearchResults(false);
    }
  };

  const handlePatientChange = (e) => {
    const { name, value } = e.target;
    setPatient({ ...patient, [name]: value });
    if (name === 'name' && value) {
      setPatient(prev => ({ ...prev, isNew: true, existingPatientId: null }));
    }
  };

  const handleTriageChange = (e) => {
    const { name, value } = e.target;
    setTriage({ ...triage, [name]: value });
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const audioUrl = URL.createObjectURL(file);
      setRecording({
        ...recording,
        file: file,
        audioUrl: audioUrl,
        prediction: null,
        isValidHeartSound: null,
        qualityScore: null,
        validationIssues: [],
        duration: 0,
        severity: null,
        auscultation_point: selectedAuscultationPoint,
        auscultation_label: AUSCULTATION_POINTS[selectedAuscultationPoint]?.label
      });
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks = [];
      let startTime = Date.now();

      mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
        const duration = (Date.now() - startTime) / 1000;
        
        setRecording({
          ...recording,
          file: audioFile,
          recordingBlob: audioBlob,
          audioUrl: audioUrl,
          isRecording: false,
          prediction: null,
          isValidHeartSound: null,
          qualityScore: null,
          validationIssues: [],
          duration: duration,
          auscultation_point: selectedAuscultationPoint,
          auscultation_label: AUSCULTATION_POINTS[selectedAuscultationPoint]?.label
        });
        
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setRecording({ ...recording, isRecording: true });
      
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
      }, 10000);
    } catch (error) {
      console.error('Error recording:', error);
      setError('Please allow microphone access to record.');
    }
  };

  const stopRecording = () => {};

  // Complete Encounter
  const completeEncounter = async () => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('doctor_id', user.id);
      formData.append('auscultation_point', selectedAuscultationPoint);
      formData.append('auscultation_label', AUSCULTATION_POINTS[selectedAuscultationPoint]?.label || 'Mitral Valve');

      // Patient data
      if (patient.isNew) {
        formData.append('patient', JSON.stringify({
          name: patient.name,
          age: parseInt(patient.age) || 0,
          gender: patient.gender || 'Unknown',
          date_of_birth: patient.date_of_birth || '',
          contact: patient.contact || '',
          address: patient.address || '',
          emergency_contact: patient.emergency_contact || '',
          medical_history: patient.medical_history || ''
        }));
      } else {
        formData.append('patient', JSON.stringify({
          id: patient.existingPatientId
        }));
      }

      // Triage data
      formData.append('triage', JSON.stringify({
        respiratory_rate: parseFloat(triage.respiratory_rate) || 0,
        heart_rate: parseFloat(triage.heart_rate) || 0,
        oxygen_saturation: parseFloat(triage.oxygen_saturation) || 100,
        temperature: parseFloat(triage.temperature) || 37,
        blood_pressure_systolic: parseInt(triage.blood_pressure_systolic) || 0,
        blood_pressure_diastolic: parseInt(triage.blood_pressure_diastolic) || 0,
        consciousness_level: triage.consciousness_level || 'alert',
        pain_score: parseInt(triage.pain_score) || 0,
        chief_complaint: triage.chief_complaint || '',
        symptoms: triage.symptoms || '',
        notes: triage.notes || ''
      }));

      // Audio file
      if (recording.file) {
        formData.append('file', recording.file);
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/encounter`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        // Calculate severity
        const severity = getSeverityGrade(
          result.ml_prediction?.prediction,
          result.ml_prediction?.confidence
        );

        // Update recording with prediction result
        setRecording({
          ...recording,
          prediction: result.ml_prediction,
          severity: severity,
          isProcessing: false
        });

        setEncounterResult({
          success: true,
          patientId: result.patient_id,
          triage: result.triage,
          prediction: result.ml_prediction,
          severity: severity,
          recommendation: result.recommendation,
          followUpNeeded: result.rhd_status?.requires_follow_up || false,
          followUpDays: result.rhd_status?.follow_up_days || null,
          auscultation: result.auscultation,
          message: `✅ Encounter completed! ${result.recommendation?.message || ''}`
        });

        setShowReportButton(true);

        // Navigate to patient after 5 seconds
        setTimeout(() => {
          navigate(`/patient/${result.patient_id}`);
        }, 5000);
      } else {
        throw new Error(result.error || 'Failed to save encounter');
      }
    } catch (error) {
      console.error('Encounter error:', error);
      setError(error.message || 'Failed to complete encounter');
    } finally {
      setLoading(false);
    }
  };

  // Generate Report
  const handleGenerateReport = async () => {
    try {
      const response = await fetch('/api/v1/reports/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          patient_id: encounterResult?.patientId,
          symptoms: triage.symptoms?.split(',') || [],
          clinical_notes: triage.notes || '',
          recommendations: [
            encounterResult?.recommendation?.message || 'Follow-up recommended',
            'Complete echocardiography',
            'Cardiology consultation within 30 days'
          ]
        })
      });
      
      const data = await response.json();
      if (data.success) {
        alert(`Report generated successfully!`);
        window.open(`/api/v1/reports/download/${data.filename}`, '_blank');
      }
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report');
    }
  };

  // ============================================
  // RENDER FUNCTIONS
  // ============================================

  const renderPatientSection = () => (
    <div className="encounter-section">
      <div className="section-header">
        <h2 className='section-badge'>Patient Information</h2>
      </div>
      
      <div className="patient-search">
        <div className="search-input-wrapper">
          <SearchIcon className="search-icon" />
          <input
            type="text"
            placeholder="Search existing patient by name or contact..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setShowSearchResults(true);
            }}
            onFocus={() => setShowSearchResults(true)}
            onBlur={() => setTimeout(() => setShowSearchResults(false), 200)}
          />
        </div>
        {showSearchResults && searchTerm && filteredPatients.length > 0 && (
          <div className="search-results">
            {filteredPatients.slice(0, 5).map(p => (
              <div 
                key={p.id} 
                className="search-result-item"
                onClick={() => selectExistingPatient(p.id)}
              >
                <span className="result-name">{p.name}</span>
                <span className="result-details">Age: {p.age} • Contact: {p.contact}</span>
              </div>
            ))}
          </div>
        )}
        {showSearchResults && searchTerm && filteredPatients.length === 0 && (
          <div className="search-results">
            <div className="search-result-item no-results">
              <span>No patients found. Enter details below to create new patient.</span>
            </div>
          </div>
        )}
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label>Patient Name *</label>
          <input
            type="text"
            name="name"
            placeholder="Enter patient's full name"
            value={patient.name}
            onChange={handlePatientChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Age</label>
          <input
            type="number"
            name="age"
            placeholder="Enter age in years"
            value={patient.age}
            onChange={handlePatientChange}
            min="0"
            max="150"
          />
        </div>
        <div className="form-group">
          <label>Gender</label>
          <select name="gender" value={patient.gender} onChange={handlePatientChange}>
            <option value="">Select gender</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div className="form-group">
          <label>Date of Birth</label>
          <input
            type="date"
            name="date_of_birth"
            value={patient.date_of_birth}
            onChange={handlePatientChange}
          />
        </div>
        <div className="form-group">
          <label>Contact Number</label>
          <input
            type="text"
            name="contact"
            placeholder="Enter phone number"
            value={patient.contact}
            onChange={handlePatientChange}
          />
        </div>
        <div className="form-group">
          <label>Residential Address</label>
          <input
            type="text"
            name="address"
            placeholder="Enter full address"
            value={patient.address}
            onChange={handlePatientChange}
          />
        </div>
        <div className="form-group">
          <label>Emergency Contact</label>
          <input
            type="text"
            name="emergency_contact"
            placeholder="Enter emergency contact number"
            value={patient.emergency_contact}
            onChange={handlePatientChange}
          />
        </div>
        <div className="form-group full-width">
          <label>Medical History</label>
          <textarea
            name="medical_history"
            placeholder="Enter relevant medical history, allergies, or chronic conditions"
            value={patient.medical_history}
            onChange={handlePatientChange}
            rows="3"
          />
        </div>
      </div>
    </div>
  );

  const renderTriageSection = () => (
    <div className="encounter-section">
      <div className="section-header">
        <h2 className='section-badge'>Triage Assessment</h2>
      </div>
      
      <div className="form-grid">
        <div className="form-group">
          <label>Respiratory Rate (breaths/min)</label>
          <input
            type="number"
            name="respiratory_rate"
            placeholder="e.g. 16"
            value={triage.respiratory_rate}
            onChange={handleTriageChange}
            min="0"
            max="60"
          />
        </div>
        <div className="form-group">
          <label>Heart Rate (bpm)</label>
          <input
            type="number"
            name="heart_rate"
            placeholder="e.g. 72"
            value={triage.heart_rate}
            onChange={handleTriageChange}
            min="0"
            max="250"
          />
        </div>
        <div className="form-group">
          <label>Oxygen Saturation (%)</label>
          <input
            type="number"
            name="oxygen_saturation"
            placeholder="e.g. 98"
            value={triage.oxygen_saturation}
            onChange={handleTriageChange}
            min="0"
            max="100"
          />
        </div>
        <div className="form-group">
          <label>Temperature (°C)</label>
          <input
            type="number"
            step="0.1"
            name="temperature"
            placeholder="e.g. 37.0"
            value={triage.temperature}
            onChange={handleTriageChange}
            min="0"
            max="45"
          />
        </div>
        <div className="form-group">
          <label>Systolic BP (mmHg)</label>
          <input
            type="number"
            name="blood_pressure_systolic"
            placeholder="e.g. 120"
            value={triage.blood_pressure_systolic}
            onChange={handleTriageChange}
            min="0"
            max="300"
          />
        </div>
        <div className="form-group">
          <label>Diastolic BP (mmHg)</label>
          <input
            type="number"
            name="blood_pressure_diastolic"
            placeholder="e.g. 80"
            value={triage.blood_pressure_diastolic}
            onChange={handleTriageChange}
            min="0"
            max="200"
          />
        </div>
        <div className="form-group">
          <label>Consciousness Level</label>
          <select name="consciousness_level" value={triage.consciousness_level} onChange={handleTriageChange}>
            <option value="alert">Alert and Oriented</option>
            <option value="confused">Confused</option>
            <option value="unresponsive">Unresponsive</option>
          </select>
        </div>
        <div className="form-group">
          <label>Pain Score (0-10)</label>
          <input
            type="number"
            name="pain_score"
            placeholder="e.g. 3"
            value={triage.pain_score}
            onChange={handleTriageChange}
            min="0"
            max="10"
          />
        </div>
        <div className="form-group full-width">
          <label>Chief Complaint</label>
          <input
            type="text"
            name="chief_complaint"
            placeholder="Primary reason for visit"
            value={triage.chief_complaint}
            onChange={handleTriageChange}
          />
        </div>
        <div className="form-group full-width">
          <label>Symptoms</label>
          <textarea
            name="symptoms"
            placeholder="List all symptoms with duration and severity"
            value={triage.symptoms}
            onChange={handleTriageChange}
            rows="2"
          />
        </div>
        <div className="form-group full-width">
          <label>Clinical Notes</label>
          <textarea
            name="notes"
            placeholder="Additional observations, medical history, or clinical notes"
            value={triage.notes}
            onChange={handleTriageChange}
            rows="2"
          />
        </div>
      </div>
    </div>
  );

  const renderRecordingSection = () => (
    <div className="encounter-section">
      <div className="section-header">
        <h2 className='section-badge'>Heart Sound Recording</h2>
        <div className="section-actions">
          <AnatomicalMapTrigger
            selectedPoint={selectedAuscultationPoint}
            onClick={() => setShowMap(true)}
          />
          <span className="auscultation-display">
            Point: <strong style={{ color: AUSCULTATION_POINTS[selectedAuscultationPoint]?.color }}>
              {AUSCULTATION_POINTS[selectedAuscultationPoint]?.label || 'MV'}
            </strong>
          </span>
        </div>
      </div>
      
      <div className="recording-controls">
        <div className="recording-methods">
          <div className="upload-section">
            <label>Upload Audio File</label>
            <div className="upload-area">
              <input
                type="file"
                id="audio-upload"
                accept=".wav,.mp3,.flac,.m4a"
                onChange={handleFileUpload}
              />
              <label htmlFor="audio-upload" className="upload-label">
                <UploadFileIcon />
                <span>Choose Audio File</span>
                <span className="upload-hint">WAV, MP3, FLAC, or M4A</span>
              </label>
            </div>
          </div>
          
          <div className="divider">or</div>
          
          <div className="record-section">
            <button
              className={`btn-record ${recording.isRecording ? 'recording' : ''}`}
              onClick={recording.isRecording ? stopRecording : startRecording}
            >
              {recording.isRecording ? <StopIcon /> : <MicIcon />}
              {recording.isRecording ? 'Stop Recording' : 'Record Heart Sound'}
            </button>
            <span className="record-hint">Record up to 10 seconds</span>
          </div>
        </div>

        {recording.audioUrl && (
          <div className="audio-preview">
            <div className="audio-player">
              <PlayArrowIcon className="audio-icon" />
              <audio controls src={recording.audioUrl} />
            </div>
            <div className="audio-info">
              <span>Duration: {recording.duration.toFixed(1)}s</span>
              <span className="auscultation-label">
                Point: {recording.auscultation_label || 'MV'}
              </span>
            </div>
            <button 
              className="btn-icon" 
              onClick={() => {
                URL.revokeObjectURL(recording.audioUrl);
                setRecording({
                  ...recording,
                  file: null,
                  audioUrl: null,
                  prediction: null,
                  isValidHeartSound: null,
                  qualityScore: null,
                  validationIssues: [],
                  duration: 0,
                  severity: null
                });
              }}
            >
              <DeleteIcon />
            </button>
          </div>
        )}

        {recording.isProcessing && (
          <div className="processing-indicator">
            <CircularProgress size={32} />
            <p>Analyzing heart sound...</p>
          </div>
        )}

        {recording.isValidHeartSound === false && (
          <div className="validation-error">
            <WarningIcon className="error-icon" />
            <div className="error-content">
              <h4>Invalid Heart Sound Recording</h4>
              <p>Please record again with the stethoscope properly placed on the chest.</p>
              {recording.validationIssues?.length > 0 && (
                <ul className="validation-issues">
                  {recording.validationIssues.map((issue, index) => (
                    <li key={index}>{issue}</li>
                  ))}
                </ul>
              )}
              <button 
                className="btn-secondary"
                onClick={() => {
                  URL.revokeObjectURL(recording.audioUrl);
                  setRecording({
                    ...recording,
                    file: null,
                    audioUrl: null,
                    prediction: null,
                    isValidHeartSound: null,
                    qualityScore: null,
                    validationIssues: [],
                    duration: 0,
                    severity: null
                  });
                }}
              >
                <MicIcon />
                Record Again
              </button>
            </div>
          </div>
        )}

        {recording.prediction && (
          <div className="prediction-result">
            <h3>AI Prediction Result</h3>
            <div className={`prediction-badge ${recording.prediction.prediction === 'Normal' ? 'normal' : 'abnormal'}`}>
              <span className="prediction-label">{recording.prediction.prediction}</span>
              <span className="prediction-confidence">
                {(recording.prediction.confidence * 100).toFixed(1) || '0.0'}% confidence
              </span>
            </div>
            
            {recording.severity && (
              <div 
                className="severity-display"
                style={{
                  backgroundColor: recording.severity.bg,
                  color: recording.severity.color,
                  padding: '8px 16px',
                  borderRadius: '8px',
                  margin: '8px 0',
                  textAlign: 'center',
                  fontWeight: '600'
                }}
              >
                Severity Grade {recording.severity.grade}: {recording.severity.label}
              </div>
            )}

            <div className="prediction-details">
              <div className="prob-bar">
                <span>Normal</span>
                <div className="bar-track">
                  <div 
                    className="bar-fill normal"
                    style={{ width: `${((recording.prediction.probabilities?.Normal || 0) * 100).toFixed(1)}%` }}
                  ></div>
                </div>
                <span>{((recording.prediction.probabilities?.Normal || 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="prob-bar">
                <span>RHD</span>
                <div className="bar-track">
                  <div 
                    className="bar-fill abnormal"
                    style={{ width: `${((recording.prediction.probabilities?.RHD || 0) * 100).toFixed(1)}%` }}
                  ></div>
                </div>
                <span>{((recording.prediction.probabilities?.RHD || 0) * 100).toFixed(1)}%</span>
              </div>
            </div>
            
            <div className="auscultation-result">
              <span>Auscultation Point: <strong>{recording.auscultation_label || 'MV'}</strong></span>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // ============================================
  // MAIN RETURN
  // ============================================

  return (
    <div className="new-encounter-container">
      {/* Anatomical Map */}
      <AnatomicalMap
        selectedPoint={selectedAuscultationPoint}
        onPointSelect={(pointId) => {
          setSelectedAuscultationPoint(pointId);
          setShowMap(false);
          // Update recording with new point
          if (recording.file) {
            setRecording({
              ...recording,
              auscultation_point: pointId,
              auscultation_label: AUSCULTATION_POINTS[pointId]?.label
            });
          }
        }}
        onClose={() => setShowMap(false)}
        isOpen={showMap}
        showLabels={true}
        interactive={true}
        size="medium"
      />

      <div className="encounter-header">
        <h1>New Patient Encounter</h1>
        <p>Complete the entire patient assessment in one page</p>
      </div>

      {error && (
        <div className="error-message">
          <ErrorIcon />
          <span>{error}</span>
          <button onClick={() => setError(null)}><CloseIcon /></button>
        </div>
      )}

      {encounterResult?.success && (
        <div className="success-message">
          <CheckCircleIcon />
          <div>
            <h4>{encounterResult.message}</h4>
            {encounterResult.followUpNeeded && (
              <p>⚠️ Follow-up required in {encounterResult.followUpDays} days</p>
            )}
            {encounterResult.severity && (
              <p>Severity Grade {encounterResult.severity.grade}: {encounterResult.severity.label}</p>
            )}
            {encounterResult.auscultation && (
              <p>Auscultation Point: {encounterResult.auscultation.label}</p>
            )}
            <p>Redirecting to patient profile...</p>
          </div>
        </div>
      )}

      <form onSubmit={(e) => { 
        e.preventDefault(); 
        completeEncounter(); 
      }}>
        {renderPatientSection()}
        {renderTriageSection()}
        {renderRecordingSection()}

        <div className="encounter-actions">
          <div className="actions-left">
            {showReportButton && encounterResult?.success && (
              <button
                type="button"
                className="btn-report"
                onClick={handleGenerateReport}
              >
                <ReportIcon />
                Generate Report
              </button>
            )}
          </div>
          <div className="actions-right">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/dashboard')}
            >
              <CancelIcon />
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading || !patient.name}
            >
              {loading ? (
                <>
                  <CircularProgress size={20} color="inherit" />
                  Processing...
                </>
              ) : (
                <>
                  <SaveIcon />
                  Complete Encounter
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default NewEncounter;