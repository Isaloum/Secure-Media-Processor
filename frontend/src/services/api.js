import axios from 'axios';
import config from '../utils/config';

// Create axios instance
const api = axios.create({
  baseURL: config.apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  getMe: () => api.get('/api/auth/me'),
};

// Users API
export const usersApi = {
  getProfile: () => api.get('/api/users/me'),
  updateProfile: (data) => api.put('/api/users/me', data),
  getUsage: () => api.get('/api/users/me/usage'),
};

// Files API
export const filesApi = {
  list: (page = 1, pageSize = 20) =>
    api.get(`/api/files?page=${page}&page_size=${pageSize}`),

  get: (fileId) => api.get(`/api/files/${fileId}`),

  getUploadUrl: (fileInfo) => api.post('/api/files/upload-url', fileInfo),

  completeUpload: (fileId) => api.post(`/api/files/${fileId}/complete`),

  getDownloadUrl: (fileId) => api.get(`/api/files/${fileId}/download-url`),

  delete: (fileId) => api.delete(`/api/files/${fileId}`),

  // Upload file using presigned URL
  uploadToS3: async (presignedUrl, file, onProgress) => {
    return axios.put(presignedUrl, file, {
      headers: {
        'Content-Type': file.type,
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
  },
};

// Licenses API
export const licensesApi = {
  activate: (licenseKey) => api.post('/api/licenses/activate', { license_key: licenseKey }),
  validate: (licenseKey) => api.post('/api/licenses/validate', { license_key: licenseKey }),
  getCurrent: () => api.get('/api/licenses/current'),
  getTiers: () => api.get('/api/licenses/tiers'),
  deactivate: () => api.delete('/api/licenses/deactivate'),
};

export default api;
