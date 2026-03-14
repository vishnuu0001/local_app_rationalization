import axios from 'axios';

import { API_BASE } from './api';
import { getAuthToken } from './authSession';

const authClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

authClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const loginWithPassword = (username, password) =>
  authClient.post('/auth/login', { username, password }).then((r) => r.data);

export const logoutSession = () => authClient.post('/auth/logout').then((r) => r.data);

export const fetchCurrentUser = () => authClient.get('/auth/me').then((r) => r.data);

export const fetchOauthProviders = () => authClient.get('/auth/oauth/providers').then((r) => r.data);

export const fetchApplications = () => authClient.get('/auth/apps').then((r) => r.data);

export const listUsers = () => authClient.get('/auth/users').then((r) => r.data);

export const createUser = (payload) => authClient.post('/auth/users', payload).then((r) => r.data);

export const updateUser = (userId, payload) => authClient.put(`/auth/users/${userId}`, payload).then((r) => r.data);

export const getGoogleAuthUrl = () => `${API_BASE}/auth/google/start`;

export const getGithubAuthUrl = () => `${API_BASE}/auth/github/start`;
