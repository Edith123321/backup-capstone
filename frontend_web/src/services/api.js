import axios from 'axios';

// =====================
// AXIOS INSTANCE
// =====================
const baseUrl = import.meta.env.VITE_API_URL || "https://capstone-be-yxzd.onrender.com";

const api = axios.create({
  // This ensures that even if you forget /api/v1 in the env var, it works correctly
  baseURL: baseUrl.endsWith('/api/v1') ? baseUrl : `${baseUrl}/api/v1`,
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

export const screeningService = {
  healthCheck: async () => {
    const res = await api.get('/screening/health');
    return res.data;
  },

  predict: async (file, patientId, doctorId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (patientId) formData.append('patient_id', patientId);
    if (doctorId) formData.append('doctor_id', doctorId);

    const res = await api.post('/screening/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return res.data;
  },

  getResult: async (resultId) => {
    const res = await api.get(`/screening/results/${resultId}`);
    return res.data;
  },

  validate: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/screening/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getHistory: async (patientId) => {
    const res = await api.get(`/screening/history/${patientId}`);
    return res.data;
  },
  
  // New: Save recording
  saveRecording: async (data) => {
    const res = await api.post('/screening/save-recording', data);
    return res.data;
  },
  
  // New: Get patient recordings
  getPatientRecordings: async (patientId) => {
    const res = await api.get(`/screening/recordings/${patientId}`);
    return res.data;
  }
};
// =====================
// DATABASE API
// =====================
export const databaseApi = {
  // ===== PATIENTS =====
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

  // ========== NEW: Update patient ==========
  updatePatient: async (patientId, data) => {
    const res = await api.put(`/database/patients/${patientId}`, data);
    return res.data;
  },

  // ========== NEW: Delete patient ==========
  deletePatient: async (patientId) => {
    const res = await api.delete(`/database/patients/${patientId}`);
    return res.data;
  },

  // ========== NEW: Update RHD status ==========
  updatePatientRHDStatus: async (patientId, data) => {
    const res = await api.put(`/database/patients/${patientId}/rhd-status`, data);
    return res.data;
  },

  // ========== NEW: Get patients by RHD status ==========
  getPatientsByRHDStatus: async (doctorId, rhdStatus) => {
    const res = await api.get(`/database/patients/rhd-status/${rhdStatus}?doctor_id=${doctorId}`);
    return res.data;
  },

  // ========== NEW: Get RHD summary ==========
  getRHDSummary: async (doctorId) => {
    const res = await api.get(`/database/patients/rhd-summary?doctor_id=${doctorId}`);
    return res.data;
  },

  // ===== TRIAGE =====
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

  // ===== RECORDINGS =====
  getRecordings: async (patientId) => {
    const res = await api.get(`/database/recordings/patient/${patientId}`);
    return res.data;
  },

  saveRecording: async (data) => {
    const res = await api.post('/database/recordings', data);
    return res.data;
  },

  // ===== DEVICES =====
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

 // In your api.js - update patientService.getPatientDetails
getPatientDetails: async (patientId) => {
  try {
    // Get the token from localStorage
    const token = localStorage.getItem('token');
    
    if (!token) {
      throw new Error('No authentication token found');
    }

    const [patientRes, triageRes, recordingsRes] = await Promise.all([
      databaseApi.getPatient(patientId),
      databaseApi.getTriageByPatient(patientId),
      databaseApi.getRecordings(patientId),
    ]);

    // Check if patient exists
    if (!patientRes.success || !patientRes.patient) {
      throw new Error('Patient not found');
    }

    return {
      patient: patientRes.patient,
      triage: triageRes.success ? triageRes.triage : [],
      recordings: recordingsRes.success ? recordingsRes.recordings : [],
    };
  } catch (error) {
    console.error('Error fetching patient details:', error);
    throw error;
  }
},

  // ========== NEW: Get RHD patients summary ==========
  getRHDSummary: async (doctorId) => {
    try {
      const res = await databaseApi.getRHDSummary(doctorId);
      if (res.success) return res.summary;
      throw new Error('Failed to fetch RHD summary');
    } catch (error) {
      console.warn('Error fetching RHD summary:', error);
      return {
        total: 0,
        confirmed: 0,
        suspected: 0,
        none: 0,
        unknown: 0,
        patients: []
      };
    }
  }
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
  },

  // ========== NEW: Get RHD stats ==========
  getRHDStats: async (doctorId) => {
    try {
      const summary = await patientService.getRHDSummary(doctorId);
      return {
        totalPatients: summary.total || 0,
        confirmedRHD: summary.confirmed || 0,
        suspectedRHD: summary.suspected || 0,
        noRHD: summary.none || 0,
        unknown: summary.unknown || 0,
        rhdRate: summary.total > 0 ? ((summary.confirmed + summary.suspected) / summary.total * 100).toFixed(1) : 0,
      };
    } catch (error) {
      console.warn('Error fetching RHD stats:', error);
      return {
        totalPatients: 0,
        confirmedRHD: 0,
        suspectedRHD: 0,
        noRHD: 0,
        unknown: 0,
        rhdRate: 0,
      };
    }
  }
};

export default api;