import axios from 'axios';

const CONFIGURED_API_BASE = process.env.REACT_APP_API_URL || (
  window.location.hostname === 'localhost'
    ? 'http://localhost:5000/api'
    : '/api'
);

export const API_BASE = CONFIGURED_API_BASE.replace(/\/+$/, '');

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Upload endpoints
export const uploadInfrastructure = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post('/upload/infrastructure', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const uploadCodeAnalysis = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post('/upload/code-analysis', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const extractCastAnalysis = (fileId) =>
  apiClient.post(`/upload/extract-cast-analysis/${fileId}`);

export const uploadIndustryTemplates = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post('/upload/industry-templates', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const getUploadedFiles = () => apiClient.get('/upload/files');
export const deleteFile = (fileId) => apiClient.delete(`/upload/file/${fileId}`);

// Industry Templates endpoints
export const getIndustryTemplates = () => apiClient.get('/upload/industry-templates/files');
export const getIndustryData = (fileId, page = 1, perPage = 20) =>
  apiClient.get(`/upload/industry-templates/${fileId}/data`, {
    params: { page, per_page: perPage }
  });
export const deleteIndustryTemplate = (fileId) => apiClient.delete(`/upload/industry-templates/${fileId}`);
export const previewIndustryTemplate = (fileId) => apiClient.get(`/upload/industry-templates/preview/${fileId}`);

// PDF Extraction endpoints
export const extractPDFData = (fileId, page = 1, perPage = 20) => 
  apiClient.post(`/upload/extract-pdf/${fileId}`, null, {
    params: { page, per_page: perPage }
  });

export const getDiscoveredApplications = (fileId, page = 1, perPage = 20) =>
  apiClient.get(`/upload/infrastructure/${fileId}/discovered-apps`, {
    params: { page, per_page: perPage }
  });

export const getPDFReports = (type = null) => {
  const params = type ? { type } : {};
  return apiClient.get('/upload/reports/pdf', { params });
};

export const getPDFReport = (reportId) =>
  apiClient.get(`/upload/reports/pdf/${reportId}`);

export const searchPDFReports = (query, type = null) => {
  const params = { q: query };
  if (type) params.type = type;
  return apiClient.get('/upload/reports/pdf/search', { params });
};

// Correlation endpoints
export const startCorrelation = () =>
  apiClient.post('/correlation/start');

export const getCorrelationData = () =>
  apiClient.get('/correlation/latest');

export const getCorrelationDashboards = () =>
  apiClient.get('/correlation/dashboards');

export const getCorrelationMasterMatrix = (confidenceLevel = null, limit = 1000) => {
  const params = { limit };
  if (confidenceLevel) params.confidence_level = confidenceLevel;
  return apiClient.get('/correlation/master-matrix', { params });
};

export const getCorrelationStatistics = () =>
  apiClient.get('/correlation/statistics');

// Analysis endpoints
export const correlateInfraAndCode = (infrastructureId, repositoryId) =>
  apiClient.post('/analysis/correlate', {
    infrastructure_id: infrastructureId,
    repository_id: repositoryId,
  });

export const getInfrastructureSummary = (infraId) =>
  apiClient.get(`/analysis/infrastructure/${infraId}/summary`);

export const getCodeSummary = (repoId) =>
  apiClient.get(`/analysis/code/${repoId}/summary`);

export const getAllApplications = () => apiClient.get('/analysis/applications');
export const getAllInfrastructure = () => apiClient.get('/analysis/infrastructure');
export const getAllRepositories = () => apiClient.get('/analysis/code-repositories');
export const getAnalysisHistory = () => apiClient.get('/analysis/analysis-history');

// Capability endpoints
export const getCapabilities = () => apiClient.get('/capabilities');
export const getCapabilityById = (id) => apiClient.get(`/capability/${id}`);
export const getCapabilityByName = (name) => apiClient.get(`/capability/by-name/${name}`);
export const createCapabilityMapping = (data) =>
  apiClient.post('/capability-map', data);

// Rationalization endpoints
export const getRationalizationScenarios = () =>
  apiClient.get('/rationalization-scenarios');

export const getRationalizationScenario = (id) =>
  apiClient.get(`/rationalization-scenario/${id}`);

export const getScenariosByCapability = (capability) =>
  apiClient.get(`/rationalization-scenarios/by-capability/${capability}`);

export const createRationalizationScenario = (data) =>
  apiClient.post('/rationalization-scenario', data);

// Dashboard endpoints
export const getDashboardData = () => apiClient.get('/dashboard');
export const getTraceabilityMatrix = () => apiClient.get('/correlation/traceability/matrix');
export const getInitializationStatus = () => apiClient.get('/initialization-status');
export const initializeTestData = () => apiClient.post('/initialize-test-data');

// Initialize defaults
export const initializeDefaults = () =>
  apiClient.post('/initialize-defaults');

export default apiClient;
