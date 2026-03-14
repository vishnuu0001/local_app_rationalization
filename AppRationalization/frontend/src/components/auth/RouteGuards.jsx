import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../../context/AuthContext';

const LoadingScreen = () => (
  <div className="min-h-screen flex items-center justify-center bg-slate-100">
    <div className="bg-white shadow-lg rounded-xl px-8 py-6 text-slate-700 font-medium">
      Validating session...
    </div>
  </div>
);

export const ProtectedRoute = ({ children }) => {
  const { initializing, isAuthenticated } = useAuth();
  const location = useLocation();

  if (initializing) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
};

export const AppAccessRoute = ({ appKey, children }) => {
  const { initializing, isAuthenticated, hasAccess } = useAuth();

  if (initializing) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (appKey && !hasAccess(appKey)) {
    return <Navigate to="/home" replace />;
  }

  return children;
};

export const AdminRoute = ({ children }) => {
  const { initializing, isAuthenticated, user } = useAuth();

  if (initializing) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== 'admin') {
    return <Navigate to="/home" replace />;
  }

  return children;
};
