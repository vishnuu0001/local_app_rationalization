const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Helper to make API calls with proper error handling
const makeRequest = async (method, endpoint, data = null, options = {}) => {
  try {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...options.headers,
      },
      withCredentials: false,
    };

    if (data) {
      if (data instanceof FormData) {
        delete config.headers['Content-Type'];
        config.data = data;
      } else {
        config.data = JSON.stringify(data);
      }
    }

    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return {
      status: response.status,
      data: await response.json(),
    };
  } catch (error) {
    console.error(`API Error [${method} ${endpoint}]:`, error);
    throw error;
  }
};

// Upload endpoints
export const uploadInfrastructure = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return makeRequest('POST', '/upload/infrastructure', formData);
};

export const uploadCodeAnalysis = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return makeRequest('POST', '/upload/code-analysis', formData);
};

// File management
export const getUploadedFiles = () => makeRequest('GET', '/upload/files');

export const deleteFile = (fileId) =>
  makeRequest('DELETE', `/upload/file/${fileId}`);

export const extractPDFData = (fileId) =>
  makeRequest('POST', `/upload/extract-pdf/${fileId}`);

// Correlation analysis
export const startCorrelation = () =>
  makeRequest('POST', '/correlation/start');

export const getCorrelationData = () =>
  makeRequest('GET', '/correlation/latest');

export const getCorrelationDashboards = () =>
  makeRequest('GET', '/correlation/dashboards');

export const getCorrelationMasterMatrix = () =>
  makeRequest('GET', '/correlation/master-matrix');

export const getCorrelationStatistics = () =>
  makeRequest('GET', '/correlation/statistics');

// Health check
export const healthCheck = () => makeRequest('GET', '/health');

export default {
  uploadInfrastructure,
  uploadCodeAnalysis,
  getUploadedFiles,
  deleteFile,
  extractPDFData,
  startCorrelation,
  getCorrelationData,
  getCorrelationDashboards,
  getCorrelationMasterMatrix,
  getCorrelationStatistics,
  healthCheck,
};
