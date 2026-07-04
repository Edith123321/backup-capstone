// frontend_web/src/services/api.js
import axios from 'axios';

// Use Vite's import.meta.env for Vite projects
const API_URL =axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://capstone-be-yxzd.onrender.com",
  withCredentials: true,
});

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============ SCREENING SERVICES ============
export const screeningService = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/api/v1/screening/health');
    return response.data;
  },

  // Get model info
  getModelInfo: async () => {
    const response = await api.get('/api/v1/screening/info');
    return response.data;
  },

  // Predict a single heart sound
  predict: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/v1/screening/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Batch predict multiple files
  batchPredict: async (files) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    const response = await api.post('/api/v1/screening/batch_predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get result by ID
  getResult: async (resultId) => {
    const response = await api.get(`/api/v1/screening/results/${resultId}`);
    return response.data;
  }
};

// ============ DATABASE SERVICES ============
export const databaseApi = {
  // ---- PATIENTS ----
  getPatients: async (doctorId) => {
    const response = await api.get(`/database/patients?doctor_id=${doctorId}`);
    return response.data;
  },

  createPatient: async (data) => {
    const response = await api.post('/database/patients', data);
    return response.data;
  },

  getPatient: async (patientId) => {
    const response = await api.get(`/api/v1/database/patients/${patientId}`);
    return response.data;
  },

  // ---- TRIAGE ----
  getTriageByDoctor: async (doctorId) => {
    const response = await api.get(`/api/v1/database/triage/doctor/${doctorId}`);
    return response.data;
  },

  getTriageByPatient: async (patientId) => {
    const response = await api.get(`/api/v1/database/triage/patient/${patientId}`);
    return response.data;
  },

  createTriage: async (data) => {
    const response = await api.post('/api/v1/database/triage', data);
    return response.data;
  },

  calculateTriage: async (data) => {
    const response = await api.post('/api/v1/database/triage/calculate', data);
    return response.data;
  },

  // ---- HEART SOUND RECORDINGS ----
  getRecordings: async (patientId) => {
    const response = await api.get(`/api/v1/database/recordings/patient/${patientId}`);
    return response.data;
  },

  saveRecording: async (data) => {
    const response = await api.post('/api/v1/database/recordings', data);
    return response.data;
  },

  // ---- IOT DEVICES ----
  getDevices: async (doctorId) => {
    const response = await api.get(`/api/v1/database/devices/${doctorId}`);
    return response.data;
  },

  registerDevice: async (data) => {
    const response = await api.post('/api/v1/database/devices/register', data);
    return response.data;
  },

  updateDeviceStatus: async (deviceId, status) => {
    const response = await api.put(`/api/v1/database/devices/${deviceId}/status`, { status });
    return response.data;
  },
};

// ============ PATIENT SERVICE (Mock data fallback) ============
export const patientService = {
  // Get all patients (uses real API if available, falls back to mock)
  getPatients: async (doctorId) => {
    try {
      const response = await databaseApi.getPatients(doctorId);
      if (response.success) {
        return response.patients;
      }
      throw new Error('Failed to fetch patients');
    } catch (error) {
      console.warn('Using mock patient data:', error);
      // Mock data fallback
      return [
        { id: '1', name: 'Sarah Kamau', age: 12, gender: 'Female', result: 'RHD', date: '2026-06-25', confidence: 97.2 },
        { id: '2', name: 'John Otieno', age: 8, gender: 'Male', result: 'Normal', date: '2026-06-25', confidence: 98.8 },
        { id: '3', name: 'Mary Wanjiku', age: 14, gender: 'Female', result: 'Normal', date: '2026-06-24', confidence: 99.1 },
        { id: '4', name: 'Peter Mwangi', age: 10, gender: 'Male', result: 'RHD', date: '2026-06-24', confidence: 95.8 },
      ];
    }
  },

  // Get patient by ID
  getPatientById: async (id) => {
    try {
      const response = await databaseApi.getPatient(id);
      if (response.success) {
        return response.patient;
      }
      throw new Error('Failed to fetch patient');
    } catch (error) {
      console.warn('Using mock patient data:', error);
      // Mock data fallback
      return {
        id: id,
        name: 'Sarah Kamau',
        age: 12,
        gender: 'Female',
        result: 'RHD',
        confidence: 97.2,
        dateOfBirth: '2014-06-15',
        lastScreening: '2026-06-25',
        screenings: [
          { date: '2026-06-25', result: 'RHD', confidence: 97.2 },
          { date: '2026-05-20', result: 'Normal', confidence: 95.8 }
        ],
        notes: 'Patient presents with mild fever and chest pain.',
        doctor: 'Dr. Jane Smith',
        location: 'Nairobi, Kenya'
      };
    }
  },

  // Create a new patient
  createPatient: async (data) => {
    const response = await databaseApi.createPatient(data);
    return response;
  },

  // Get screening history
  getHistory: async () => {
    // Mock data - replace with actual API call
    return [
      { id: '1', name: 'Sarah Kamau', age: 12, result: 'RHD', date: '2026-06-25', confidence: 97.2, doctor: 'Dr. Smith' },
      { id: '2', name: 'John Otieno', age: 8, result: 'Normal', date: '2026-06-25', confidence: 98.8, doctor: 'Dr. Jones' },
      { id: '3', name: 'Mary Wanjiku', age: 14, result: 'Normal', date: '2026-06-24', confidence: 99.1, doctor: 'Dr. Smith' },
      { id: '4', name: 'Peter Mwangi', age: 10, result: 'RHD', date: '2026-06-24', confidence: 95.8, doctor: 'Dr. Williams' },
    ];
  }
};

// ============ STATS SERVICE ============
export const statsService = {
  // Get dashboard stats
  getStats: async (doctorId) => {
    try {
      // Try to get real data
      const patients = await patientService.getPatients(doctorId);
      const triage = await databaseApi.getTriageByDoctor(doctorId);
      
      return {
        totalPatients: patients?.length || 0,
        todayScreenings: patients?.filter(p => {
          const today = new Date().toDateString();
          return new Date(p.date).toDateString() === today;
        }).length || 0,
        accuracy: '98.4%',
        flagged: triage?.triage?.filter(t => t.triage_color === 'Red' || t.triage_color === 'Orange').length || 0,
        recentActivities: [
          { type: 'upload', title: 'New heart sound uploaded', patient: patients?.[0]?.name || 'N/A', time: '2 min ago' },
          { type: 'result', title: 'RHD detected', patient: patients?.[1]?.name || 'N/A', time: '15 min ago' }
        ],
        triageItems: triage?.triage?.slice(0, 5).map(t => ({
          id: t.id,
          patientName: t.patient_name || 'Unknown',
          urgency: t.triage_level || 'Unknown',
          time: new Date(t.created_at).toLocaleString(),
          reason: t.chief_complaint || 'No details'
        })) || []
      };
    } catch (error) {
      console.warn('Using mock stats data:', error);
      // Mock data fallback
      return {
        totalPatients: 14,
        todayScreenings: 5,
        accuracy: '98.4%',
        flagged: 3,
        recentActivities: [
          { type: 'upload', title: 'New heart sound uploaded', patient: 'Sarah Kamau', time: '2 min ago' },
          { type: 'result', title: 'RHD detected', patient: 'John Otieno', time: '15 min ago' }
        ],
        triageItems: [
          { id: '1', patientName: 'Grace Akinyi', urgency: 'High', time: '2 hours ago', reason: 'Abnormal heart sound' },
          { id: '2', patientName: 'James Odhiambo', urgency: 'Medium', time: '4 hours ago', reason: 'Irregular rhythm' }
        ]
      };
    }
  }
};

export default api;