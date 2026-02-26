import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import FileUpload from './components/FileUpload';
import CASTAnalysis from './components/CASTAnalysis';
import Analysis from './components/Analysis';
import CorrelationDashboard from './components/CorrelationDashboard';
import BusinessCapabilityMapping from './components/business-capability/BusinessCapabilityMapping';
import StandardizationERP from './components/business-capability/StandardizationERP';
import FinalTraceabilityMatrix from './components/business-capability/FinalTraceabilityMatrix';
import IndustryTemplates from './components/IndustryTemplates';

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div className="h-screen">
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<FileUpload />} />
              <Route path="/industry-templates" element={<IndustryTemplates />} />
              <Route path="/cast-analysis" element={<CASTAnalysis />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/correlation" element={<CorrelationDashboard />} />
              <Route path="/capability/inventory" element={<BusinessCapabilityMapping />} />
              <Route path="/capability/standardization" element={<StandardizationERP />} />
              <Route path="/capability/traceability" element={<FinalTraceabilityMatrix />} />
            </Routes>
          </Layout>
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
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
