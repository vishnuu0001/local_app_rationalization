import React, { useState, useEffect } from 'react';
import { GitBranch, CheckCircle, AlertCircle, XCircle, ChevronDown, ChevronUp, Loader } from 'lucide-react';
import { getTraceabilityMatrix } from '../../services/api';

const FinalTraceabilityMatrix = () => {
  const [traceabilityData, setTraceabilityData] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [filterAction, setFilterAction] = useState('All');

  useEffect(() => {
    const fetchTraceabilityMatrix = async () => {
      try {
        setLoading(true);
        const response = await getTraceabilityMatrix();
        
        if (response.data.status === 'success') {
          setTraceabilityData(response.data.data || []);
          setSummary(response.data.summary || {});
          setError(null);
        } else {
          setError('Failed to load traceability matrix');
        }
      } catch (err) {
        console.error('Error fetching traceability matrix:', err);
        setError('Unable to load traceability data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchTraceabilityMatrix();
  }, []);

  const toggleRowExpansion = (index) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  const filteredData = filterAction === 'All' 
    ? traceabilityData 
    : traceabilityData.filter(item => item.action === filterAction);

  const getRedundancyColor = (redundancy) => {
    switch(redundancy) {
      case 'Unique': return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'Duplicate': return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'High': return 'bg-red-100 text-red-800 border-red-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getActionColor = (action) => {
    switch(action) {
      case 'Retain': return 'bg-emerald-50 text-emerald-700 border-emerald-300 border-l-4 border-l-emerald-600';
      case 'Migrate to SAP': return 'bg-blue-50 text-blue-700 border-blue-300 border-l-4 border-l-blue-600';
      case 'Decommission': return 'bg-red-50 text-red-700 border-red-300 border-l-4 border-l-red-600';
      default: return 'bg-gray-50 text-gray-700';
    }
  };

  const getActionIcon = (action) => {
    switch(action) {
      case 'Retain': return <CheckCircle size={18} className="text-emerald-600" />;
      case 'Migrate to SAP': return <AlertCircle size={18} className="text-blue-600" />;
      case 'Decommission': return <XCircle size={18} className="text-red-600" />;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3">
            <GitBranch size={40} className="text-indigo-600" />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Final Traceability Matrix</h1>
              <p className="text-gray-600 mt-2">Complete application-to-infrastructure mapping with remediation actions for rationalization</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        
        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-xl shadow-md p-8 border border-gray-200 flex items-center justify-center gap-3">
            <Loader size={24} className="text-indigo-600 animate-spin" />
            <p className="text-gray-600 text-lg">Loading traceability matrix...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-50 rounded-xl shadow-md p-6 border border-red-300 mb-8">
            <div className="flex items-center gap-3">
              <XCircle size={24} className="text-red-600" />
              <div>
                <h3 className="font-semibold text-red-900">Error Loading Data</h3>
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Filter Buttons */}
        {!loading && !error && (
          <div className="mb-6 flex flex-wrap gap-2">
            <button
              onClick={() => setFilterAction('All')}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                filterAction === 'All'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              All ({traceabilityData.length})
            </button>
            <button
              onClick={() => setFilterAction('Retain')}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                filterAction === 'Retain'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Retain ({traceabilityData.filter(i => i.action === 'Retain').length})
            </button>
            <button
              onClick={() => setFilterAction('Migrate to SAP')}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                filterAction === 'Migrate to SAP'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Migrate ({traceabilityData.filter(i => i.action === 'Migrate to SAP').length})
            </button>
            <button
              onClick={() => setFilterAction('Decommission')}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                filterAction === 'Decommission'
                  ? 'bg-red-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Decommission ({traceabilityData.filter(i => i.action === 'Decommission').length})
            </button>
          </div>
        )}

        {/* Main Table */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200 mb-8">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gradient-to-r from-indigo-50 to-indigo-100 border-b-2 border-indigo-300">
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider w-12"></th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Infrastructure
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Application
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Repository
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Capability
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Redundancy
                  </th>
                  <th className="px-6 py-4 text-left font-bold text-gray-900 text-sm uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredData.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      No entries found for the selected filter.
                    </td>
                  </tr>
                ) : (
                  filteredData.map((item, index) => (
                    <React.Fragment key={index}>
                      <tr 
                        className={`border-b transition-colors hover:bg-indigo-50 cursor-pointer ${
                          index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                        }`}
                        onClick={() => toggleRowExpansion(index)}
                      >
                        <td className="px-6 py-4 text-center">
                          {expandedRows.has(index) ? (
                            <ChevronUp size={18} className="text-indigo-600" />
                          ) : (
                            <ChevronDown size={18} className="text-gray-400" />
                          )}
                        </td>
                        <td className="px-6 py-4 text-gray-900 font-semibold">
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700 border border-gray-300">
                            {item.infrastructure}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-700 font-medium">{item.application}</td>
                        <td className="px-6 py-4 text-gray-700">
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200">
                            {item.repository}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-700">{item.capability}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getRedundancyColor(item.redundancy)}`}>
                            {item.redundancy}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold ${getActionColor(item.action)}`}>
                            {getActionIcon(item.action)}
                            {item.action}
                          </div>
                        </td>
                      </tr>
                      
                      {/* Detail Row */}
                      {expandedRows.has(index) && (
                        <tr className={`border-b ${index % 2 === 0 ? 'bg-indigo-50' : 'bg-indigo-100'}`}>
                          <td colSpan="7" className="px-6 py-4">
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <p className="text-sm font-semibold text-gray-700">Application ID</p>
                                <p className="text-gray-900">{item.app_id}</p>
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-gray-700">Application Type</p>
                                <p className="text-gray-900">{item.application_type || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-gray-700">Apps with this Capability</p>
                                <p className="text-gray-900">{item.apps_with_capability}</p>
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-gray-700">Rationalization Reason</p>
                                <p className="text-gray-900">
                                  {item.redundancy === 'Unique' && 'No redundancy - unique capability'}
                                  {item.redundancy === 'Duplicate' && 'Duplicate capability - consolidation opportunity'}
                                  {item.redundancy === 'High' && 'High redundancy - recommend decommission'}
                                </p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Legend and Summary */}
        {!loading && !error && summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Legend */}
          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <h3 className="text-xl font-bold text-gray-900 mb-6">Action Legend</h3>
            
            <div className="space-y-4">
              <div className="flex items-start gap-3 pb-4 border-b border-gray-200">
                <CheckCircle size={20} className="text-emerald-600 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">Retain</h4>
                  <p className="text-sm text-gray-600">Keep as-is - unique capability with no redundancy</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3 pb-4 border-b border-gray-200">
                <AlertCircle size={20} className="text-blue-600 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">Migrate to SAP</h4>
                  <p className="text-sm text-gray-600">Consolidate capability into SAP EWM core module</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <XCircle size={20} className="text-red-600 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">Decommission</h4>
                  <p className="text-sm text-gray-600">Retire legacy/redundant application and infrastructure</p>
                </div>
              </div>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-emerald-600">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">Applications to Retain</p>
                  <p className="text-3xl font-bold text-emerald-600 mt-2">{summary.applications_to_retain || 0}</p>
                </div>
                <CheckCircle size={40} className="text-emerald-600 opacity-20" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-600">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">Applications to Migrate</p>
                  <p className="text-3xl font-bold text-blue-600 mt-2">{summary.applications_to_migrate || 0}</p>
                </div>
                <AlertCircle size={40} className="text-blue-600 opacity-20" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-red-600">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-600 text-sm font-semibold">Applications to Decommission</p>
                  <p className="text-3xl font-bold text-red-600 mt-2">{summary.applications_to_decommission || 0}</p>
                </div>
                <XCircle size={40} className="text-red-600 opacity-20" />
              </div>
            </div>
          </div>
        </div>
        )}

        {/* Implementation Roadmap */}
        {!loading && !error && summary && (
        <div className="mt-8 bg-white rounded-lg shadow-md p-8 border border-gray-200">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Implementation Roadmap & Analysis</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <p className="text-sm text-blue-700 font-semibold">Total Applications</p>
              <p className="text-2xl font-bold text-blue-900 mt-2">{summary.total_applications || 0}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
              <p className="text-sm text-purple-700 font-semibold">Unique Infrastructure</p>
              <p className="text-2xl font-bold text-purple-900 mt-2">{summary.unique_infrastructure || 0}</p>
            </div>
            <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
              <p className="text-sm text-indigo-700 font-semibold">Unique Capabilities</p>
              <p className="text-2xl font-bold text-indigo-900 mt-2">{summary.unique_capabilities || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
              <p className="text-sm text-amber-700 font-semibold">Consolidation Potential</p>
              <p className="text-2xl font-bold text-amber-900 mt-2">{summary.potential_consolidation || 0} apps</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="relative">
              <div className="absolute top-0 left-8 w-1 h-full bg-blue-200"></div>
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center h-12 w-12 rounded-full bg-blue-600 text-white font-bold">
                    1
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Phase 1: Assessment</h4>
                  <p className="text-sm text-gray-600 mt-2">Complete traceability analysis and impact assessment across all {summary.total_applications || 0} applications</p>
                  <p className="text-xs text-blue-600 font-semibold mt-3">Weeks 1-4</p>
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="absolute top-0 left-8 w-1 h-full bg-orange-200"></div>
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center h-12 w-12 rounded-full bg-orange-600 text-white font-bold">
                    2
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Phase 2: Migration</h4>
                  <p className="text-sm text-gray-600 mt-2">Migrate {summary.applications_to_migrate || 0} applications to SAP EWM and consolidate capabilities</p>
                  <p className="text-xs text-orange-600 font-semibold mt-3">Weeks 5-12</p>
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center h-12 w-12 rounded-full bg-emerald-600 text-white font-bold">
                    3
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Phase 3: Retirement</h4>
                  <p className="text-sm text-gray-600 mt-2">Decommission {summary.applications_to_decommission || 0} redundant applications and optimize infrastructure</p>
                  <p className="text-xs text-emerald-600 font-semibold mt-3">Weeks 13-16</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

export default FinalTraceabilityMatrix;
