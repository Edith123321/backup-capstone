// frontend_web/src/components/Dashboard/IoTDevices.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi } from '../../services/api';
import './IoTDevices.css';

const IoTDevices = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState('idle');
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [registerForm, setRegisterForm] = useState({
    device_name: '',
    device_type: 'stethoscope',
    ip_address: '',
    mac_address: ''
  });
  
  const wsConnection = useRef(null);
  const audioContext = useRef(null);
  const audioChunks = useRef([]);
  const mediaRecorder = useRef(null);

  // Fetch devices
  const fetchDevices = useCallback(async () => {
    if (!user?.id) return;
    
    try {
      setLoading(true);
      setError(null);
      const response = await databaseApi.getDevices(user.id);
      
      if (response.success) {
        setDevices(response.devices || []);
      } else {
        setError(response.error || 'Failed to fetch devices');
      }
    } catch (err) {
      console.error('Error fetching devices:', err);
      setError(err.message || 'Failed to connect to server');
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchDevices();
    
    // Cleanup on unmount
    return () => {
      if (wsConnection.current) {
        wsConnection.current.close();
      }
      if (audioContext.current) {
        audioContext.current.close();
      }
    };
  }, [fetchDevices]);

  // Connect to IoT device via WebSocket
  const connectToDevice = async (device) => {
    if (!device.ip_address) {
      alert('Device IP address not configured');
      return;
    }

    try {
      setRecordingStatus('connecting');
      setSelectedDevice(device);

      // Close existing connection if any
      if (wsConnection.current) {
        wsConnection.current.close();
      }

      // Create WebSocket connection
      const ws = new WebSocket(`ws://${device.ip_address}/audio`);
      
      ws.onopen = () => {
        console.log('Connected to IoT device:', device.device_name);
        setRecordingStatus('connected');
        // Update device status in UI
        updateDeviceStatus(device.id, 'online');
      };
      
      ws.onmessage = (event) => {
        handleAudioData(event.data);
      };
      
      ws.onclose = () => {
        console.log('Disconnected from IoT device');
        setRecordingStatus('disconnected');
        updateDeviceStatus(device.id, 'offline');
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setRecordingStatus('error');
        alert('Failed to connect to device. Please check the IP address and try again.');
      };
      
      wsConnection.current = ws;
      
    } catch (error) {
      console.error('Failed to connect to device:', error);
      setRecordingStatus('error');
      alert('Failed to connect to device. Please check the IP address and try again.');
    }
  };

  // Disconnect from device
  const disconnectDevice = () => {
    if (wsConnection.current) {
      wsConnection.current.close();
      wsConnection.current = null;
    }
    if (isRecording) {
      stopRecording();
    }
    setSelectedDevice(null);
    setRecordingStatus('idle');
  };

  // Handle incoming audio data
  const handleAudioData = (data) => {
    try {
      // Parse the incoming data
      const audioData = typeof data === 'string' ? JSON.parse(data) : data;
      
      if (audioData.type === 'audio_chunk') {
        // Handle audio chunk
        const base64Data = audioData.data;
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        audioChunks.current.push(bytes.buffer);
      } else if (audioData.type === 'recording_complete') {
        // Handle completed recording
        console.log('Recording complete received from device');
        processRecording();
      }
    } catch (err) {
      console.error('Error processing audio data:', err);
    }
  };

  // Start recording
  const startRecording = () => {
    if (!wsConnection.current || wsConnection.current.readyState !== WebSocket.OPEN) {
      alert('Please connect to a device first');
      return;
    }

    try {
      // Reset audio chunks
      audioChunks.current = [];
      
      // Send start recording command to device
      wsConnection.current.send(JSON.stringify({ 
        action: 'start_recording',
        timestamp: new Date().toISOString()
      }));
      
      setIsRecording(true);
      setRecordingStatus('recording');
      console.log('Recording started...');
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('Failed to start recording. Please try again.');
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (!wsConnection.current || wsConnection.current.readyState !== WebSocket.OPEN) {
      setIsRecording(false);
      setRecordingStatus('idle');
      return;
    }

    try {
      // Send stop recording command to device
      wsConnection.current.send(JSON.stringify({ 
        action: 'stop_recording',
        timestamp: new Date().toISOString()
      }));
      
      setIsRecording(false);
      setRecordingStatus('processing');
      
      // Process recording after a short delay
      setTimeout(() => {
        processRecording();
      }, 2000);
      
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setIsRecording(false);
      setRecordingStatus('idle');
    }
  };

  // Process the recorded audio
  const processRecording = async () => {
    try {
      if (audioChunks.current.length === 0) {
        console.warn('No audio data received');
        setRecordingStatus('idle');
        return;
      }

      // Combine audio chunks
      const combinedBuffer = new Blob(audioChunks.current, { type: 'audio/wav' });
      const file = new File([combinedBuffer], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
      
      // Send to backend for analysis
      await analyzeRecording(file);
      
      // Reset
      audioChunks.current = [];
      setRecordingStatus('idle');
      
    } catch (error) {
      console.error('Error processing recording:', error);
      setRecordingStatus('error');
    }
  };

  // Analyze recording using screening service
  const analyzeRecording = async (file) => {
    try {
      // Import screening service dynamically to avoid circular dependency
      const { screeningService } = await import('../../services/api');
      
      // Get patient ID from selected device or prompt
      const patientId = prompt('Enter patient ID for this recording:');
      if (!patientId) {
        alert('Patient ID is required to save the recording');
        return;
      }

      // Get prediction
      const result = await screeningService.predict(file);
      
      if (result.success || result.prediction) {
        // Save recording to database
        const recordingData = {
          patient_id: patientId,
          doctor_id: user?.id,
          file_name: `IoT_recording_${Date.now()}.wav`,
          prediction: result.prediction || result.class || 'Unknown',
          confidence: result.confidence || 0,
          recording_date: new Date().toISOString(),
          notes: `Recorded via IoT stethoscope on ${new Date().toLocaleString()}`
        };

        await databaseApi.saveRecording(recordingData);
        
        alert(`Analysis complete: ${recordingData.prediction} (${(recordingData.confidence * 100).toFixed(1)}% confidence)`);
      }
      
    } catch (error) {
      console.error('Error analyzing recording:', error);
      alert('Failed to analyze recording: ' + error.message);
    }
  };

  // Update device status in UI
  const updateDeviceStatus = async (deviceId, status) => {
    try {
      await databaseApi.updateDeviceStatus(deviceId, status);
      
      setDevices(prev => 
        prev.map(d => 
          d.id === deviceId ? { ...d, status: status } : d
        )
      );
    } catch (error) {
      console.error('Error updating device status:', error);
    }
  };

  // Register new device
  const handleRegisterDevice = async (e) => {
    e.preventDefault();
    
    if (!registerForm.device_name || !registerForm.ip_address) {
      alert('Device name and IP address are required');
      return;
    }

    try {
      const deviceData = {
        doctor_id: user.id,
        ...registerForm
      };

      const response = await databaseApi.registerDevice(deviceData);
      
      if (response.success) {
        alert('Device registered successfully!');
        setShowRegisterModal(false);
        setRegisterForm({
          device_name: '',
          device_type: 'stethoscope',
          ip_address: '',
          mac_address: ''
        });
        fetchDevices();
      } else {
        alert(response.error || 'Failed to register device');
      }
    } catch (error) {
      console.error('Error registering device:', error);
      alert('Failed to register device: ' + error.message);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="devices-loading">
        <div className="loading-spinner"></div>
        <p>Loading devices...</p>
      </div>
    );
  }

  return (
    <div className="iot-devices-container">
      {/* Header */}
      <div className="devices-header">
        <div className="header-left">
          <h1>IoT Stethoscope Devices</h1>
          <p className="subtitle">Connect and manage your IoT stethoscope devices</p>
        </div>
        <button className="btn-primary" onClick={() => setShowRegisterModal(true)}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Register Device
        </button>
      </div>

      {/* Status Cards */}
      <div className="status-cards">
        <div className="status-card">
          <div className="status-icon status-icon-connection">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L15 9"/>
              <path d="M22 2L17 13L13 9L22 2Z"/>
              <path d="M13 9L9 13"/>
              <path d="M6 17L2 21"/>
              <path d="M12 12L17 17"/>
            </svg>
          </div>
          <div className="status-info">
            <span className="status-label">Connection</span>
            <span className={`status-value ${recordingStatus}`}>
              {recordingStatus === 'connected' ? 'Connected' :
               recordingStatus === 'connecting' ? 'Connecting...' :
               recordingStatus === 'recording' ? 'Recording' :
               recordingStatus === 'processing' ? 'Processing...' :
               recordingStatus === 'disconnected' ? 'Disconnected' :
               recordingStatus === 'error' ? 'Error' : 'Idle'}
            </span>
          </div>
        </div>

        <div className="status-card">
          <div className="status-icon status-icon-recording">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
          <div className="status-info">
            <span className="status-label">Recording Status</span>
            <span className={`status-value ${isRecording ? 'recording-active' : ''}`}>
              {isRecording ? 'Recording...' : 'Stopped'}
            </span>
          </div>
        </div>

        <div className="status-card">
          <div className="status-icon status-icon-devices">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div className="status-info">
            <span className="status-label">Connected Devices</span>
            <span className="status-value">
              {devices.filter(d => d.status === 'online').length} / {devices.length}
            </span>
          </div>
        </div>

        <div className="status-card">
          <div className="status-icon status-icon-selected">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div className="status-info">
            <span className="status-label">Selected Device</span>
            <span className="status-value">
              {selectedDevice ? selectedDevice.device_name : 'None'}
            </span>
          </div>
        </div>
      </div>

      {/* Recording Controls */}
      <div className="recording-controls">
        <div className="controls-wrapper">
          <button 
            className={`btn-record ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={recordingStatus !== 'connected' && !isRecording}
          >
            {isRecording ? (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="12" height="16" rx="2"/>
                </svg>
                Stop Recording
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <circle cx="12" cy="12" r="8"/>
                </svg>
                Start Recording
              </>
            )}
          </button>
          
          {selectedDevice && (
            <button 
              className="btn-disconnect"
              onClick={disconnectDevice}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Disconnect
            </button>
          )}
          
          <button 
            className="btn-refresh" 
            onClick={fetchDevices}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Devices List */}
      <div className="devices-list">
        <h3>Registered Devices</h3>
        {error ? (
          <div className="error-message">
            <p>{error}</p>
            <button className="btn-secondary" onClick={fetchDevices}>Retry</button>
          </div>
        ) : devices.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            </div>
            <p>No devices registered yet</p>
            <button className="btn-primary" onClick={() => setShowRegisterModal(true)}>
              Register Your First Device
            </button>
          </div>
        ) : (
          <div className="devices-grid">
            {devices.map((device) => (
              <div 
                key={device.id} 
                className={`device-card ${selectedDevice?.id === device.id ? 'selected' : ''}`}
              >
                <div className="device-header">
                  <div className="device-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                      <line x1="8" y1="21" x2="16" y2="21"/>
                      <line x1="12" y1="17" x2="12" y2="21"/>
                    </svg>
                  </div>
                  <div className="device-info">
                    <h4>{device.device_name}</h4>
                    <span className="device-type">{device.device_type}</span>
                  </div>
                  <span className={`device-status ${device.status}`}>
                    <span className="status-dot"></span>
                    {device.status}
                  </span>
                </div>
                
                <div className="device-details">
                  <div className="detail-row">
                    <span className="detail-label">IP Address</span>
                    <span className="detail-value">{device.ip_address || '—'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">MAC Address</span>
                    <span className="detail-value">{device.mac_address || '—'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Last Connected</span>
                    <span className="detail-value">
                      {device.last_connected 
                        ? new Date(device.last_connected).toLocaleString() 
                        : 'Never'}
                    </span>
                  </div>
                </div>

                <div className="device-actions">
                  {selectedDevice?.id === device.id ? (
                    <button 
                      className="btn-disconnect-full"
                      onClick={disconnectDevice}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                        <polyline points="16 17 21 12 16 7"/>
                        <line x1="21" y1="12" x2="9" y2="12"/>
                      </svg>
                      Disconnect
                    </button>
                  ) : (
                    <button 
                      className="btn-connect"
                      onClick={() => connectToDevice(device)}
                      disabled={device.status === 'online'}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M5 12h14"/>
                        <path d="M12 5l7 7-7 7"/>
                      </svg>
                      {device.status === 'online' ? 'Connected' : 'Connect'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Register Device Modal */}
      {showRegisterModal && (
        <div className="modal-overlay" onClick={() => setShowRegisterModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Register IoT Device</h3>
              <button 
                className="modal-close" 
                onClick={() => setShowRegisterModal(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleRegisterDevice}>
              <div className="modal-body">
                <div className="form-group">
                  <label htmlFor="device_name">Device Name *</label>
                  <input
                    id="device_name"
                    type="text"
                    placeholder="e.g., Stethoscope-01"
                    value={registerForm.device_name}
                    onChange={(e) => setRegisterForm({...registerForm, device_name: e.target.value})}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="device_type">Device Type</label>
                  <select
                    id="device_type"
                    value={registerForm.device_type}
                    onChange={(e) => setRegisterForm({...registerForm, device_type: e.target.value})}
                  >
                    <option value="stethoscope">Stethoscope</option>
                    <option value="ecg">ECG Monitor</option>
                    <option value="heart_monitor">Heart Monitor</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label htmlFor="ip_address">IP Address *</label>
                  <input
                    id="ip_address"
                    type="text"
                    placeholder="e.g., 192.168.1.100"
                    value={registerForm.ip_address}
                    onChange={(e) => setRegisterForm({...registerForm, ip_address: e.target.value})}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="mac_address">MAC Address</label>
                  <input
                    id="mac_address"
                    type="text"
                    placeholder="e.g., AA:BB:CC:DD:EE:FF"
                    value={registerForm.mac_address}
                    onChange={(e) => setRegisterForm({...registerForm, mac_address: e.target.value})}
                  />
                </div>
              </div>
              
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowRegisterModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Register Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default IoTDevices;