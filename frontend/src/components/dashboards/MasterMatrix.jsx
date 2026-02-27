import React, { useState } from 'react';
import { Download } from 'lucide-react';

const MasterMatrix = ({ data }) => {
  const [filterConfidence, setFilterConfidence] = useState('all');
  const masterMatrix = data.master_matrix || [];

  const getInfra = (row) => row.infra || row.infrastructure || '';
  const getServer = (row) => row.server || row.server_type || '';
  const getRepo = (row) => row.repo || row.repository || '';
  
  // Filter based on confidence level
  const filteredData = filterConfidence === 'all'
    ? masterMatrix
    : masterMatrix.filter(row => row.confidence_level === filterConfidence);
  
  // Download as CSV
  const downloadCSV = () => {
    const headers = ['Infra', 'Server', 'Installed App', 'App Component', 'Repo', 'Confidence', 'App ID', 'Tech Stack', 'Version'];
    const rows = filteredData.map(row => [
      getInfra(row),
      getServer(row),
      row.installed_app || '',
      row.app_component || '',
      getRepo(row),
      `${(row.confidence * 100).toFixed(0)}%`,
      row.app_id || '',
      row.tech_stack || '',
      row.version || '',
    ]);
    
    const csv = [headers, ...rows].map(row => 
      row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `master-matrix-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };
  
  if (!data || masterMatrix.length === 0) {
    return <div className="text-gray-500">No master matrix data available</div>;
  }
  
  // Count by confidence level
  const confidenceCounts = {
    high: masterMatrix.filter(r => r.confidence_level === 'high').length,
    medium: masterMatrix.filter(r => r.confidence_level === 'medium').length,
    unmatched: masterMatrix.filter(r => r.confidence_level === 'unmatched').length,
  };
  
  return (
    <div className="space-y-6">
      {/* Header with Filter and Export */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Master Matrix</h3>
          <p className="text-sm text-gray-600 mt-1">
            {filteredData.length} of {masterMatrix.length} entries
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Filter */}
          <select
            value={filterConfidence}
            onChange={(e) => setFilterConfidence(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 font-medium hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="all">All ({masterMatrix.length})</option>
            <option value="high">High Confidence ({confidenceCounts.high})</option>
            <option value="medium">Medium Confidence ({confidenceCounts.medium})</option>
            <option value="unmatched">Unmatched ({confidenceCounts.unmatched})</option>
          </select>
          
          {/* Export Button */}
          <button
            onClick={downloadCSV}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            <Download size={18} />
            Export CSV
          </button>
        </div>
      </div>
      
      {/* Confidence Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-600 font-semibold text-sm">High Confidence</p>
          <p className="text-green-900 text-2xl font-bold mt-1">{confidenceCounts.high}</p>
        </div>
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-600 font-semibold text-sm">Medium Confidence</p>
          <p className="text-yellow-900 text-2xl font-bold mt-1">{confidenceCounts.medium}</p>
        </div>
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-gray-600 font-semibold text-sm">Unmatched</p>
          <p className="text-gray-900 text-2xl font-bold mt-1">{confidenceCounts.unmatched}</p>
        </div>
      </div>
      
      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gradient-to-r from-blue-50 to-blue-100 border-b border-gray-200">
              <th className="px-6 py-4 text-left font-semibold text-gray-900">Infra</th>
              <th className="px-6 py-4 text-left font-semibold text-gray-900">Server</th>
              <th className="px-6 py-4 text-left font-semibold text-gray-900">Installed App</th>
              <th className="px-6 py-4 text-left font-semibold text-gray-900">App Component</th>
              <th className="px-6 py-4 text-left font-semibold text-gray-900">Repo</th>
              <th className="px-6 py-4 text-center font-semibold text-gray-900">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row, idx) => {
              const confidencePercent = (row.confidence * 100).toFixed(0);
              const bgColor = row.confidence_level === 'high' 
                ? 'bg-green-50'
                : row.confidence_level === 'medium'
                ? 'bg-yellow-50'
                : 'bg-gray-50';
              
              return (
                <tr key={idx} className={`border-b border-gray-100 hover:${bgColor} transition-colors`}>
                  <td className="px-6 py-4">
                    <span className="font-medium text-gray-900">{getInfra(row) || '—'}</span>
                  </td>
                  <td className="px-6 py-4 text-gray-700">{getServer(row) || '—'}</td>
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900">{row.installed_app || '—'}</p>
                      <p className="text-xs text-gray-500 mt-1">{row.app_id || ''}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-700">{row.app_component || '—'}</td>
                  <td className="px-6 py-4">
                    <span className="text-gray-700 text-xs break-words max-w-xs inline-block">
                      {getRepo(row) ? getRepo(row).substring(0, 50) + (getRepo(row).length > 50 ? '...' : '') : '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className={`px-3 py-1 rounded-full font-bold text-white text-xs ${
                        row.confidence_level === 'high'
                          ? 'bg-green-600'
                          : row.confidence_level === 'medium'
                          ? 'bg-yellow-600'
                          : 'bg-gray-400'
                      }`}
                    >
                      {confidencePercent}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* Legend */}
      <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <h4 className="font-semibold text-gray-900 mb-3">Legend</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <span className="inline-block w-4 h-4 bg-green-600 rounded mr-2"></span>
            <span className="text-gray-700">High Confidence: 85%+ match</span>
          </div>
          <div>
            <span className="inline-block w-4 h-4 bg-yellow-600 rounded mr-2"></span>
            <span className="text-gray-700">Medium Confidence: 60-84% match</span>
          </div>
          <div>
            <span className="inline-block w-4 h-4 bg-gray-400 rounded mr-2"></span>
            <span className="text-gray-700">Unmatched: No correlation found</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MasterMatrix;
