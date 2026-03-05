import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle } from 'lucide-react';
import apiClient from '../../services/api';

const BusinessCapabilityMapping = () => {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalApplications, setTotalApplications] = useState(0);
  const [perPage] = useState(10);
  const [selectedCapability, setSelectedCapability] = useState(null);
  const [capabilityDetails, setCapabilityDetails] = useState(null);
  const [viewMode, setViewMode] = useState('mapping'); // 'mapping' or 'analysis'
  const [generating, setGenerating] = useState(false);
  const [clearing, setClearing] = useState(false);

  // Fetch capability mapping data
  const fetchCapabilityMapping = useCallback(async (page) => {
    try {
      setLoading(true);
      const response = await apiClient.get(
        `/capability/mapping?page=${page}&per_page=${perPage}`
      );
      
      if (response.data?.data) {
        setApplications(response.data.data.applications || []);
        setTotalPages(response.data.data.pagination?.pages || 1);
        setTotalApplications(response.data.data.pagination?.total || 0);
      }
      setLoading(false);
    } catch (err) {
      console.error('Failed to load capability mapping:', err);
      setLoading(false);
    }
  }, [perPage]);

  useEffect(() => {
    if (viewMode === 'mapping') {
      fetchCapabilityMapping(currentPage);
    }
  }, [currentPage, viewMode, fetchCapabilityMapping]);

  const handleGenerate = async () => {
    setGenerating(true);
    if (viewMode === 'mapping') await fetchCapabilityMapping(currentPage);
    setGenerating(false);
  };

  const handleClear = async () => {
    if (!window.confirm('Clear all capability/industry template data? This will reset the capability mapping.')) return;
    try {
      setClearing(true);
      await apiClient.delete('/capability/clear');
      setApplications([]);
      setTotalApplications(0);
      setTotalPages(1);
    } catch (err) {
      console.error('Clear failed:', err);
    } finally {
      setClearing(false);
    }
  };

  const handleCapabilityClick = async (capabilityName) => {
    try {
      setLoading(true);
      setSelectedCapability(capabilityName);
      const response = await apiClient.get(
        `/capability/details/${encodeURIComponent(capabilityName)}`
      );
      
      if (response.data?.data) {
        setCapabilityDetails(response.data.data);
      }
      setViewMode('details');
      setLoading(false);
    } catch (err) {
      console.error('Failed to load capability details:', err);
      setLoading(false);
    }
  };

  if (loading && viewMode === 'mapping') {
    return <div className="p-8 text-center">Loading business capability mapping...</div>;
  }

  if (viewMode === 'details' && capabilityDetails) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <button
              onClick={() => {
                setViewMode('analysis');
                setSelectedCapability(null);
                setCapabilityDetails(null);
              }}
              className="text-purple-600 hover:text-purple-700 font-semibold mb-4 flex items-center gap-2"
            >
              ← Back to Capability Analysis
            </button>
            <h1 className="text-4xl font-bold text-gray-900">
              Capability: {selectedCapability}
            </h1>
          </div>

          {/* L2 Level Summary Analysis */}
          {capabilityDetails.analysis && (
            <div className={`bg-white rounded-lg shadow-md p-8 mb-8 border-l-4 ${
              capabilityDetails.analysis.is_elimination_candidate ? 'border-red-500' : 'border-green-500'
            }`}>
              {/* Header */}
              <div className="mb-6">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-2xl font-bold text-gray-900">
                    Consolidation Analysis
                  </h3>
                  {capabilityDetails.analysis.is_elimination_candidate && (
                    <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-semibold flex items-center gap-1">
                      <AlertCircle size={16} />
                      CONSOLIDATION OPPORTUNITY
                    </span>
                  )}
                </div>
              </div>

              {capabilityDetails.analysis.is_elimination_candidate ? (
                <div className="space-y-8">
                  {/* L2: Summary Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                      <h4 className="font-bold text-gray-900 mb-2">Total Applications</h4>
                      <p className="text-3xl font-bold text-red-600">{capabilityDetails.analysis.total_apps}</p>
                      <p className="text-xs text-gray-600 mt-1">Providing this capability</p>
                    </div>

                    {capabilityDetails.analysis.consolidation_summary && (
                      <>
                        <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                          <h4 className="font-bold text-gray-900 mb-2">Applications to Eliminate</h4>
                          <p className="text-3xl font-bold text-orange-600">{capabilityDetails.analysis.consolidation_summary.apps_to_eliminate}</p>
                          <p className="text-xs text-gray-600 mt-1">Redundant applications</p>
                        </div>

                        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                          <h4 className="font-bold text-gray-900 mb-2">Consolidation Ratio</h4>
                          <p className="text-3xl font-bold text-blue-600">{capabilityDetails.analysis.consolidation_summary.consolidation_ratio}</p>
                          <p className="text-xs text-gray-600 mt-1">Target consolidation</p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* L2: Business Classification Breakdown */}
                  {capabilityDetails.applications && capabilityDetails.applications.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* By Owner */}
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                        <h4 className="font-bold text-gray-900 mb-4">Applications by Business Owner</h4>
                        <div className="space-y-2">
                          {(() => {
                            const byOwner = {};
                            capabilityDetails.applications.forEach(app => {
                              const owner = app.business_owner || 'Unassigned';
                              byOwner[owner] = (byOwner[owner] || 0) + 1;
                            });
                            return Object.entries(byOwner)
                              .sort((a, b) => b[1] - a[1])
                              .map(([owner, count]) => (
                                <div key={owner} className="flex justify-between items-center">
                                  <span className="text-sm text-gray-700">{owner}</span>
                                  <span className="bg-blue-200 text-blue-900 px-3 py-1 rounded-full text-sm font-semibold">{count}</span>
                                </div>
                              ));
                          })()}
                        </div>
                      </div>

                      {/* By Platform */}
                      <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
                        <h4 className="font-bold text-gray-900 mb-4">Applications by Platform Host</h4>
                        <div className="space-y-2">
                          {(() => {
                            const byPlatform = {};
                            capabilityDetails.applications.forEach(app => {
                              const platform = app.platform_host || 'N/A';
                              byPlatform[platform] = (byPlatform[platform] || 0) + 1;
                            });
                            return Object.entries(byPlatform)
                              .sort((a, b) => b[1] - a[1])
                              .map(([platform, count]) => (
                                <div key={platform} className="flex justify-between items-center">
                                  <span className="text-sm text-gray-700">{platform}</span>
                                  <span className="bg-purple-200 text-purple-900 px-3 py-1 rounded-full text-sm font-semibold">{count}</span>
                                </div>
                              ));
                          })()}
                        </div>
                      </div>

                      {/* By Application Type */}
                      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                        <h4 className="font-bold text-gray-900 mb-4">Applications by Type</h4>
                        <div className="space-y-2">
                          {(() => {
                            const byType = {};
                            capabilityDetails.applications.forEach(app => {
                              const type = app.application_type || 'N/A';
                              byType[type] = (byType[type] || 0) + 1;
                            });
                            return Object.entries(byType)
                              .sort((a, b) => b[1] - a[1])
                              .map(([type, count]) => (
                                <div key={type} className="flex justify-between items-center">
                                  <span className="text-sm text-gray-700">{type}</span>
                                  <span className="bg-green-200 text-green-900 px-3 py-1 rounded-full text-sm font-semibold">{count}</span>
                                </div>
                              ));
                          })()}
                        </div>
                      </div>

                      {/* By Install Type */}
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                        <h4 className="font-bold text-gray-900 mb-4">Applications by Install Type</h4>
                        <div className="space-y-2">
                          {(() => {
                            const byInstall = {};
                            capabilityDetails.applications.forEach(app => {
                              const install = app.install_type || 'N/A';
                              byInstall[install] = (byInstall[install] || 0) + 1;
                            });
                            return Object.entries(byInstall)
                              .sort((a, b) => b[1] - a[1])
                              .map(([install, count]) => (
                                <div key={install} className="flex justify-between items-center">
                                  <span className="text-sm text-gray-700">{install}</span>
                                  <span className="bg-yellow-200 text-yellow-900 px-3 py-1 rounded-full text-sm font-semibold">{count}</span>
                                </div>
                              ));
                          })()}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* L2: Technology Distribution */}
                  {capabilityDetails.analysis.technology_distribution && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                      <h4 className="font-bold text-gray-900 mb-4">Technology Distribution</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {Object.entries(capabilityDetails.analysis.technology_distribution).map(([tech, apps]) => (
                          <div key={tech} className="bg-white p-4 rounded border border-gray-300">
                            <div className="flex justify-between items-center mb-2">
                              <p className="font-semibold text-gray-900">{tech}</p>
                              <span className="bg-gray-200 text-gray-900 px-3 py-1 rounded-full text-xs font-bold">{apps.length}</span>
                            </div>
                            <ul className="text-xs text-gray-600 space-y-1">
                              {apps.slice(0, 4).map((app, idx) => (
                                <li key={idx}>• {app}</li>
                              ))}
                              {apps.length > 4 && <li className="italic text-gray-500">+ {apps.length - 4} more</li>}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendation */}
                  <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white rounded-lg p-6">
                    <h4 className="text-lg font-bold mb-2">Consolidation Recommendation</h4>
                    <p className="text-sm">{capabilityDetails.analysis.consolidation_summary?.recommendation || capabilityDetails.analysis.recommendation}</p>
                  </div>
                </div>
              ) : (
                <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                  <p className="text-lg font-semibold text-green-800">
                    ✓ Optimal Configuration
                  </p>
                  <p className="text-sm text-green-700 mt-1">
                    {capabilityDetails.analysis.recommendation}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* L3: Detailed Application Inventory */}
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Application Inventory (L3 Details)
              </h2>
              <p className="text-sm text-gray-600">Complete list of {capabilityDetails.applications?.length || 0} applications providing this capability</p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-gray-100 to-gray-50 border-b-2 border-gray-300">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 bg-gray-100">APP ID</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900">APP NAME</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900">BUSINESS OWNER</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900">ARCHITECTURE</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900">PLATFORM</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900">APP TYPE</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-900">INSTALL TYPE</th>
                  </tr>
                </thead>
                <tbody>
                  {capabilityDetails.applications?.map((app, idx) => (
                    <tr key={idx} className="border-b border-gray-100 hover:bg-blue-50 transition">
                      <td className="px-4 py-3 text-xs font-mono text-gray-700 bg-gray-50">{app.app_id}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{app.app_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                          {app.business_owner || 'Unassigned'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        <span className="text-xs">{app.architecture_type || 'N/A'}</span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className="inline-block bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-medium">
                          {app.platform_host || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className="inline-block bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                          {app.application_type || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className="inline-block bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">
                          {app.install_type || 'N/A'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {(!capabilityDetails.applications || capabilityDetails.applications.length === 0) && (
              <div className="p-8 text-center text-gray-500">
                <p>No applications found for this capability</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Tab Navigation */}
        <div className="mb-8 flex items-center justify-between border-b border-gray-200">
          <div className="flex gap-4">
            <button
              onClick={() => setViewMode('mapping')}
              className={`px-6 py-3 font-semibold border-b-2 transition ${
                viewMode === 'mapping'
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Application Mapping
            </button>
            <button
              onClick={() => setViewMode('analysis')}
              className={`px-6 py-3 font-semibold border-b-2 transition ${
                viewMode === 'analysis'
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Capability Analysis
            </button>
          </div>
          <div className="flex gap-3 pb-2">
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

        {viewMode === 'mapping' && (
          <>
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-4xl font-bold text-gray-900 mb-2">Business Capability Mapping</h1>
              <p className="text-gray-600 text-lg">Application-to-capability assignments with consolidation opportunities</p>
            </div>

            {/* Applications Table */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-8 border border-gray-200">
              {/* Table Header */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">Applications</h2>
                    <p className="text-blue-100 text-sm">Total: {totalApplications} applications across {totalPages} pages</p>
                  </div>
                  <div className="bg-blue-500 bg-opacity-50 px-4 py-2 rounded-lg">
                    <p className="text-white font-semibold text-lg">Page {currentPage}/{totalPages}</p>
                  </div>
                </div>
              </div>

              {/* Table Container */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  {/* Table Head */}
                  <thead>
                    <tr className="border-b-2 border-gray-200 bg-gray-50">
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">App ID</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">App Name</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Owner</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Architecture</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Platform</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Type</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Business Capability</th>
                      <th className="px-6 py-4 text-center text-xs font-bold text-gray-700 uppercase tracking-wider">Action</th>
                    </tr>
                  </thead>
                  
                  {/* Table Body */}
                  <tbody className="divide-y divide-gray-100">
                    {applications.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                          <p className="text-lg font-medium">No applications found</p>
                          <p className="text-sm">Try adjusting your search filters</p>
                        </td>
                      </tr>
                    ) : (
                      applications.map((app, idx) => (
                        <tr 
                          key={idx} 
                          className="hover:bg-blue-50 transition-colors duration-150 even:bg-gray-50 hover:shadow-md"
                        >
                          <td className="px-6 py-4">
                            <code className="text-xs font-mono bg-gray-100 px-2 py-1 rounded text-gray-700">{app.app_id}</code>
                          </td>
                          <td className="px-6 py-4">
                            <p className="font-semibold text-gray-900">{app.app_name}</p>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {app.business_owner || 'Unassigned'}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-gray-700 text-sm">{app.architecture_type || 'N/A'}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                              {app.platform_host || 'N/A'}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              {app.application_type || 'N/A'}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => handleCapabilityClick(app.capability)}
                              className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 hover:bg-amber-200 transition-colors"
                            >
                              <span className="truncate max-w-xs">{app.capability || 'Unclassified'}</span>
                            </button>
                          </td>
                          <td className="px-6 py-4 text-center">
                            <button
                              onClick={() => handleCapabilityClick(app.capability)}
                              title="View capability details"
                              className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-blue-600 hover:bg-blue-100 hover:text-blue-700 transition-colors font-bold text-lg"
                            >
                              →
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Footer */}
              <div className="px-8 py-5 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-700">
                    Page <span className="font-bold text-gray-900">{currentPage}</span> of <span className="font-bold text-gray-900">{totalPages}</span>
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-100 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    ← Previous
                  </button>
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-100 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    Next →
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {viewMode === 'analysis' && <CapabilityAnalysisView onViewDetails={handleCapabilityClick} />}
      </div>
    </div>
  );
};

// Capability Analysis Component
const CapabilityAnalysisView = ({ onViewDetails }) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalysis = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/capability/analysis');
      if (response.data?.data) {
        setAnalysis(response.data.data);
      }
      setLoading(false);
    } catch (err) {
      console.error('Failed to load analysis:', err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  if (loading) {
    return <div className="text-center p-8">Loading capability analysis...</div>;
  }

  return (
    <div>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
          <p className="text-sm text-gray-600 mb-2">Total Capabilities</p>
          <p className="text-4xl font-bold text-blue-600">{analysis?.summary?.total_capabilities || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-purple-500">
          <p className="text-sm text-gray-600 mb-2">Total Applications</p>
          <p className="text-4xl font-bold text-purple-600">{analysis?.summary?.total_applications || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-red-500">
          <p className="text-sm text-gray-600 mb-2">Elimination Candidates</p>
          <p className="text-4xl font-bold text-red-600">{analysis?.summary?.elimination_candidates || 0}</p>
          <p className="text-xs text-gray-500 mt-2">Capabilities with 2+ apps</p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-yellow-500">
          <p className="text-sm text-gray-600 mb-2">Redundant Applications</p>
          <p className="text-4xl font-bold text-yellow-600">{analysis?.summary?.total_redundant_apps || 0}</p>
          <p className="text-xs text-gray-500 mt-2">Apps available for consolidation</p>
        </div>
      </div>

      {/* Capabilities List */}
      <div className="space-y-4">
        {analysis?.capabilities?.map((cap, idx) => (
          <div key={idx} className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${
            cap.is_elimination_candidate ? 'border-red-500' : 'border-green-500'
          }`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-2xl font-bold text-gray-900">{cap.capability}</h3>
                  {cap.is_elimination_candidate && (
                    <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold ${
                      cap.priority === 'HIGH' ? 'bg-red-100 text-red-700' :
                      cap.priority === 'MEDIUM' ? 'bg-orange-100 text-orange-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      <AlertCircle size={16} />
                      {cap.priority} PRIORITY
                    </span>
                  )}
                </div>
                <p className="text-gray-600 mb-4">{cap.elimination_reason || 'No elimination needed'}</p>
                
                {cap.is_elimination_candidate && (
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-red-50 p-3 rounded">
                      <p className="text-xs text-gray-600">Total Apps</p>
                      <p className="text-2xl font-bold text-red-600">{cap.app_count}</p>
                    </div>
                    <div className="bg-orange-50 p-3 rounded">
                      <p className="text-xs text-gray-600">Redundant Apps</p>
                      <p className="text-2xl font-bold text-orange-600">{cap.optimization_potential?.redundant_apps}</p>
                    </div>
                    <div className="bg-blue-50 p-3 rounded">
                      <p className="text-xs text-gray-600">Consolidation Ratio</p>
                      <p className="text-2xl font-bold text-blue-600">{cap.optimization_potential?.consolidation_ratio}</p>
                    </div>
                  </div>
                )}
                
                <div className="flex items-center gap-4">
                  <div className="text-sm text-gray-600">
                    Representative App:{' '}
                    <button
                      onClick={() => onViewDetails(cap.capability)}
                      className="text-purple-600 hover:text-purple-700 font-semibold hover:underline cursor-pointer"
                      title="Click to view all applications for this capability"
                    >
                      {cap.sample_app}
                    </button>
                  </div>
                </div>
              </div>
              <button
                onClick={() => onViewDetails(cap.capability)}
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 font-semibold whitespace-nowrap"
              >
                View Details →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default BusinessCapabilityMapping;
