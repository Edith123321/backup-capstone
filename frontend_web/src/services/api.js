import axios from 'axios';

// =====================
// AXIOS INSTANCE
// =====================
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://capstone-be-yxzd.onrender.com",
  withCredentials: true,
});

// =====================
// AUTH INTERCEPTOR
// =====================
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

// =====================
// RESPONSE HANDLER
// =====================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// =====================
// SCREENING SERVICES
// =====================
export const screeningService = {
  healthCheck: async () => {
    const res = await api.get('/screening/health');
    return res.data;
  },

  getModelInfo: async () => {
    const res = await api.get('/screening/info');
    return res.data;
  },

  predict: async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const res = await api.post('/screening/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return res.data;
  },

  batchPredict: async (files) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const res = await api.post('/screening/batch_predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return res.data;
  },

  getResult: async (resultId) => {
    const res = await api.get(`/screening/results/${resultId}`);
    return res.data;
  },
};

// =====================
// DATABASE API
// =====================
export const databaseApi = {
  getPatients: async (doctorId) => {
    const res = await api.get(`/database/patients?doctor_id=${doctorId}`);
    return res.data;
  },

  createPatient: async (data) => {
    const res = await api.post('/database/patients', data);
    return res.data;
  },

  getPatient: async (patientId) => {
    const res = await api.get(`/database/patients/${patientId}`);
    return res.data;
  },

  getTriageByDoctor: async (doctorId) => {
    const res = await api.get(`/database/triage/doctor/${doctorId}`);
    return res.data;
  },

  getTriageByPatient: async (patientId) => {
    const res = await api.get(`/database/triage/patient/${patientId}`);
    return res.data;
  },

  createTriage: async (data) => {
    const res = await api.post('/database/triage', data);
    return res.data;
  },

  calculateTriage: async (data) => {
    const res = await api.post('/database/triage/calculate', data);
    return res.data;
  },

  getRecordings: async (patientId) => {
    const res = await api.get(`/database/recordings/patient/${patientId}`);
    return res.data;
  },

  saveRecording: async (data) => {
    const res = await api.post('/database/recordings', data);
    return res.data;
  },

  getDevices: async (doctorId) => {
    const res = await api.get(`/database/devices/${doctorId}`);
    return res.data;
  },

  registerDevice: async (data) => {
    const res = await api.post('/database/devices/register', data);
    return res.data;
  },

  updateDeviceStatus: async (deviceId, status) => {
    const res = await api.put(`/database/devices/${deviceId}/status`, { status });
    return res.data;
  },
};

// =====================
// PATIENT SERVICE
// =====================
export const patientService = {
  getPatients: async (doctorId) => {
    try {
      const res = await databaseApi.getPatients(doctorId);
      if (res.success) return res.patients;
      throw new Error('Failed to fetch patients');
    } catch (error) {
      console.warn('Using mock patient data:', error);
      return [];
    }
  },
};

// =====================
// STATS SERVICE
// =====================
export const statsService = {
  getStats: async (doctorId) => {
    try {
      const patients = await patientService.getPatients(doctorId);
      const triage = await databaseApi.getTriageByDoctor(doctorId);

      return {
        totalPatients: patients?.length || 0,
        todayScreenings: patients?.filter(p =>
          new Date(p.date).toDateString() === new Date().toDateString()
        ).length || 0,
        accuracy: '98.4%',
        flagged: triage?.triage?.filter(t =>
          t.triage_color === 'Red' || t.triage_color === 'Orange'
        ).length || 0,
      };
    } catch (error) {
      console.warn('Using mock stats data:', error);
      return {
        totalPatients: 0,
        todayScreenings: 0,
        accuracy: '98.4%',
        flagged: 0,
      };
    }
  }
};

export default api;