import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { fetchCurrentUser, loginWithPassword, logoutSession } from '../services/authApi';
import {
  clearAuthSession,
  getAuthSession,
  hasAppPermission,
  setAuthSession,
} from '../services/authSession';

const AuthContext = createContext(null);

const parseOauthHash = () => {
  const hash = window.location.hash || '';
  if (!hash.startsWith('#')) {
    return {};
  }

  const params = new URLSearchParams(hash.slice(1));
  return {
    token: params.get('token') || null,
    error: params.get('error') || null,
  };
};

export const AuthProvider = ({ children }) => {
  const [session, setSessionState] = useState(() => getAuthSession());
  const [initializing, setInitializing] = useState(true);
  const [oauthError, setOauthError] = useState(null);

  const refreshFromToken = useCallback(async (token) => {
    const current = getAuthSession();
    setAuthSession({ token, user: current?.user || { username: 'Loading...' } });

    const me = await fetchCurrentUser();
    const nextSession = {
      token,
      user: me.user,
      expires_at: me.expires_at,
    };
    setAuthSession(nextSession);
    setSessionState(nextSession);
    return nextSession;
  }, []);

  const bootstrap = useCallback(async () => {
    const { token: oauthToken, error } = parseOauthHash();
    if (window.location.hash) {
      window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
    }
    if (error) {
      setOauthError(error);
    }

    const existing = getAuthSession();
    const token = oauthToken || existing?.token;

    if (!token) {
      setSessionState(null);
      setInitializing(false);
      return;
    }

    try {
      await refreshFromToken(token);
    } catch {
      clearAuthSession();
      setSessionState(null);
    } finally {
      setInitializing(false);
    }
  }, [refreshFromToken]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (username, password) => {
    const payload = await loginWithPassword(username, password);
    setAuthSession(payload);
    setSessionState(payload);
    setOauthError(null);
    return payload;
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getAuthSession()?.token) {
        await logoutSession();
      }
    } catch {
      // Local session cleanup is still executed below.
    }
    clearAuthSession();
    setSessionState(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getAuthSession()?.token;
    if (!token) {
      return null;
    }

    const me = await fetchCurrentUser();
    const nextSession = {
      token,
      user: me.user,
      expires_at: me.expires_at,
    };
    setAuthSession(nextSession);
    setSessionState(nextSession);
    return me.user;
  }, []);

  const hasAccess = useCallback(
    (appKey) => {
      if (!appKey) {
        return Boolean(session?.user);
      }
      return hasAppPermission(appKey);
    },
    [session?.user]
  );

  const value = useMemo(
    () => ({
      initializing,
      session,
      user: session?.user || null,
      token: session?.token || null,
      oauthError,
      isAuthenticated: Boolean(session?.token && session?.user),
      login,
      logout,
      refreshUser,
      hasAccess,
    }),
    [initializing, session, oauthError, login, logout, refreshUser, hasAccess]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
};
