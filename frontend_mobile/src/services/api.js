// frontend_mobile/src/services/api.js
import axios from 'axios';
import * as FileSystem from 'expo-file-system';

// Get API URL from environment or use default
const API_URL = 'http://localhost:5001/api/v1/screening';

// For physical device, use your computer's IP address
// const API_URL = 'http://192.168.1.100:5001/api/v1/screening';

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export const predictHeartSound = async (file) => {
  try {
    const formData = new FormData();
    
    // Handle both DocumentPicker and Recording results
    if (file.uri) {
      // For DocumentPicker result
      formData.append('file', {
        uri: file.uri,
        name: file.name || 'recording.wav',
        type: 'audio/wav',
      });
    } else {
      // For FileSystem result
      formData.append('file', {
        uri: file,
        name: 'recording.wav',
        type: 'audio/wav',
      });
    }

    const response = await api.post('/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    if (error.response) {
      throw new Error(error.response.data.error || 'Server error');
    } else if (error.request) {
      throw new Error('No response from server. Please check your connection.');
    } else {
      throw new Error(error.message || 'Failed to analyze heart sound');
    }
  }
};

export const healthCheck = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};

export const getModelInfo = async () => {
  try {
    const response = await api.get('/info');
    return response.data;
  } catch (error) {
    console.error('Failed to get model info:', error);
    throw error;
  }
};