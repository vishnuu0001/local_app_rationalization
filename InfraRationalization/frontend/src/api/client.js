import axios from 'axios'

const AUTH_TOKEN_KEY = 'infra_portal_auth_token'
const API_BASE = import.meta.env.VITE_INFRA_API_URL || ''
const PORTAL_HOME_URL = import.meta.env.VITE_PORTAL_HOME_URL || 'http://localhost:3000/launch-modules'
const PORTAL_LOGIN_URL = import.meta.env.VITE_PORTAL_LOGIN_URL || 'http://localhost:3000/login'

export const getPortalLoginUrl = () => PORTAL_LOGIN_URL
export const getPortalHomeUrl = () => PORTAL_HOME_URL

export const getPortalToken = () => sessionStorage.getItem(AUTH_TOKEN_KEY)

export const setPortalToken = (token) => {
  if (!token) return
  sessionStorage.setItem(AUTH_TOKEN_KEY, token)
}

export const clearPortalToken = () => {
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
}

export const consumePortalTokenFromHash = () => {
  const hash = window.location.hash || ''
  if (!hash.startsWith('#')) return null
  const params = new URLSearchParams(hash.slice(1))
  const token = params.get('authToken') || params.get('token')
  if (!token) return null
  setPortalToken(token)
  window.history.replaceState(null, document.title, window.location.pathname + window.location.search)
  return token
}

export const logoutFromPortal = () => {
  clearPortalToken()
  window.location.href = PORTAL_HOME_URL
}

const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = getPortalToken()
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

export const validateSession = async () => {
  const { data } = await api.get('/api/auth/session')
  return data
}

// ── Persisted scan CRUD ──────────────────────────────────────────────────────
export const listScans = async () => {
  const { data } = await api.get('/api/scans')
  return data
}

export const getScan = async (scanId) => {
  const { data } = await api.get(`/api/scans/${scanId}`)
  return data
}

export const createScan = async (scanData) => {
  const { data } = await api.post('/api/scans', scanData)
  return data
}

export const deleteScan = async (scanId) => {
  const { data } = await api.delete(`/api/scans/${scanId}`)
  return data
}

export const getTemplateUrl = () => `${API_BASE}/api/template`

// ── Live scan jobs ────────────────────────────────────────────────────────────
export const startScan = async (scanConfig) => {
  const { data } = await api.post('/api/scans/start', scanConfig)
  return data   // { scan_id, report_name, status }
}

export const listScanJobs = async () => {
  const { data } = await api.get('/api/scans/jobs')
  return data   // { jobs: [...] }
}

export const getScanJob = async (scanId) => {
  const { data } = await api.get(`/api/scans/jobs/${scanId}`)
  return data
}

export const getScanReport = async (scanId) => {
  const { data } = await api.get(`/api/scans/jobs/${scanId}/report`)
  return data
}

export const getScanStreamUrl = (scanId) =>
  `${API_BASE}/api/scans/jobs/${scanId}/stream`
