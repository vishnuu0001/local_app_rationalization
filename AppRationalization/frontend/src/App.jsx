import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { AuthProvider, useAuth } from './context/AuthContext';
import { AdminRoute, AppAccessRoute, ProtectedRoute } from './components/auth/RouteGuards';
import ErrorBoundary from './components/ErrorBoundary';
import AdminUsersPage from './pages/AdminUsersPage';
import AppRationalizationWorkspace from './pages/AppRationalizationWorkspace';
import HomePage from './pages/HomePage';
import LaunchModulesPage from './pages/LaunchModulesPage';
import LoginPage from './pages/LoginPage';

const APP_RATIONALIZATION = 'APP_RATIONALIZATION';

const RootRedirect = () => {
  const { isAuthenticated } = useAuth();
  return <Navigate to={isAuthenticated ? '/home' : '/login'} replace />;
};

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/home"
              element={
                <ProtectedRoute>
                  <HomePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/launch-modules"
              element={
                <ProtectedRoute>
                  <LaunchModulesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminUsersPage />
                </AdminRoute>
              }
            />
            <Route
              path="/app-rationalization/*"
              element={
                <AppAccessRoute appKey={APP_RATIONALIZATION}>
                  <AppRationalizationWorkspace />
                </AppAccessRoute>
              }
            />
            <Route path="*" element={<RootRedirect />} />
          </Routes>

          <ToastContainer
            position="bottom-right"
            autoClose={5000}
            hideProgressBar={false}
            newestOnTop={false}
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="light"
          />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
