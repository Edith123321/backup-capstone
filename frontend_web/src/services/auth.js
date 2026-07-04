// frontend_web/src/services/auth.js
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL ||'https://capstone-be-yxzd.onrender.com/api/v1';

// Axios instance with auth header
const authApi = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});

// Add token to requests
authApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle token refresh on 401
authApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Try to refresh token
        const response = await axios.post(`${API_URL}/auth/refresh`, {}, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.data.token) {
          localStorage.setItem('token', response.data.token);
          originalRequest.headers.Authorization = `Bearer ${response.data.token}`;
          return authApi(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed - logout
        localStorage.removeItem('token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const authService = {
  // Get Google login URL
  getGoogleLoginUrl: async () => {
    const response = await authApi.get('/auth/google/login');
    return response.data;
  },

  // Verify token
  verifyToken: async () => {
    const response = await authApi.get('/auth/verify');
    return response.data;
  },

  // Refresh token
  refreshToken: async () => {
    const response = await authApi.post('/auth/refresh');
    return response.data;
  },

  // Logout
  logout: async () => {
    const response = await authApi.post('/auth/logout');
    return response.data;
  },

  // Get current user
  getCurrentUser: async () => {
    const response = await authApi.get('/auth/user');
    return response.data;
  }
};

export default authApi;