// frontend_web/src/components/Dashboard/NewEncounter.jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi, screeningService } from '../../services/api';
import { useNavigate } from 'react-router-dom';
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
import { CircularProgress } from '@mui/material';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://capstone-be-yxzd.onrender.com';

const NewEncounter = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [existingPatients, setExistingPatients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);

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
    duration: 0
  });

  // Section 4: Results
  const [encounterResult, setEncounterResult] = useState(null);

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
    // If user types, mark as new patient
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
        duration: 0
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
          duration: duration
        });
        
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setRecording({ ...recording, isRecording: true });
      
      // Auto-stop after 10 seconds
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

  const stopRecording = () => {
    // Stop will be handled by the mediaRecorder onstop event
  };

  const analyzeHeartSound = async () => {
    if (!recording.file) {
      setError('Please upload or record a heart sound first.');
      return;
    }

    setRecording({ ...recording, isProcessing: true });
    setError(null);

    try {
      // Step 1: Validate heart sound quality
      const formData = new FormData();
      formData.append('file', recording.file);
      
      let validationResult = { is_valid: true, quality_score: 0.8, issues: [] };
      try {
        const validationResponse = await fetch(`${API_BASE_URL}/api/v1/screening/validate`, {
          method: 'POST',
          body: formData
        });
        validationResult = await validationResponse.json();
      } catch (e) {
        console.warn('Validation endpoint not available, proceeding with default validation');
      }
      
      if (validationResult && validationResult.is_valid === false) {
        setRecording({
          ...recording,
          isProcessing: false,
          isValidHeartSound: false,
          qualityScore: validationResult.quality_score || 0.3,
          validationIssues: validationResult.issues || ['Recording quality is poor'],
          prediction: null
        });
        return;
      }

      // Step 2: Run AI prediction
      const predictFormData = new FormData();
      predictFormData.append('file', recording.file);
      
      const predictResponse = await fetch(`${API_BASE_URL}/api/v1/screening/predict`, {
        method: 'POST',
        body: predictFormData
      });
      
      const result = await predictResponse.json();
      
      if (result.success) {
        setRecording({
          ...recording,
          isProcessing: false,
          isValidHeartSound: true,
          qualityScore: validationResult?.quality_score || 0.8,
          validationIssues: [],
          prediction: result
        });
      } else {
        throw new Error(result.error || 'Prediction failed');
      }
    } catch (error) {
      console.error('Analysis error:', error);
      setError(error.message || 'Failed to analyze heart sound. Please try again.');
      setRecording({ ...recording, isProcessing: false });
    }
  };

  const saveEncounter = async () => {
    setLoading(true);
    setError(null);

    try {
      // Step 1: Create or get patient
      let patientId;
      if (patient.isNew) {
        const patientData = {
          name: patient.name,
          age: parseInt(patient.age) || 0,
          gender: patient.gender || 'Unknown',
          date_of_birth: patient.date_of_birth || '',
          contact: patient.contact || '',
          address: patient.address || '',
          emergency_contact: patient.emergency_contact || '',
          medical_history: patient.medical_history || '',
          doctor_id: user.id
        };
        
        const patientResponse = await databaseApi.createPatient(patientData);
        if (!patientResponse.success) {
          throw new Error(patientResponse.error || 'Failed to create patient');
        }
        patientId = patientResponse.patient_id;
      } else {
        patientId = patient.existingPatientId;
      }

      // Step 2: Create triage record
      const triageData = {
        patient_id: patientId,
        doctor_id: user.id,
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
      };
      
      const triageResponse = await databaseApi.createTriage(triageData);
      if (!triageResponse.success) {
        throw new Error(triageResponse.error || 'Failed to create triage record');
      }

      // Step 3: Save heart sound recording and prediction
      if (recording.file && recording.prediction) {
        const formData = new FormData();
        formData.append('file', recording.file);
        formData.append('patient_id', patientId);
        formData.append('doctor_id', user.id);
        formData.append('prediction', recording.prediction.prediction || 'Unknown');
        formData.append('confidence', String(recording.prediction.confidence || 0));
        formData.append('probabilities', JSON.stringify(recording.prediction.probabilities || {}));
        formData.append('quality_score', String(recording.qualityScore || 0));
        formData.append('duration', String(recording.duration || 0));
        
        try {
          await databaseApi.saveRecording(formData);
        } catch (recordingError) {
          console.error('Error saving recording:', recordingError);
          // Don't fail the whole encounter if recording fails
        }
      }

      // Step 4: Show success
      setEncounterResult({
        success: true,
        patientId: patientId,
        message: '✅ Patient encounter completed successfully!'
      });

      setLoading(false);

      // Navigate to patient profile after 2 seconds
      setTimeout(() => {
        navigate(`/patient/${patientId}`);
      }, 2000);

    } catch (error) {
      console.error('Save encounter error:', error);
      setError(error.message || 'Failed to save encounter. Please try again.');
      setLoading(false);
    }
  };

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
                  duration: 0
                });
              }}
            >
              <DeleteIcon />
            </button>
          </div>
        )}

        {recording.file && !recording.prediction && !recording.isProcessing && recording.isValidHeartSound !== false && (
          <button
            className="btn-primary analyze-btn"
            onClick={analyzeHeartSound}
          >
            <PlayArrowIcon />
            Analyze Heart Sound
          </button>
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
                    duration: 0
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
              <span className="prediction-confidence">{recording.prediction.confidence?.toFixed(1) || '0.0'}% confidence</span>
            </div>
            <div className="prediction-details">
              <div className="prob-bar">
                <span>Normal</span>
                <div className="bar-track">
                  <div 
                    className="bar-fill normal"
                    style={{ width: `${(recording.prediction.probabilities?.Normal || 0) * 100}%` }}
                  ></div>
                </div>
                <span>{((recording.prediction.probabilities?.Normal || 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="prob-bar">
                <span>Abnormal</span>
                <div className="bar-track">
                  <div 
                    className="bar-fill abnormal"
                    style={{ width: `${(recording.prediction.probabilities?.RHD || 0) * 100}%` }}
                  ></div>
                </div>
                <span>{((recording.prediction.probabilities?.RHD || 0) * 100).toFixed(1)}%</span>
              </div>
            </div>
            {recording.qualityScore && (
              <div className="quality-score">
                <span>Signal Quality: {(recording.qualityScore * 100).toFixed(0)}%</span>
                <div className="quality-bar">
                  <div 
                    className={`quality-fill ${recording.qualityScore > 0.7 ? 'good' : recording.qualityScore > 0.4 ? 'fair' : 'poor'}`}
                    style={{ width: `${recording.qualityScore * 100}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="new-encounter-container">
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
            <p>Redirecting to patient profile...</p>
          </div>
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); saveEncounter(); }}>
        {renderPatientSection()}
        {renderTriageSection()}
        {renderRecordingSection()}

        <div className="encounter-actions">
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
            disabled={loading || !patient.name || !recording.prediction}
          >
            {loading ? (
              <>
                <CircularProgress size={20} color="inherit" />
                Saving...
              </>
            ) : (
              <>
                <SaveIcon />
                Complete Profile
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default NewEncounter;