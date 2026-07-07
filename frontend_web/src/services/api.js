// frontend_web/src/services/api.js
import axios from 'axios';

// =====================
// OFFLINE QUEUE MANAGER
// =====================
class OfflineQueue {
  constructor() {
    this.queueKey = 'offline_request_queue';
    this.isProcessing = false;
    this.isOnline = navigator.onLine;
    
    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processQueue();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  // Add request to queue
  async addRequest(config) {
    const queue = this.getQueue();
    queue.push({
      ...config,
      timestamp: new Date().toISOString(),
      id: Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    });
    this.saveQueue(queue);
    
    // If online, process immediately
    if (this.isOnline) {
      this.processQueue();
    }
    
    return Promise.resolve({
      queued: true,
      message: 'Request queued for offline sync'
    });
  }

  // Get queue from localStorage
  getQueue() {
    try {
      return JSON.parse(localStorage.getItem(this.queueKey)) || [];
    } catch {
      return [];
    }
  }

  // Save queue to localStorage
  saveQueue(queue) {
    try {
      localStorage.setItem(this.queueKey, JSON.stringify(queue));
    } catch (e) {
      console.error('Failed to save offline queue:', e);
    }
  }

  // Process all queued requests
  async processQueue() {
    if (this.isProcessing || !this.isOnline) return;
    
    const queue = this.getQueue();
    if (queue.length === 0) return;
    
    this.isProcessing = true;
    console.log(`🔄 Processing ${queue.length} offline requests...`);
    
    const failedRequests = [];
    
    for (const request of queue) {
      try {
        const response = await api.request({
          method: request.method,
          url: request.url,
          data: request.data,
          headers: request.headers,
          params: request.params
        });
        
        console.log(`✅ Offline request completed: ${request.method} ${request.url}`);
        
        // Dispatch event for successful sync
        window.dispatchEvent(new CustomEvent('offline_sync_success', {
          detail: { request, response: response.data }
        }));
        
      } catch (error) {
        console.error(`❌ Failed to sync request: ${request.method} ${request.url}`, error);
        failedRequests.push(request);
      }
    }
    
    // Update queue with failed requests
    this.saveQueue(failedRequests);
    this.isProcessing = false;
    
    if (failedRequests.length === 0) {
      console.log('✅ All offline requests synced successfully!');
      window.dispatchEvent(new CustomEvent('offline_sync_complete'));
    } else {
      console.warn(`⚠️ ${failedRequests.length} requests failed to sync`);
    }
  }

  // Clear all queued requests
  clearQueue() {
    localStorage.removeItem(this.queueKey);
  }

  // Get queue status
  getStatus() {
    const queue = this.getQueue();
    return {
      isOnline: this.isOnline,
      isProcessing: this.isProcessing,
      queueLength: queue.length,
      pendingRequests: queue.map(req => ({
        id: req.id,
        method: req.method,
        url: req.url,
        timestamp: req.timestamp
      }))
    };
  }
}

// Initialize offline queue
const offlineQueue = new OfflineQueue();

// =====================
// AXIOS INSTANCE
// =====================
const baseUrl = import.meta.env.VITE_API_URL || "https://capstone-be-yxzd.onrender.com";

const api = axios.create({
  baseURL: baseUrl.endsWith('/api/v1') ? baseUrl : `${baseUrl}/api/v1`,
  withCredentials: true,
  timeout: 30000, // 30 second timeout
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
// RESPONSE HANDLER WITH OFFLINE SUPPORT
// =====================
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      return Promise.reject(error);
    }
    
    // Handle network errors (offline)
    if (!error.response && error.message === 'Network Error') {
      console.warn('🌐 Network error - adding to offline queue');
      
      // Add failed request to offline queue
      if (error.config) {
        await offlineQueue.addRequest({
          method: error.config.method?.toUpperCase() || 'GET',
          url: error.config.url,
          data: error.config.data,
          headers: error.config.headers,
          params: error.config.params
        });
        
        // Return a special response for queued requests
        return Promise.resolve({
          data: {
            queued: true,
            offline: true,
            message: 'Request queued for offline processing',
            queueId: Date.now()
          },
          status: 202,
          statusText: 'Accepted - Queued'
        });
      }
    }
    
    return Promise.reject(error);
  }
);

// =====================
// OFFLINE QUEUE EXPOSURE
// =====================
export const offlineService = {
  getStatus: () => offlineQueue.getStatus(),
  processQueue: () => offlineQueue.processQueue(),
  clearQueue: () => offlineQueue.clearQueue(),
  getQueue: () => offlineQueue.getQueue(),
  isOnline: () => navigator.onLine
};

// =====================
// SCREENING SERVICES
// =====================
export const screeningService = {
  healthCheck: async () => {
    const res = await api.get('/screening/health');
    return res.data;
  },

  predict: async (file, patientId, doctorId, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    if (patientId) formData.append('patient_id', patientId);
    if (doctorId) formData.append('doctor_id', doctorId);
    
    // Add severity and auscultation data if provided
    if (options.auscultation_point) {
      formData.append('auscultation_point', options.auscultation_point);
    }
    if (options.auscultation_label) {
      formData.append('auscultation_label', options.auscultation_label);
    }
    if (options.severity_grade !== undefined) {
      formData.append('severity_grade', options.severity_grade);
    }
    if (options.severity_label) {
      formData.append('severity_label', options.severity_label);
    }

    try {
      const res = await api.post('/screening/predict', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        // Add timeout for large files
        timeout: 60000, // 60 seconds
      });
      return res.data;
    } catch (error) {
      // If offline, queue the request
      if (!navigator.onLine || error.message === 'Network Error') {
        console.warn('📱 Offline - queuing prediction request');
        await offlineQueue.addRequest({
          method: 'POST',
          url: '/screening/predict',
          data: formData,
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        return {
          queued: true,
          offline: true,
          message: 'Prediction queued for offline processing'
        };
      }
      throw error;
    }
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
  
  saveRecording: async (data) => {
    try {
      const res = await api.post('/screening/save-recording', data);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'POST',
          url: '/screening/save-recording',
          data: data
        });
        return {
          queued: true,
          offline: true,
          message: 'Recording save queued for offline processing'
        };
      }
      throw error;
    }
  },
  
  getPatientRecordings: async (patientId) => {
    const res = await api.get(`/screening/recordings/${patientId}`);
    return res.data;
  }
};

// =====================
// DATABASE API WITH OFFLINE SUPPORT
// =====================
export const databaseApi = {
  // ===== PATIENTS =====
  getPatients: async (doctorId) => {
    const res = await api.get(`/database/patients?doctor_id=${doctorId}`);
    return res.data;
  },

  createPatient: async (data) => {
    try {
      const res = await api.post('/database/patients', data);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'POST',
          url: '/database/patients',
          data: data
        });
        return {
          queued: true,
          offline: true,
          message: 'Patient creation queued for offline processing'
        };
      }
      throw error;
    }
  },

  getPatient: async (patientId) => {
    const res = await api.get(`/database/patients/${patientId}`);
    return res.data;
  },

  updatePatient: async (patientId, data) => {
    try {
      const res = await api.put(`/database/patients/${patientId}`, data);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'PUT',
          url: `/database/patients/${patientId}`,
          data: data
        });
        return {
          queued: true,
          offline: true,
          message: 'Patient update queued for offline processing'
        };
      }
      throw error;
    }
  },

  deletePatient: async (patientId) => {
    try {
      const res = await api.delete(`/database/patients/${patientId}`);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'DELETE',
          url: `/database/patients/${patientId}`
        });
        return {
          queued: true,
          offline: true,
          message: 'Patient deletion queued for offline processing'
        };
      }
      throw error;
    }
  },

  updatePatientRHDStatus: async (patientId, data) => {
    try {
      const res = await api.put(`/database/patients/${patientId}/rhd-status`, data);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'PUT',
          url: `/database/patients/${patientId}/rhd-status`,
          data: data
        });
        return {
          queued: true,
          offline: true,
          message: 'RHD status update queued for offline processing'
        };
      }
      throw error;
    }
  },

  getPatientsByRHDStatus: async (doctorId, rhdStatus) => {
    const res = await api.get(`/database/patients/rhd-status/${rhdStatus}?doctor_id=${doctorId}`);
    return res.data;
  },

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
    try {
      const res = await api.post('/database/triage', data);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'POST',
          url: '/database/triage',
          data: data
        });
        return {
          queued: true,
          offline: true,
          message: 'Triage creation queued for offline processing'
        };
      }
      throw error;
    }
  },

  calculateTriage: async (data) => {
    const res = await api.post('/database/triage/calculate', data);
    return res.data;
  },

  // ===== RECORDINGS WITH SEVERITY =====
  getRecordings: async (patientId) => {
    try {
      const res = await api.get(`/database/recordings/patient/${patientId}`);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        // Return cached data from localStorage if available
        const cached = localStorage.getItem(`recordings_${patientId}`);
        if (cached) {
          return JSON.parse(cached);
        }
        return {
          success: false,
          offline: true,
          recordings: [],
          message: 'No cached recordings available'
        };
      }
      throw error;
    }
  },

  saveRecording: async (data) => {
    try {
      // Include severity grade and auscultation data
      const payload = {
        ...data,
        severity_grade: data.severity_grade || 0,
        severity_label: data.severity_label || 'Unknown',
        auscultation_point: data.auscultation_point || null,
        auscultation_label: data.auscultation_label || null
      };
      
      const res = await api.post('/database/recordings', payload);
      
      // Cache the recording locally
      if (res.data.success) {
        const patientId = data.patient_id;
        const cachedKey = `recordings_${patientId}`;
        const cached = localStorage.getItem(cachedKey);
        const recordings = cached ? JSON.parse(cached) : [];
        recordings.unshift({
          ...payload,
          id: res.data.recording_id,
          created_at: new Date().toISOString()
        });
        localStorage.setItem(cachedKey, JSON.stringify(recordings));
      }
      
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        // Cache offline recording
        const patientId = data.patient_id;
        const cachedKey = `recordings_${patientId}`;
        const cached = localStorage.getItem(cachedKey);
        const recordings = cached ? JSON.parse(cached) : [];
        recordings.unshift({
          ...data,
          id: 'offline_' + Date.now(),
          created_at: new Date().toISOString(),
          offline: true
        });
        localStorage.setItem(cachedKey, JSON.stringify(recordings));
        
        await offlineQueue.addRequest({
          method: 'POST',
          url: '/database/recordings',
          data: data
        });
        
        return {
          queued: true,
          offline: true,
          recording_id: 'offline_' + Date.now(),
          message: 'Recording saved offline and queued for sync'
        };
      }
      throw error;
    }
  },

  // ===== DEVICES =====
  getDevices: async (doctorId) => {
    const res = await api.get(`/database/devices/${doctorId}`);
    return res.data;
  },

  registerDevice: async (data) => {
    try {
      const res = await api.post('/database/devices/register', data);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'POST',
          url: '/database/devices/register',
          data: data
        });
        return {
          queued: true,
          offline: true,
          message: 'Device registration queued for offline processing'
        };
      }
      throw error;
    }
  },

  updateDeviceStatus: async (deviceId, status) => {
    try {
      const res = await api.put(`/database/devices/${deviceId}/status`, { status });
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        await offlineQueue.addRequest({
          method: 'PUT',
          url: `/database/devices/${deviceId}/status`,
          data: { status }
        });
        return {
          queued: true,
          offline: true,
          message: 'Device status update queued for offline processing'
        };
      }
      throw error;
    }
  },

  // ===== SEVERITY METHODS =====
  getSeverityHistory: async (patientId, limit = 20) => {
    try {
      const res = await api.get(`/database/severity/history/${patientId}?limit=${limit}`);
      return res.data;
    } catch (error) {
      if (!navigator.onLine || error.message === 'Network Error') {
        const cached = localStorage.getItem(`severity_history_${patientId}`);
        if (cached) {
          return JSON.parse(cached);
        }
        return {
          success: false,
          offline: true,
          history: []
        };
      }
      throw error;
    }
  },

  getSeverityTrend: async (patientId) => {
    const res = await api.get(`/database/severity/trend/${patientId}`);
    return res.data;
  }
};

// =====================
// PATIENT SERVICE WITH CACHING
// =====================
export const patientService = {
  getPatients: async (doctorId) => {
    try {
      const res = await databaseApi.getPatients(doctorId);
      if (res.success) {
        // Cache patients list
        localStorage.setItem(`patients_${doctorId}`, JSON.stringify(res.patients));
        return res.patients;
      }
      throw new Error('Failed to fetch patients');
    } catch (error) {
      console.warn('Using cached patient data:', error);
      const cached = localStorage.getItem(`patients_${doctorId}`);
      if (cached) {
        return JSON.parse(cached);
      }
      return [];
    }
  },

  getPatientDetails: async (patientId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      // Fetch the patient first — it is the critical resource. Triage and
      // recordings are fetched independently (allSettled) so that a transient
      // failure in either does NOT wipe the patient from the profile view.
      const patientRes = await databaseApi.getPatient(patientId);
      if (!patientRes.success || !patientRes.patient) {
        throw new Error('Patient not found');
      }

      const [triageSettled, recordingsSettled] = await Promise.allSettled([
        databaseApi.getTriageByPatient(patientId),
        databaseApi.getRecordings(patientId),
      ]);
      const triage = (triageSettled.status === 'fulfilled' && triageSettled.value?.success)
        ? triageSettled.value.triage : [];
      const recordings = (recordingsSettled.status === 'fulfilled' && recordingsSettled.value?.success)
        ? recordingsSettled.value.recordings : [];

      // Cache patient details
      const cacheKey = `patient_details_${patientId}`;
      localStorage.setItem(cacheKey, JSON.stringify({
        patient: patientRes.patient,
        triage,
        recordings,
        cached_at: new Date().toISOString()
      }));

      return { patient: patientRes.patient, triage, recordings };
    } catch (error) {
      console.error('Error fetching patient details:', error);
      
      // Return cached data if available
      const cacheKey = `patient_details_${patientId}`;
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        console.log('📱 Using cached patient data');
        const parsed = JSON.parse(cached);
        return {
          patient: parsed.patient,
          triage: parsed.triage || [],
          recordings: parsed.recordings || [],
          cached: true,
          cached_at: parsed.cached_at
        };
      }
      
      throw error;
    }
  },

  getRHDSummary: async (doctorId) => {
    try {
      const res = await databaseApi.getRHDSummary(doctorId);
      if (res.success) {
        localStorage.setItem(`rhd_summary_${doctorId}`, JSON.stringify(res.summary));
        return res.summary;
      }
      throw new Error('Failed to fetch RHD summary');
    } catch (error) {
      console.warn('Error fetching RHD summary:', error);
      const cached = localStorage.getItem(`rhd_summary_${doctorId}`);
      if (cached) {
        return JSON.parse(cached);
      }
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

// =====================
// REPORT SERVICE
// =====================
export const reportService = {
  // Generate a PDF referral report for a patient.
  generate: async (payload) => {
    const res = await api.post('/reports/generate', payload);
    return res.data;
  },
  // Absolute download URL on the backend (the file endpoint returns a PDF).
  downloadUrl: (filename) => `${api.defaults.baseURL}/reports/download/${filename}`,
};

// =====================
// PROGNOSIS SERVICE
// =====================
export const prognosisService = {
  getRisk: async (patientId) => {
    const res = await api.get(`/prognosis/risk/${patientId}`);
    return res.data;
  },
};

// Export offline status helper
export const isOffline = () => !navigator.onLine;
export const isOnline = () => navigator.onLine;

export default api;