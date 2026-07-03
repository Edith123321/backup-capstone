// frontend_web/src/components/Dashboard/IoTDevices.jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import './DashboardLayout.css';

const IoTDevices = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [audioStream, setAudioStream] = useState(null);
  const [wsConnection, setWsConnection] = useState(null);
  const [recordingStatus, setRecordingStatus] = useState('idle');

  useEffect(() => {
    fetchDevices();
  }, [user]);

  const fetchDevices = async () => {
    if (!user?.id) return;
    
    try {
      const response = await fetch(`/api/v1/database/devices/${user.id}`);
      const data = await response.json();
      if (data.success) {
        setDevices(data.devices);
      }
    } catch (error) {
      console.error('Error fetching devices:', error);
    }
  };

  const connectToDevice = async (device) => {
    try {
      // Connect to WebSocket for audio streaming
      const ws = new WebSocket(`ws://${device.ip_address}/audio`);
      
      ws.onopen = () => {
        console.log('Connected to IoT device');
        setWsConnection(ws);
        setRecordingStatus('connected');
      };
      
      ws.onmessage = (event) => {
        // Handle incoming audio data
        console.log('Audio data received:', event.data);
      };
      
      ws.onclose = () => {
        console.log('Disconnected from IoT device');
        setRecordingStatus('disconnected');
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setRecordingStatus('error');
      };
    } catch (error) {
      console.error('Failed to connect to device:', error);
      setRecordingStatus('error');
    }
  };

  const startRecording = () => {
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      wsConnection.send(JSON.stringify({ action: 'start_recording' }));
      setIsRecording(true);
      setRecordingStatus('recording');
      console.log('🎙️ Recording started...');
    } else {
      alert('Please connect to a device first');
    }
  };

  const stopRecording = () => {
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      wsConnection.send(JSON.stringify({ action: 'stop_recording' }));
      setIsRecording(false);
      setRecordingStatus('idle');
      console.log('⏹️ Recording stopped');
    }
  };

  const registerDevice = async () => {
    const deviceData = {
      doctor_id: user.id,
      device_name: 'ESP32 Stethoscope',
      device_type: 'stethoscope',
      ip_address: prompt('Enter device IP address:'),
      mac_address: prompt('Enter device MAC address:')
    };
    
    if (deviceData.ip_address) {
      try {
        const response = await fetch('/api/v1/database/devices/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(deviceData)
        });
        const data = await response.json();
        if (data.success) {
          alert('Device registered successfully!');
          fetchDevices();
        }
      } catch (error) {
        console.error('Error registering device:', error);
      }
    }
  };

  return (
    <div className="iot-dashboard">
      <div className="dashboard-header">
        <h1>📡 IoT Stethoscope Devices</h1>
        <button className="btn-primary" onClick={registerDevice}>
          + Register New Device
        </button>
      </div>

      <div className="iot-status">
        <div className="status-card">
          <span className="status-label">Connection Status</span>
          <span className={`status-value ${recordingStatus}`}>
            {recordingStatus === 'connected' ? '🟢 Connected' :
             recordingStatus === 'recording' ? '🔴 Recording' :
             recordingStatus === 'disconnected' ? '🔴 Disconnected' :
             recordingStatus === 'error' ? '⚠️ Error' : '⚪ Idle'}
          </span>
        </div>
        
        <div className="status-card">
          <span className="status-label">Recording</span>
          <span className="status-value">
            {isRecording ? '🔴 Recording...' : '⏹️ Stopped'}
          </span>
        </div>
      </div>

      <div className="device-controls">
        <div className="control-group">
          <button 
            className={`btn-record ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={recordingStatus !== 'connected'}
          >
            {isRecording ? '⏹️ Stop Recording' : '🎙️ Start Recording'}
          </button>
        </div>
      </div>

      <div className="devices-list">
        <h3>Connected Devices</h3>
        {devices.length === 0 ? (
          <p className="no-devices">No devices registered. Add your IoT stethoscope.</p>
        ) : (
          devices.map((device) => (
            <div key={device.id} className="device-card">
              <div className="device-info">
                <span className="device-name">{device.device_name}</span>
                <span className="device-type">{device.device_type}</span>
                <span className={`device-status ${device.status}`}>
                  {device.status}
                </span>
                <span className="device-ip">IP: {device.ip_address}</span>
              </div>
              <button 
                className="btn-connect"
                onClick={() => connectToDevice(device)}
                disabled={device.status === 'online'}
              >
                {device.status === 'online' ? 'Connected' : 'Connect'}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default IoTDevices;