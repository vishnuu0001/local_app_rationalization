import axios from 'axios';
import { getAuthToken } from './authSession';

/**
 * API base URL resolution:
 *  - Local dev (npm start):       .env.development.local → http://localhost:5000/api
 *  - Production build (npm build): .env.production       → https://api.stratapp.org/api
 *  - Fallback when env var absent: same-origin /api
 */
const resolveApiBase = () => {
  const configured = process.env.REACT_APP_API_URL;
  if (configured) {
    return configured.replace(/\/+$/, '');
  }
  // No env var — infer from browser origin
  return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : '/api';
};

export const API_BASE = resolveApiBase();

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
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

export const getLlmAnalysis = () =>
  apiClient.get('/correlation/llm-analysis');

export const rerunLlmAnalysis = () =>
  apiClient.post('/correlation/llm-analysis/rerun', null, { timeout: 210_000 }); // 210s > 200s server limit

export const getCorrelationDashboards = () =>
  apiClient.get('/correlation/dashboards');

export const getCorrelationMasterMatrix = (confidenceLevel = null, limit = 1000) => {
  const params = { limit };
  if (confidenceLevel) params.confidence_level = confidenceLevel;
  return apiClient.get('/correlation/master-matrix', { params });
};

export const getCorrelationStatistics = () =>
  apiClient.get('/correlation/statistics');

// Consolidated DB + Ollama endpoints
export const getConsolidatedApps = () =>
  apiClient.get('/correlation/consolidated');

export const getConsolidatedStats = () =>
  apiClient.get('/correlation/consolidated/stats');

export const getOllamaStatus = () =>
  apiClient.get('/correlation/ollama/status');

// Workspace pipeline endpoints — file copy, LLM fill, column traceability
export const getWorkspaceRuns = (limit = 20) =>
  apiClient.get('/correlation/workspace/runs', { params: { limit } });

export const getWorkspaceColumnUpdates = (runId = null, source = null, limit = 1000) => {
  const params = { limit };
  if (runId) params.run_id = runId;
  if (source) params.source = source;
  return apiClient.get('/correlation/workspace/column-updates', { params });
};

// Workspace row data (includes updated_rows per-row AI summary)
export const getWorkspaceCastRows = (runId = null, limit = 500) => {
  const params = { limit };
  if (runId) params.run_id = runId;
  return apiClient.get('/correlation/workspace/cast', { params });
};

export const getWorkspaceCorentRows = (runId = null, limit = 500) => {
  const params = { limit };
  if (runId) params.run_id = runId;
  return apiClient.get('/correlation/workspace/corent', { params });
};

export const getWorkspaceBizRows = (runId = null, limit = 500) => {
  const params = { limit };
  if (runId) params.run_id = runId;
  return apiClient.get('/correlation/workspace/business', { params });
};

// Drill-down: apps by cloud-suitability group (L2) and single-app detail (L3)
export const getAppsByCloudGroup = () =>
  apiClient.get('/correlation/apps/cloud-groups');

export const getAppDetail = (appId) =>
  apiClient.get(`/correlation/apps/${encodeURIComponent(appId)}/detail`);

export const getWorkspaceCorrelations = (runId = null, matchType = null, limit = 500) => {
  const params = { limit };
  if (runId) params.run_id = runId;
  if (matchType) params.match_type = matchType;
  return apiClient.get('/correlation/workspace/correlations', { params });
};

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

// Golden Data endpoints
export const generateGoldenData = () => apiClient.post('/golden-data/generate');
export const getGoldenDataPreview = () => apiClient.get('/golden-data/preview');
export const getGoldenDataDownloadUrl = () => `${API_BASE}/golden-data/download`;
export const clearGoldenData = () => apiClient.post('/golden-data/clear');
export const getGoldenDataRecords = (page = 1, perPage = 200, search = '') =>
  apiClient.get('/golden-data/records', { params: { page, per_page: perPage, search } });
export const updateGoldenDataRecord = (appId, data) =>
  apiClient.put(`/golden-data/records/${encodeURIComponent(appId)}`, data);
export const regenerateGoldenExcel = () => apiClient.post('/golden-data/regenerate-excel');

export default apiClient;
