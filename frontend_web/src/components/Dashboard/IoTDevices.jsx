// frontend_web/src/components/Dashboard/IoTDevices.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi, screeningService } from '../../services/api';
import './IoTDevices.css';

// ============================================
// PCG WAVEFORM COMPONENT
// ============================================
const PCGWaveform = ({ audioData, isRecording, deviceName }) => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const dataRef = useRef([]);
  
  useEffect(() => {
    dataRef.current = audioData || [];
  }, [audioData]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    const drawWaveform = () => {
      ctx.clearRect(0, 0, width, height);
      
      // Draw grid
      ctx.strokeStyle = 'rgba(0, 70, 79, 0.05)';
      ctx.lineWidth = 0.5;
      for (let i = 0; i < width; i += 20) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, height);
        ctx.stroke();
      }
      for (let i = 0; i < height; i += 20) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(width, i);
        ctx.stroke();
      }

      const data = dataRef.current;
      
      if (data.length === 0) {
        // Draw flat line
        ctx.strokeStyle = isRecording ? '#00464F' : '#94a3b8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
        
        // Draw "No Signal" text
        ctx.fillStyle = '#94a3b8';
        ctx.font = '14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(isRecording ? 'Receiving signal...' : 'No signal - Connect device', width / 2, height / 2 - 10);
        return;
      }

      // Draw waveform
      const step = Math.max(1, Math.floor(data.length / width));
      const normalizedData = [];
      
      for (let i = 0; i < width; i++) {
        const start = Math.floor(i * step);
        const end = Math.min(start + step, data.length);
        let sum = 0;
        for (let j = start; j < end; j++) {
          sum += data[j] || 0;
        }
        normalizedData.push(sum / (end - start));
      }

      // Draw main waveform
      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      if (isRecording) {
        gradient.addColorStop(0, '#00464F');
        gradient.addColorStop(0.5, '#0D9488');
        gradient.addColorStop(1, '#00464F');
      } else {
        gradient.addColorStop(0, '#94a3b8');
        gradient.addColorStop(1, '#64748b');
      }

      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2;
      ctx.shadowColor = isRecording ? 'rgba(0, 70, 79, 0.3)' : 'transparent';
      ctx.shadowBlur = isRecording ? 8 : 0;
      
      ctx.beginPath();
      for (let i = 0; i < normalizedData.length; i++) {
        const x = i;
        const y = height / 2 - (normalizedData[i] * height * 0.8);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      // Draw fill under waveform
      ctx.shadowBlur = 0;
      const fillGradient = ctx.createLinearGradient(0, 0, 0, height);
      if (isRecording) {
        fillGradient.addColorStop(0, 'rgba(0, 70, 79, 0.2)');
        fillGradient.addColorStop(1, 'rgba(0, 70, 79, 0)');
      } else {
        fillGradient.addColorStop(0, 'rgba(148, 163, 184, 0.1)');
        fillGradient.addColorStop(1, 'rgba(148, 163, 184, 0)');
      }
      
      ctx.fillStyle = fillGradient;
      ctx.beginPath();
      ctx.moveTo(0, height);
      for (let i = 0; i < normalizedData.length; i++) {
        const x = i;
        const y = height / 2 - (normalizedData[i] * height * 0.8);
        ctx.lineTo(x, y);
      }
      ctx.lineTo(width, height);
      ctx.closePath();
      ctx.fill();

      // Draw recording indicator
      if (isRecording) {
        ctx.fillStyle = '#dc2626';
        ctx.beginPath();
        ctx.arc(width - 20, 20, 6, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.fillStyle = '#dc2626';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText('REC', width - 30, 24);
      }
    };

    const animate = () => {
      drawWaveform();
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isRecording]);

  return (
    <div className="pcg-waveform-container">
      <div className="waveform-header">
        <span className="waveform-title">
          {deviceName || 'PCG Waveform'}
        </span>
        <span className={`waveform-status ${isRecording ? 'recording' : 'idle'}`}>
          {isRecording ? '● Live' : '○ Idle'}
        </span>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={200}
        className="pcg-waveform-canvas"
      />
    </div>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const IoTDevices = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState('idle');
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [waveformData, setWaveformData] = useState([]);
  const [showWaveform, setShowWaveform] = useState(false);
  const [signalQuality, setSignalQuality] = useState(0);
  const [recordingProgress, setRecordingProgress] = useState(0);
  // Scenario 8 — Device Health: battery/signal telemetry from the ESP32.
  const [battery, setBattery] = useState(null);       // 0-100, or null if unknown
  const [rssi, setRssi] = useState(null);             // signal strength (dBm)
  const [deviceSqa, setDeviceSqa] = useState(null);   // on-device SQA report from ESP32
  const BATTERY_CRITICAL = 15;                         // matches firmware threshold
  const batteryLow = battery !== null && battery < BATTERY_CRITICAL;
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
  const waveformBuffer = useRef([]);
  const maxBufferSize = 1024;

  // Web Bluetooth (must match iot/src/Config.h — BLE_SERVICE_UUID / BLE_CHAR_UUID)
  const BLE_SERVICE_UUID = '4fafc201-1fb5-459e-8fcc-c5c9c331914b';
  const BLE_CHAR_UUID = 'beb5483e-36e1-4688-b7f5-ea07361b26a8';
  const bleDevice = useRef(null);
  const bleCharacteristic = useRef(null);

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
      setShowWaveform(true);
      setWaveformData([]);
      waveformBuffer.current = [];

      // Close existing connection if any
      if (wsConnection.current) {
        wsConnection.current.close();
      }

      // Create WebSocket connection
      const ws = new WebSocket(`ws://${device.ip_address}/audio`);
      
      ws.onopen = () => {
        console.log('Connected to IoT device:', device.device_name);
        setRecordingStatus('connected');
        updateDeviceStatus(device.id, 'online');
        setSignalQuality(100);
      };
      
      ws.onmessage = (event) => {
        handleAudioData(event.data);
      };
      
      ws.onclose = () => {
        console.log('Disconnected from IoT device');
        setRecordingStatus('disconnected');
        setShowWaveform(false);
        updateDeviceStatus(device.id, 'offline');
        setSignalQuality(0);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setRecordingStatus('error');
        setSignalQuality(0);
        alert('Failed to connect to device. Please check the IP address and try again.');
      };
      
      wsConnection.current = ws;
      
    } catch (error) {
      console.error('Failed to connect to device:', error);
      setRecordingStatus('error');
      alert('Failed to connect to device. Please check the IP address and try again.');
    }
  };

  // Connect to the Saka stethoscope directly over Bluetooth (Web Bluetooth API).
  // Requires HTTPS + a Chromium browser and a user gesture. Uses the same audio
  // pipeline / waveform as the WebSocket path.
  const connectViaBluetooth = async () => {
    if (!navigator.bluetooth) {
      alert('Web Bluetooth is not supported in this browser. Use Chrome or Edge over HTTPS.');
      return;
    }
    try {
      setRecordingStatus('connecting');
      const device = await navigator.bluetooth.requestDevice({
        filters: [{ services: [BLE_SERVICE_UUID] }],
        optionalServices: [BLE_SERVICE_UUID],
      });

      bleDevice.current = device;
      device.addEventListener('gattserverdisconnected', handleBluetoothDisconnected);

      const server = await device.gatt.connect();
      const service = await server.getPrimaryService(BLE_SERVICE_UUID);
      const characteristic = await service.getCharacteristic(BLE_CHAR_UUID);
      bleCharacteristic.current = characteristic;

      // Stream audio via notifications, reusing the existing waveform handler.
      await characteristic.startNotifications();
      characteristic.addEventListener('characteristicvaluechanged', handleBluetoothNotification);

      // Ask the firmware to start streaming (matches BLE_Handler onWrite "START").
      try {
        await characteristic.writeValue(new TextEncoder().encode('START'));
      } catch (e) {
        console.warn('Could not send START command:', e);
      }

      setSelectedDevice({
        id: device.id || 'ble-device',
        device_name: device.name || 'Saka Stethoscope (BLE)',
        connection: 'bluetooth',
      });
      setShowWaveform(true);
      setWaveformData([]);
      waveformBuffer.current = [];
      setRecordingStatus('connected');
      setSignalQuality(100);
    } catch (error) {
      // A user cancelling the chooser throws NotFoundError — treat as a no-op.
      if (error?.name === 'NotFoundError') {
        setRecordingStatus('idle');
        return;
      }
      console.error('Bluetooth connection failed:', error);
      setRecordingStatus('error');
      alert('Bluetooth connection failed: ' + (error?.message || error));
    }
  };

  // Decode raw int16 PCM notifications into normalised samples for the waveform.
  const handleBluetoothNotification = (event) => {
    const view = event.target.value; // DataView
    const samples = [];
    for (let i = 0; i + 1 < view.byteLength; i += 2) {
      samples.push(view.getInt16(i, true) / 32768);
    }
    if (samples.length) {
      handleAudioData({ type: 'waveform', data: samples });
    }
  };

  const handleBluetoothDisconnected = () => {
    setRecordingStatus('disconnected');
    setShowWaveform(false);
    setSignalQuality(0);
  };

  // Disconnect from device
  const disconnectDevice = async () => {
    if (wsConnection.current) {
      wsConnection.current.close();
      wsConnection.current = null;
    }
    // Tear down any Bluetooth connection too.
    if (bleCharacteristic.current) {
      try {
        await bleCharacteristic.current.writeValue(new TextEncoder().encode('STOP'));
        await bleCharacteristic.current.stopNotifications();
        bleCharacteristic.current.removeEventListener('characteristicvaluechanged', handleBluetoothNotification);
      } catch (e) { /* ignore */ }
      bleCharacteristic.current = null;
    }
    if (bleDevice.current) {
      bleDevice.current.removeEventListener('gattserverdisconnected', handleBluetoothDisconnected);
      if (bleDevice.current.gatt?.connected) bleDevice.current.gatt.disconnect();
      bleDevice.current = null;
    }
    if (isRecording) {
      stopRecording();
    }
    setSelectedDevice(null);
    setRecordingStatus('idle');
    setShowWaveform(false);
    setWaveformData([]);
    waveformBuffer.current = [];
    setSignalQuality(0);
  };

  // Handle incoming audio data
  const handleAudioData = (data) => {
    try {
      const audioData = typeof data === 'string' ? JSON.parse(data) : data;
      
      if (audioData.type === 'audio_chunk' || audioData.type === 'waveform') {
        // Handle waveform data for visualization
        const rawData = audioData.data || audioData;
        let values;
        
        if (typeof rawData === 'string') {
          // Base64 encoded data
          const binaryString = atob(rawData);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          values = Array.from(bytes);
        } else if (Array.isArray(rawData)) {
          values = rawData;
        } else if (rawData.buffer) {
          values = Array.from(new Float32Array(rawData.buffer));
        } else {
          values = [];
        }

        // Update waveform buffer
        waveformBuffer.current = [...waveformBuffer.current, ...values];
        if (waveformBuffer.current.length > maxBufferSize) {
          waveformBuffer.current = waveformBuffer.current.slice(-maxBufferSize);
        }
        setWaveformData(waveformBuffer.current);
        
        // Store audio data if recording
        if (isRecording) {
          audioChunks.current.push(values);
          setRecordingProgress(prev => Math.min(prev + 5, 95));
        }

        // Update signal quality
        if (values.length > 0) {
          const rms = Math.sqrt(values.reduce((sum, v) => sum + v * v, 0) / values.length);
          const quality = Math.min(100, Math.round(rms * 100));
          setSignalQuality(Math.max(quality, 5));
        }
      } else if (audioData.type === 'recording_complete') {
        console.log('Recording complete received from device');
        processRecording();
      } else if (audioData.type === 'signal_quality') {
        setSignalQuality(audioData.quality || 50);
        // On-device SQA report from the ESP32 (see iot/src/SignalQuality.cpp):
        // surface the block/warning state so the nurse gets instant feedback.
        setDeviceSqa({
          blocked: !!audioData.blocked,
          code: audioData.code || 'ok',
          message: audioData.message || '',
          bpm: audioData.bpm || 0,
          rms_dbfs: audioData.rms_dbfs,
          clip_ratio: audioData.clip_ratio,
          final: !!audioData.final,
        });
      }

      // Scenario 8 — Device Health telemetry (sent by the ESP32 on GET_STATUS).
      if (audioData.battery_percent !== undefined) {
        setBattery(audioData.battery_percent);
      }
      if (audioData.rssi !== undefined) {
        setRssi(audioData.rssi);
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
      audioChunks.current = [];
      setRecordingProgress(0);
      setDeviceSqa(null);   // clear any prior on-device quality report
      
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
      wsConnection.current.send(JSON.stringify({ 
        action: 'stop_recording',
        timestamp: new Date().toISOString()
      }));
      
      setIsRecording(false);
      setRecordingStatus('processing');
      setRecordingProgress(100);
      
      setTimeout(() => {
        processRecording();
      }, 1500);
      
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
        setRecordingProgress(0);
        return;
      }

      // Flatten audio chunks
      const allValues = audioChunks.current.flat();
      const audioBuffer = new Float32Array(allValues);
      
      // Create WAV file
      const wavBlob = createWavBlob(audioBuffer);
      const file = new File([wavBlob], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
      
      // Send to backend for analysis
      await analyzeRecording(file);
      
      // Reset
      audioChunks.current = [];
      setRecordingStatus('idle');
      setRecordingProgress(0);
      
    } catch (error) {
      console.error('Error processing recording:', error);
      setRecordingStatus('error');
      setRecordingProgress(0);
    }
  };

  // Create WAV blob from audio data
  const createWavBlob = (audioData) => {
    const sampleRate = 44100;
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = audioData.length * bitsPerSample / 8;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    // RIFF header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    // Write audio data
    const offset = 44;
    for (let i = 0; i < audioData.length; i++) {
      const value = Math.max(-1, Math.min(1, audioData[i] || 0));
      const intValue = value * 32767;
      view.setInt16(offset + i * 2, intValue, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  };

  const writeString = (view, offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  // Analyze recording using screening service
  const analyzeRecording = async (file) => {
    try {
      const patientId = prompt('Enter patient ID for this recording:');
      if (!patientId) {
        alert('Patient ID is required to save the recording');
        return;
      }

      const doctorId = user?.id;
      const result = await screeningService.predict(file, patientId, doctorId);
      
      if (result.success || result.prediction) {
        const recordingData = {
          patient_id: patientId,
          doctor_id: doctorId,
          file_name: `IoT_recording_${Date.now()}.wav`,
          prediction: result.prediction || result.class || 'Unknown',
          confidence: result.confidence || 0,
          recording_date: new Date().toISOString(),
          notes: `Recorded via IoT stethoscope on ${new Date().toLocaleString()}`,
          device_name: selectedDevice?.device_name || 'Unknown IoT Device'
        };

        await databaseApi.saveRecording(recordingData);
        
        alert(`✅ Analysis complete: ${recordingData.prediction} (${(recordingData.confidence * 100).toFixed(1)}% confidence)`);
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
        <div className="header-actions">
          <button className="btn-bluetooth" onClick={connectViaBluetooth} title="Connect the stethoscope over Bluetooth">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6.5 6.5 L17.5 17.5 L12 23 V1 L17.5 6.5 L6.5 17.5"/>
            </svg>
            Connect via Bluetooth
          </button>
          <button className="btn-primary" onClick={() => setShowRegisterModal(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Register Device
          </button>
        </div>
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
          <div className="status-icon status-icon-signal">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L15 9"/>
              <path d="M22 2L17 13L13 9L22 2Z"/>
            </svg>
          </div>
          <div className="status-info">
            <span className="status-label">Signal Quality</span>
            <span className={`status-value ${signalQuality > 70 ? 'good' : signalQuality > 30 ? 'fair' : 'poor'}`}>
              {signalQuality > 70 ? 'Good' : signalQuality > 30 ? 'Fair' : 'Poor'} ({signalQuality}%)
            </span>
          </div>
        </div>

        {/* Scenario 8 — Device Health: battery status card */}
        <div className="status-card">
          <div className="status-icon status-icon-signal">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="1" y="6" width="18" height="12" rx="2" ry="2"/>
              <line x1="23" y1="10" x2="23" y2="14"/>
            </svg>
          </div>
          <div className="status-info">
            <span className="status-label">Battery {rssi !== null ? `· ${rssi} dBm` : ''}</span>
            <span className={`status-value ${battery === null ? '' : battery < BATTERY_CRITICAL ? 'poor' : battery < 40 ? 'fair' : 'good'}`}>
              {battery === null ? 'Unknown' : `${battery}%${battery < BATTERY_CRITICAL ? ' · Charge!' : ''}`}
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

      {/* PCG Waveform Display */}
      {showWaveform && (
        <div className="waveform-section">
          <PCGWaveform 
            audioData={waveformData}
            isRecording={isRecording}
            deviceName={selectedDevice?.device_name}
          />
          {isRecording && (
            <div className="recording-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${recordingProgress}%` }}
                />
              </div>
              <span className="progress-text">{recordingProgress}%</span>
            </div>
          )}
        </div>
      )}

      {/* Scenario 8 — Device Health: block recording on a dying battery, whose
          BLE jitter corrupts audio with murmur-like clicks. */}
      {batteryLow && (
        <div className="sqa-block" style={{ marginTop: 12 }}>
          <div className="sqa-block-header">
            <span className="sqa-block-icon">🪫</span>
            <span className="sqa-block-title">Charge device to ensure signal integrity</span>
          </div>
          <p className="sqa-block-message">
            Stethoscope battery is at {battery}%. A low battery causes Bluetooth to
            drop packets, adding digital clicks that can look like murmurs. Please
            charge the device before recording.
          </p>
        </div>
      )}

      {/* On-device Signal Quality feedback (from the ESP32, scenarios 1/2/3) */}
      {deviceSqa && (isRecording || deviceSqa.final) && deviceSqa.code !== 'ok' && (
        <div className={deviceSqa.blocked ? 'sqa-block' : 'sqa-warnings'} style={{ marginTop: 12 }}>
          {deviceSqa.blocked ? (
            <>
              <div className="sqa-block-header">
                <span className="sqa-block-icon">🎧</span>
                <span className="sqa-block-title">
                  {deviceSqa.final ? 'Recording rejected by device' : 'Signal problem detected'}
                </span>
              </div>
              <p className="sqa-block-message">{deviceSqa.message}</p>
              <div className="sqa-metrics">
                {deviceSqa.rms_dbfs !== undefined && <span>Loudness: {deviceSqa.rms_dbfs} dBFS</span>}
                {deviceSqa.bpm > 0 && <span>Est. rate: {deviceSqa.bpm} BPM</span>}
                {deviceSqa.clip_ratio !== undefined && <span>Clipping: {(deviceSqa.clip_ratio * 100).toFixed(1)}%</span>}
              </div>
            </>
          ) : (
            <div className="sqa-warning">
              <span className="sqa-warning-icon">🎧</span>
              <div>
                <div className="sqa-warning-title">Device signal note</div>
                <div className="sqa-warning-message">{deviceSqa.message}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Recording Controls */}
      <div className="recording-controls">
        <div className="controls-wrapper">
          <button
            className={`btn-record ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={(recordingStatus !== 'connected' && !isRecording) || (batteryLow && !isRecording)}
            title={batteryLow ? 'Charge device to ensure signal integrity' : undefined}
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