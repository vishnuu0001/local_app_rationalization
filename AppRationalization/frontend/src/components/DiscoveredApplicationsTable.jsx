import React, { useState, useEffect, useCallback } from 'react';
import { getDiscoveredApplications } from '../services/api';
import { ChevronDown, Search, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

const DiscoveredApplicationsTable = ({ infrastructureFileId, onClose }) => {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [expandedRow, setExpandedRow] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [pagination, setPagination] = useState({});

  const columns = [
    { key: 'app_id', label: 'APP ID', width: '100px' },
    { key: 'name', label: 'Name', width: '200px' },
    { key: 'business_owner', label: 'Business Owner', width: '150px' },
    { key: 'architecture_type', label: 'Architecture Type', width: '150px' },
    { key: 'platform_host', label: 'Platform Host', width: '150px' },
    { key: 'application_type', label: 'Application Type', width: '150px' },
    { key: 'install_type', label: 'Install Type', width: '120px' },
    { key: 'capabilities', label: 'Capabilities', width: '200px' },
  ];

  const fetchDiscoveredApplications = useCallback(async (page = 1) => {
    setLoading(true);
    setError(null);
    try {
      const response = await getDiscoveredApplications(infrastructureFileId, page, perPage);
      setApplications(response.data.applications || []);
      setPagination(response.data.pagination || {});
      setCurrentPage(page);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load discovered applications');
    } finally {
      setLoading(false);
    }
  }, [infrastructureFileId, perPage]);

  useEffect(() => {
    fetchDiscoveredApplications(1);
  }, [fetchDiscoveredApplications]);

  const filteredApplications = applications.filter(app =>
    Object.values(app).some(val =>
      val && val.toString().toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const sortedApplications = [...filteredApplications].sort((a, b) => {
    const aVal = a[sortField] || '';
    const bVal = b[sortField] || '';
    
    if (typeof aVal === 'string') {
      return sortOrder === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }
    
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
  });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const handleExportCSV = () => {
    const headers = columns.map(c => c.label).join(',');
    const rows = sortedApplications.map(app =>
      columns.map(col => {
        const value = app[col.key] || '';
        return `"${String(value).replace(/"/g, '""')}"`;
      }).join(',')
    );
    
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'discovered-applications.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handlePreviousPage = () => {
    if (pagination.has_prev) {
      fetchDiscoveredApplications(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (pagination.has_next) {
      fetchDiscoveredApplications(currentPage + 1);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
        <p className="text-red-800 font-semibold">Error</p>
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Corent Analysis</h2>
            <p className="text-sm text-gray-600 mt-1">
              {sortedApplications.length} of {applications.length} applications
            </p>
          </div>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            <Download size={18} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search applications..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 text-left w-10">
                <span className="text-gray-600 font-semibold">#</span>
              </th>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="px-4 py-3 text-left bg-gray-50 border-r border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
                  style={{ minWidth: col.width }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-gray-700 font-semibold whitespace-nowrap">{col.label}</span>
                    {sortField === col.key && (
                      <ChevronDown
                        size={16}
                        className={`text-blue-600 transition-transform ${
                          sortOrder === 'desc' ? 'rotate-180' : ''
                        }`}
                      />
                    )}
                  </div>
                </th>
              ))}
              <th className="px-4 py-3 text-center w-12 bg-gray-50">
                <span className="text-gray-600 font-semibold">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedApplications.map((app, idx) => (
              <React.Fragment key={app.id}>
                <tr className="border-b border-gray-200 hover:bg-blue-50 transition-colors">
                  <td className="px-4 py-3 text-gray-600 font-medium">{idx + 1}</td>
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className="px-4 py-3 text-gray-700 border-r border-gray-100"
                      style={{ minWidth: col.width }}
                    >
                      <span className="block truncate" title={app[col.key] || ''}>
                        {app[col.key] || '-'}
                      </span>
                    </td>
                  ))}
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => setExpandedRow(expandedRow === app.id ? null : app.id)}
                      className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-gray-200 transition-colors"
                      title="View details"
                    >
                      <ChevronDown
                        size={18}
                        className={`text-gray-600 transition-transform ${
                          expandedRow === app.id ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                  </td>
                </tr>

                {/* Expanded Details Row */}
                {expandedRow === app.id && (
                  <tr className="bg-blue-50 border-b border-gray-200">
                    <td colSpan={columns.length + 2} className="px-6 py-4">
                      <div className="grid grid-cols-2 gap-4">
                        {columns.map((col) => (
                          <div key={col.key} className="border-l-2 border-blue-300 pl-3">
                            <p className="text-xs font-semibold text-gray-600 uppercase">{col.label}</p>
                            <p className="text-sm text-gray-800 mt-1 break-words">
                              {app[col.key] || 'N/A'}
                            </p>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {sortedApplications.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No applications found matching your search.</p>
        </div>
      )}

      {/* Footer */}
      <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
        <div className="flex justify-between items-center mb-4">
          <p className="text-sm text-gray-600">
            Page {pagination.page || 1} of {pagination.pages || 1} | Total: {pagination.total || 0} applications
          </p>
          <div className="flex items-center gap-2">
            <select
              value={perPage}
              onChange={(e) => setPerPage(parseInt(e.target.value))}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
        </div>
        
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePreviousPage}
              disabled={!pagination.has_prev}
              className={`flex items-center gap-1 px-3 py-2 rounded-lg font-medium transition-colors ${
                pagination.has_prev
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <button
              onClick={handleNextPage}
              disabled={!pagination.has_next}
              className={`flex items-center gap-1 px-3 py-2 rounded-lg font-medium transition-colors ${
                pagination.has_next
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              Next
              <ChevronRight size={16} />
            </button>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-800 rounded-lg font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DiscoveredApplicationsTable;
