// frontend_web/src/components/Dashboard/NewEncounter.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNotify } from '../../context/NotificationContext';
import { databaseApi } from '../../services/api';
import { resilientFetch, friendlyError } from '../../services/resilientFetch';
import { useNavigate } from 'react-router-dom';
import AnatomicalMap, { AnatomicalMapTrigger } from './AnatomicalMap';
import './Encounter.css';

// Material Icons
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import SearchIcon from '@mui/icons-material/Search';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import MicIcon from '@mui/icons-material/Mic';
import DevicesIcon from '@mui/icons-material/Devices';
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
  const notify = useNotify();
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

  // Derive age (in whole years) from a date of birth.
  const computeAge = (dob) => {
    if (!dob) return '';
    const birth = new Date(dob);
    if (isNaN(birth.getTime())) return '';
    const now = new Date();
    let age = now.getFullYear() - birth.getFullYear();
    const m = now.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age -= 1;
    return age >= 0 ? age : '';
  };

  const handlePatientChange = (e) => {
    const { name, value } = e.target;
    setPatient(prev => {
      const next = { ...prev, [name]: value };
      // Age is derived from date of birth, not entered directly.
      if (name === 'date_of_birth') next.age = computeAge(value);
      if (name === 'name' && value) {
        next.isNew = true;
        next.existingPatientId = null;
      }
      return next;
    });
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

  // ---- Record from the connected IoT stethoscope over Bluetooth ----
  // UUIDs must match iot/src/Config.h (BLE_SERVICE_UUID / BLE_CHAR_UUID).
  const BLE_SERVICE_UUID = '4fafc201-1fb5-459e-8fcc-c5c9c331914b';
  const BLE_CHAR_UUID = 'beb5483e-36e1-4688-b7f5-ea07361b26a8';
  const DEVICE_SAMPLE_RATE = 4000;
  const bleSamples = useRef([]);

  // Encode Float32 samples [-1,1] to a 16-bit PCM mono WAV Blob.
  const encodeWav = (samples, sampleRate) => {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);          // PCM
    view.setUint16(22, 1, true);          // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, 'data');
    view.setUint32(40, samples.length * 2, true);
    let off = 44;
    for (let i = 0; i < samples.length; i++, off += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Blob([view], { type: 'audio/wav' });
  };

  // Turn collected samples into a WAV file on the recording state (shared by the
  // Bluetooth and WiFi capture paths).
  const finalizeDeviceSamples = (samples) => {
    if (!samples.length) {
      setError('No audio received from the device. Ensure it is powered on and streaming.');
      setRecording(prev => ({ ...prev, isRecording: false }));
      return;
    }
    const blob = encodeWav(samples, DEVICE_SAMPLE_RATE);
    const file = new File([blob], 'device_recording.wav', { type: 'audio/wav' });
    setRecording(prev => ({
      ...prev,
      file,
      recordingBlob: blob,
      audioUrl: URL.createObjectURL(blob),
      isRecording: false,
      prediction: null,
      isValidHeartSound: null,
      qualityScore: null,
      validationIssues: [],
      duration: samples.length / DEVICE_SAMPLE_RATE,
      auscultation_point: selectedAuscultationPoint,
      auscultation_label: AUSCULTATION_POINTS[selectedAuscultationPoint]?.label,
    }));
  };

  // ---- Record from the connected IoT stethoscope over WiFi (WebSocket) ----
  // Same firmware protocol as Bluetooth, over ws://<device-ip>/audio. Note:
  // ws:// is blocked from an HTTPS page (mixed content), so this path works when
  // the dashboard runs locally over http; on the deployed HTTPS site use
  // Bluetooth instead.
  const recordFromDeviceWifi = async () => {
    const remembered = localStorage.getItem('saka_device_ip') || '';
    const ip = window.prompt(
      'Enter the stethoscope IP address (shown on the device serial monitor on boot):',
      remembered
    );
    if (!ip) return;
    const host = ip.trim();
    localStorage.setItem('saka_device_ip', host);

    const samples = [];
    let ws;
    try {
      setRecording(prev => ({ ...prev, isRecording: true }));
      ws = new WebSocket(`ws://${host}/audio`);
      ws.binaryType = 'arraybuffer';
      ws.onmessage = (e) => {
        if (e.data instanceof ArrayBuffer) {
          const dv = new DataView(e.data);
          for (let i = 0; i + 1 < dv.byteLength; i += 2) {
            samples.push(dv.getInt16(i, true) / 32768);
          }
        }
      };
      // Wait for the socket to open (or fail).
      await new Promise((resolve, reject) => {
        ws.onopen = resolve;
        ws.onerror = () => reject(new Error(`Could not connect to ${host}`));
        setTimeout(() => reject(new Error('Connection timed out')), 8000);
      });

      ws.send(JSON.stringify({ command: 'START_RECORDING' }));
      await new Promise((res) => setTimeout(res, 10000)); // capture ~10s
      try { ws.send(JSON.stringify({ command: 'STOP_RECORDING' })); } catch { /* ignore */ }
      ws.close();

      finalizeDeviceSamples(samples);
    } catch (error) {
      console.error('WiFi device recording failed:', error);
      setError('WiFi device recording failed: ' + (error?.message || error));
      setRecording(prev => ({ ...prev, isRecording: false }));
      try { if (ws) ws.close(); } catch { /* ignore */ }
    }
  };

  const recordFromDevice = async () => {
    if (!navigator.bluetooth) {
      setError('Web Bluetooth is not supported here. Use Chrome or Edge over HTTPS, or upload a file.');
      return;
    }
    let device, characteristic;
    const onValue = (e) => {
      const dv = e.target.value;
      for (let i = 0; i + 1 < dv.byteLength; i += 2) {
        bleSamples.current.push(dv.getInt16(i, true) / 32768);
      }
    };
    try {
      setRecording(prev => ({ ...prev, isRecording: true }));
      bleSamples.current = [];
      device = await navigator.bluetooth.requestDevice({
        filters: [{ services: [BLE_SERVICE_UUID] }],
        optionalServices: [BLE_SERVICE_UUID],
      });
      const server = await device.gatt.connect();
      const service = await server.getPrimaryService(BLE_SERVICE_UUID);
      characteristic = await service.getCharacteristic(BLE_CHAR_UUID);
      await characteristic.startNotifications();
      characteristic.addEventListener('characteristicvaluechanged', onValue);
      try { await characteristic.writeValue(new TextEncoder().encode('START')); } catch { /* optional */ }

      // Capture ~10 seconds of streamed audio.
      await new Promise(res => setTimeout(res, 10000));

      try { await characteristic.writeValue(new TextEncoder().encode('STOP')); } catch { /* optional */ }
      characteristic.removeEventListener('characteristicvaluechanged', onValue);
      await characteristic.stopNotifications();
      if (device.gatt?.connected) device.gatt.disconnect();

      finalizeDeviceSamples(bleSamples.current);
    } catch (error) {
      if (error?.name !== 'NotFoundError') {
        console.error('Device recording failed:', error);
        setError('Device recording failed: ' + (error?.message || error));
      }
      setRecording(prev => ({ ...prev, isRecording: false }));
      try { if (device?.gatt?.connected) device.gatt.disconnect(); } catch { /* ignore */ }
    }
  };

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

      // Cold-start-aware submit: retries a spun-down backend and tells the nurse
      // what's happening instead of failing with a cryptic "CORS" error.
      const savingId = notify.loading('Saving encounter…');
      let coldStartId = null;
      const response = await resilientFetch(
        `${API_BASE_URL}/api/v1/encounter`,
        { method: 'POST', body: formData },
        {
          onRetry: () => {
            if (!coldStartId) {
              coldStartId = notify.info('Server is waking up — retrying…', {
                title: 'Please wait', duration: 0,
              });
            }
          },
        }
      );
      if (coldStartId) notify.dismiss(coldStartId);
      notify.dismiss(savingId);

      let result = null;
      try { result = await response.json(); } catch { /* handled below */ }

      if (!response.ok || !result?.success) {
        throw new Error(result?.error || `Failed to save encounter (HTTP ${response.status})`);
      }

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
        // Human-centered additions:
        signalQuality: result.signal_quality || null,      // scenarios 1,2,3,5,6
        clinicalOverride: result.clinical_override || null, // scenario 7
        followUpNeeded: result.rhd_status?.requires_follow_up || false,
        followUpDays: result.rhd_status?.follow_up_days || null,
        auscultation: result.auscultation,
        message: `✅ Encounter completed! ${result.recommendation?.message || ''}`
      });

      setShowReportButton(true);

      // --- Human-centered notifications (the SQA/override design) ---
      notify.success('Encounter saved successfully.', {
        detail: result.recommendation?.message,
      });

      const sq = result.signal_quality;
      if (sq?.blocked) {
        notify.warning(sq.message || 'The heart sound was not gradeable — AI analysis was skipped.', {
          title: sq.title || 'Signal not gradeable', duration: 0,
        });
      } else if (sq?.warnings?.length) {
        sq.warnings.forEach((w) =>
          notify.warning(w.message, { title: w.title || 'Signal note' })
        );
      }

      // Scenario 7 — clinical red-flag override must be impossible to miss.
      if (result.clinical_override?.active) {
        notify.error(result.clinical_override.message, {
          title: result.clinical_override.title || 'Clinical override',
          duration: 0,
          action: { label: 'Open patient', onClick: () => navigate(`/patient/${result.patient_id}`) },
        });
      } else {
        // Auto-navigate only when there's no override the nurse must read first.
        setTimeout(() => navigate(`/patient/${result.patient_id}`), 5000);
      }
    } catch (error) {
      console.error('Encounter error:', error);
      const msg = friendlyError(error);
      setError(msg);
      notify.error(msg, {
        title: 'Could not save encounter',
        action: { label: 'Retry', onClick: () => completeEncounter() },
      });
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
          <label>Date of Birth</label>
          <input
            type="date"
            name="date_of_birth"
            value={patient.date_of_birth}
            max={new Date().toISOString().split('T')[0]}
            onChange={handlePatientChange}
          />
        </div>
        <div className="form-group">
          <label>Age (auto-calculated)</label>
          <input
            type="text"
            name="age"
            value={patient.age !== '' && patient.age !== null && patient.age !== undefined ? `${patient.age} years` : ''}
            placeholder="Set from date of birth"
            readOnly
            disabled
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
              disabled={recording.isRecording}
            >
              {recording.isRecording ? <StopIcon /> : <MicIcon />}
              {recording.isRecording ? 'Recording…' : 'Record Heart Sound'}
            </button>
            <span className="record-hint">Record up to 10 seconds</span>
          </div>

          <div className="divider">or</div>

          <div className="record-section">
            <button
              type="button"
              className="btn-record btn-record-device"
              onClick={recordFromDevice}
              disabled={recording.isRecording}
            >
              <DevicesIcon />
              Record via Bluetooth
            </button>
            <button
              type="button"
              className="btn-record btn-record-device"
              onClick={recordFromDeviceWifi}
              disabled={recording.isRecording}
            >
              <DevicesIcon />
              Record via WiFi
            </button>
            <span className="record-hint">
              Streams 10s from the Saka stethoscope. Bluetooth works on the live site;
              WiFi (ws://device-ip) requires running the dashboard locally over http.
            </span>
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

      {/* Scenario 7 — Clinical red-flag override. Rendered ABOVE the success
          message so a high-risk-but-AI-normal conflict can never be missed. */}
      {encounterResult?.clinicalOverride?.active && (
        <div className="clinical-override">
          <div className="clinical-override-title">
            {encounterResult.clinicalOverride.title}
          </div>
          <div className="clinical-override-message">
            {encounterResult.clinicalOverride.message}
          </div>
          {encounterResult.clinicalOverride.action && (
            <div className="clinical-override-message" style={{ marginTop: 6, fontWeight: 600 }}>
              → {encounterResult.clinicalOverride.action}
            </div>
          )}
        </div>
      )}

      {/* Signal Quality feedback for the encounter audio (scenarios 1,2,3,5,6) */}
      {encounterResult?.signalQuality?.blocked && (
        <div className="sqa-block">
          <div className="sqa-block-header">
            <span className="sqa-block-icon">🚫</span>
            <span className="sqa-block-title">{encounterResult.signalQuality.title}</span>
          </div>
          <p className="sqa-block-message">{encounterResult.signalQuality.message}</p>
          <p className="sqa-block-hint">
            The triage was saved, but the AI heart analysis was skipped — please re-record the heart sound.
          </p>
        </div>
      )}
      {!encounterResult?.signalQuality?.blocked &&
        encounterResult?.signalQuality?.warnings?.length > 0 && (
        <div className="sqa-warnings">
          {encounterResult.signalQuality.warnings.map((w, i) => (
            <div key={i} className="sqa-warning">
              <span className="sqa-warning-icon">⚠️</span>
              <div>
                <div className="sqa-warning-title">{w.title}</div>
                <div className="sqa-warning-message">{w.message}</div>
              </div>
            </div>
          ))}
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