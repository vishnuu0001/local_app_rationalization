const STORAGE_KEY = 'portal_auth_session';

export const getAuthSession = () => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw);
    if (!parsed?.token || !parsed?.user) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
};

export const setAuthSession = (sessionPayload) => {
  if (!sessionPayload?.token || !sessionPayload?.user) {
    return;
  }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(sessionPayload));
};

export const clearAuthSession = () => {
  sessionStorage.removeItem(STORAGE_KEY);
};

export const getAuthToken = () => {
  const session = getAuthSession();
  return session?.token || null;
};

export const getAuthUser = () => {
  const session = getAuthSession();
  return session?.user || null;
};

export const hasAppPermission = (appKey) => {
  const user = getAuthUser();
  if (!user) {
    return false;
  }
  if (user.role === 'admin') {
    return true;
  }
  const apps = Array.isArray(user.apps) ? user.apps : [];
  return apps.includes(appKey);
};
