import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Layout = ({ children }) => {
  const [expandedSections, setExpandedSections] = useState({
    baseline: false,
    cast: false,
    correlation: false,
    capability: false,
    industry: false,
  });
  const location = useLocation();

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const isActive = (path) => location.pathname === path;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-gradient-to-b from-blue-900 to-blue-800 text-white flex flex-col overflow-hidden">
        {/* Header Section */}
        <div className="bg-blue-950 px-6 py-8 border-b border-blue-700">
          <h1 className="text-2xl font-bold text-white">Application Assessment</h1>
          <p className="text-blue-200 text-sm mt-2">Infrastructure Discovery</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-6">
          {/* Home / Dashboard */}
          <Link
            to="/"
            className={`flex items-center gap-3 px-6 py-3 transition-colors ${
              isActive('/') ? 'bg-blue-700 border-l-4 border-white' : 'hover:bg-blue-700'
            }`}
          >
            <span className="text-xl">🏠</span>
            <span className="font-medium">Home / Dashboard</span>
          </Link>

          {/* Infra Scan - Corent Section */}
          <div className="mt-6">
            <button
              onClick={() => toggleSection('baseline')}
              className="w-full flex items-center gap-3 px-6 py-3 hover:bg-blue-700 transition-colors text-left"
            >
              <span className="text-xl">📊</span>
              <span className="font-semibold flex-1">
                Infra Scan - Corent
              </span>
              <span className={`text-lg transition-transform ${expandedSections.baseline ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {expandedSections.baseline && (
              <Link
                to="/upload"
                className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                  isActive('/upload')
                    ? 'bg-blue-700 border-white text-white'
                    : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                }`}
              >
                <span className="text-lg">👥</span>
                <span>Corent Analysis</span>
              </Link>
            )}
          </div>

          {/* Software Intelligence - CAST Section */}
          <div className="mt-2">
            <button
              onClick={() => toggleSection('cast')}
              className="w-full flex items-center gap-3 px-6 py-3 hover:bg-blue-700 transition-colors text-left"
            >
              <span className="text-xl">💻</span>
              <span className="font-semibold flex-1">Software Intelligence - CAST</span>
              <span className={`text-lg transition-transform ${expandedSections.cast ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {expandedSections.cast && (
              <Link
                to="/cast-analysis"
                className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                  isActive('/cast-analysis')
                    ? 'bg-blue-700 border-white text-white'
                    : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                }`}
              >
                <span className="text-lg">📁</span>
                <span>CAST Analysis</span>
              </Link>
            )}
          </div>

          {/* Industry Templates Section */}
          <div className="mt-2">
            <button
              onClick={() => toggleSection('industry')}
              className="w-full flex items-center gap-3 px-6 py-3 hover:bg-blue-700 transition-colors text-left"
            >
              <span className="text-xl">🏭</span>
              <span className="font-semibold flex-1">
                Industry Templates
              </span>
              <span className={`text-lg transition-transform ${expandedSections.industry ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {expandedSections.industry && (
              <Link
                to="/industry-templates"
                className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                  isActive('/industry-templates')
                    ? 'bg-blue-700 border-white text-white'
                    : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                }`}
              >
                <span className="text-lg">📋</span>
                <span>Template Upload</span>
              </Link>
            )}
          </div>

          {/* Correlation Section */}
          <div className="mt-2">
            <button
              onClick={() => toggleSection('correlation')}
              className="w-full flex items-center gap-3 px-6 py-3 hover:bg-blue-700 transition-colors text-left"
            >
              <span className="text-xl">⚡</span>
              <span className="font-semibold flex-1">Correlation</span>
              <span className={`text-lg transition-transform ${expandedSections.correlation ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {expandedSections.correlation && (
              <Link
                to="/correlation"
                className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                  isActive('/correlation')
                    ? 'bg-blue-700 border-white text-white'
                    : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                }`}
              >
                <span className="text-lg">🔗</span>
                <span>Correlation & Analysis</span>
              </Link>
            )}
          </div>

          {/* Business Capability Mapping Section */}
          <div className="mt-2">
            <button
              onClick={() => toggleSection('capability')}
              className="w-full flex items-center gap-3 px-6 py-3 hover:bg-blue-700 transition-colors text-left"
            >
              <span className="text-xl">📊</span>
              <span className="font-semibold flex-1">Business Capability Mapping</span>
              <span className={`text-lg transition-transform ${expandedSections.capability ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {expandedSections.capability && (
              <>
                <Link
                  to="/capability/standardization"
                  className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                    isActive('/capability/standardization')
                      ? 'bg-blue-700 border-white text-white'
                      : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                  }`}
                >
                  <span className="text-lg">🔄</span>
                  <span>Standardization & ERP Consolidation</span>
                </Link>
                <Link
                  to="/capability/inventory"
                  className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                    isActive('/capability/inventory')
                      ? 'bg-blue-700 border-white text-white'
                      : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                  }`}
                >
                  <span className="text-lg">📦</span>
                  <span>Business Capability</span>
                </Link>
                <Link
                  to="/capability/traceability"
                  className={`flex items-center gap-3 px-6 py-3 ml-6 transition-colors border-l-2 ${
                    isActive('/capability/traceability')
                      ? 'bg-blue-700 border-white text-white'
                      : 'border-blue-600 text-blue-100 hover:text-white hover:bg-blue-700'
                  }`}
                >
                  <span className="text-lg">🎯</span>
                  <span>Final Traceability Matrix</span>
                </Link>
              </>
            )}
          </div>
        </nav>

        {/* Footer */}
        <div className="border-t border-blue-700 px-6 py-4">
          <p className="text-xs text-blue-200 text-center">
            Version 1.0<br />
            Infrastructure Assessment Platform
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Layout;
