import React, { useState, useEffect, useCallback } from 'react';
import { TrendingDown, ArrowRight } from 'lucide-react';
import api from '../../services/api';

const StandardizationERP = () => {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [clearing, setClearing] = useState(false);

  const fetchAnalysis = useCallback(async () => {
    try {
      setGenerating(true);
      const response = await api.get('/api/standardization-analysis');
      if (response.data && response.data.analysis) {
        setAnalysisData(response.data.analysis);
      }
    } catch (err) {
      console.error('Failed to load standardization analysis data:', err);
    } finally {
      setGenerating(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAnalysis(); }, [fetchAnalysis]);

  const handleGenerate = () => fetchAnalysis();

  const handleClear = async () => {
    if (!window.confirm('Clear all standardization (CorentData) data? This will also reset Dashboard infrastructure stats.')) return;
    try {
      setClearing(true);
      await api.delete('/api/standardization-analysis/clear');
      setAnalysisData(null);
    } catch (err) {
      console.error('Clear failed:', err);
    } finally {
      setClearing(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading analysis...</div>;
  }

  const infra = analysisData?.infrastructure_analysis || {};
  const tech = analysisData?.technology_standardization || {};
  const code = analysisData?.code_analysis || {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingDown size={40} className="text-purple-600" />
              <div>
                <h1 className="text-4xl font-bold text-gray-900">Standardization &amp; Consolidation Scenario</h1>
                <p className="text-gray-600 mt-2">Before and After: Application rationalization and infrastructure consolidation</p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleGenerate}
                disabled={generating || clearing}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                {generating ? (
                  <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg> Generating...</>
                ) : (
                  <><svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg> Generate</>
                )}
              </button>
              <button
                onClick={handleClear}
                disabled={generating || clearing}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                {clearing ? (
                  <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg> Clearing...</>
                ) : (
                  <><svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg> Clear</>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Before Section */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span className="text-3xl">⬅️</span> Current Infrastructure State
          </h2>
          
          <div className="bg-white rounded-xl shadow-md p-8 border-l-4 border-red-500">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Applications */}
              <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-6 border border-red-200">
                <div className="text-4xl font-bold text-red-600 mb-2">{infra.total_applications || '195'}</div>
                <div className="text-gray-700 font-semibold mb-3">Total Applications</div>
                <p className="text-sm text-gray-600">Scattered across {infra.unique_servers || '26'} infrastructure servers</p>
              </div>

              {/* Database Technologies */}
              <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-6 border border-orange-200">
                <div className="text-4xl font-bold text-orange-600 mb-2">{tech.total_db_engines || '5'}</div>
                <div className="text-gray-700 font-semibold mb-3">Database Engines</div>
                <p className="text-sm text-gray-600">Oracle, PostgreSQL, SQL Server, MySQL, and MongoDB creating data silos</p>
              </div>

              {/* Operating Systems */}
              <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-6 border border-yellow-200">
                <div className="text-4xl font-bold text-yellow-600 mb-2">4</div>
                <div className="text-gray-700 font-semibold mb-3">OS Variants</div>
                <p className="text-sm text-gray-600">Windows, RHEL, Ubuntu with inconsistent versions and patches</p>
              </div>

              {/* Source Code */}
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
                <div className="text-4xl font-bold text-blue-600 mb-2">{code.cloud_ready_percentage?.toFixed(1) || '48.2'}%</div>
                <div className="text-gray-700 font-semibold mb-3">Cloud-Ready</div>
                <p className="text-sm text-gray-600">{code.source_code_percentage?.toFixed(1) || '91.3'}% have source code access</p>
              </div>
            </div>
          </div>
        </div>

        {/* Arrow Transition */}
        <div className="flex justify-center my-8">
          <div className="flex flex-col items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg shadow-lg">
            <ArrowRight size={32} className="rotate-90" />
            <span className="font-semibold">After Standardization & Consolidation</span>
          </div>
        </div>

        {/* After Section */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span className="text-3xl">➡️</span> Recommended Consolidated State
          </h2>
          
          <div className="bg-white rounded-xl shadow-md p-8 border-l-4 border-emerald-500">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Unified Platform */}
              <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg p-6 border border-emerald-200">
                <div className="text-4xl font-bold text-emerald-600 mb-2">5</div>
                <div className="text-gray-700 font-semibold mb-3">Standardized Platforms</div>
                <p className="text-sm text-gray-600">Consolidate to 5 primary infrastructure platforms for unified management</p>
              </div>

              {/* Database Engines */}
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
                <div className="text-4xl font-bold text-blue-600 mb-2">3-4</div>
                <div className="text-gray-700 font-semibold mb-3">Database Standards</div>
                <p className="text-sm text-gray-600">Standardized database engines with cloud-ready architecture</p>
              </div>

              {/* Operating Systems */}
              <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border border-purple-200">
                <div className="text-4xl font-bold text-purple-600 mb-2">2</div>
                <div className="text-gray-700 font-semibold mb-3">OS Standards</div>
                <p className="text-sm text-gray-600">Unified OS standards with consistent patching and versioning</p>
              </div>

              {/* Consolidated Teams */}
              <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-lg p-6 border border-indigo-200">
                <div className="text-4xl font-bold text-indigo-600 mb-2">2</div>
                <div className="text-gray-700 font-semibold mb-3">Specialized Teams</div>
                <p className="text-sm text-gray-600">Infrastructure and consolidation specialists focused on cloud readiness</p>
              </div>
            </div>
          </div>
        </div>

        {/* Benefits Summary */}
        <div className="mt-12 bg-white rounded-xl shadow-md p-8 border-l-4 border-green-500">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Business Value & ROI</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex gap-4">
              <span className="text-2xl">🎯</span>
              <div>
                <h4 className="font-semibold text-gray-900">Infrastructure Simplification</h4>
                <p className="text-sm text-gray-600 mt-1">Reduce platform complexity from 26 to 5 standardized infrastructure endpoints</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-2xl">💾</span>
              <div>
                <h4 className="font-semibold text-gray-900">Data Consistency</h4>
                <p className="text-sm text-gray-600 mt-1">Eliminate data silos through standardized database architecture</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-2xl">👥</span>
              <div>
                <h4 className="font-semibold text-gray-900">Team Efficiency</h4>
                <p className="text-sm text-gray-600 mt-1">Consolidate expertise in infrastructure and cloud specialization</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-2xl">📉</span>
              <div>
                <h4 className="font-semibold text-gray-900">Cost Reduction</h4>
                <p className="text-sm text-gray-600 mt-1">EUR 835K annual savings with 1.9 year payback period (168% 5-year ROI)</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-2xl">☁️</span>
              <div>
                <h4 className="font-semibold text-gray-900">Cloud Migration Ready</h4>
                <p className="text-sm text-gray-600 mt-1">48% of applications already cloud-ready; modern architecture supports rapid cloud adoption</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-2xl">⚡</span>
              <div>
                <h4 className="font-semibold text-gray-900">Operational Velocity</h4>
                <p className="text-sm text-gray-600 mt-1">Standardized platforms enable faster deployment and reduced maintenance overhead</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StandardizationERP;
