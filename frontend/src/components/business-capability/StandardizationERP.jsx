import React, { useState, useEffect } from 'react';
import { TrendingDown, ArrowRight } from 'lucide-react';
import api from '../../services/api';

const StandardizationERP = () => {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const response = await api.get('/api/standardization-analysis');
        if (response.data && response.data.analysis) {
          setAnalysisData(response.data.analysis);
        }
        setLoading(false);
      } catch (err) {
        console.error('Failed to load standardization analysis data:', err);
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, []);

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
          <div className="flex items-center gap-3">
            <TrendingDown size={40} className="text-purple-600" />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Standardization & Consolidation Scenario</h1>
              <p className="text-gray-600 mt-2">Before and After: Application rationalization and infrastructure consolidation</p>
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
