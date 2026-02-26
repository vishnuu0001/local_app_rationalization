import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import {
  getUploadedFiles,
  correlateInfraAndCode,
  deleteFile,
} from '../services/api';
import { toast } from 'react-toastify';

const Analysis = () => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedInfra, setSelectedInfra] = useState(null);
  const [selectedCode, setSelectedCode] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const filesResponse = await getUploadedFiles();
        setFiles(filesResponse.data.files || []);
      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleDeleteFile = async (fileId) => {
    if (!window.confirm('Are you sure you want to delete this file?')) {
      return;
    }

    setDeleting(fileId);
    try {
      await deleteFile(fileId);
      setFiles(files.filter(f => f.file_id !== fileId));
      
      // Clear selections if deleted file was selected
      const deletedFile = files.find(f => f.file_id === fileId);
      if (deletedFile) {
        if (deletedFile.type === 'Infrastructure' && selectedInfra) {
          const infra = files.find(f => f.file_id === fileId);
          if (infra && infra.id === selectedInfra) {
            setSelectedInfra(null);
          }
        } else if (deletedFile.type === 'Code Analysis' && selectedCode) {
          const code = files.find(f => f.file_id === fileId);
          if (code && code.id === selectedCode) {
            setSelectedCode(null);
          }
        }
      }
      
      toast.success('File deleted successfully');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete file');
    } finally {
      setDeleting(null);
    }
  };

  const handleCorrelate = async () => {
    if (!selectedInfra || !selectedCode) {
      toast.error('Please select both infrastructure and code analysis files');
      return;
    }

    setAnalyzing(true);

    try {
      const result = await correlateInfraAndCode(selectedInfra, selectedCode);
      setAnalysisResult(result.data);
      toast.success('Correlation analysis completed successfully');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-blue-600 border-t-transparent"></div>
      </div>
    );
  }

  const hasInfraFiles = files.filter((f) => f.type === 'Infrastructure').length > 0;
  const hasCodeFiles = files.filter((f) => f.type === 'Code Analysis').length > 0;

  return (
    <div className="min-h-screen bg-white">
      {/* Header Section */}
      <div className="border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50 px-12 py-10">
        <h1 className="text-3xl font-bold text-gray-900">Correlation Layer</h1>
        <p className="text-gray-600 mt-3">Correlate infrastructure and code intelligence to map applications</p>
      </div>

      {/* Content Section */}
      <div className="px-12 py-10">
        {/* Empty State */}
        {!hasInfraFiles && !hasCodeFiles && (
          <div className="text-center py-20">
            <div className="text-6xl mb-4">📤</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">No Files Available</h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Upload infrastructure discovery (Corent) and CAST analysis files first in their respective sections before running correlation analysis.
            </p>
          </div>
        )}

        {/* File Selection */}
        {(hasInfraFiles || hasCodeFiles) && (
          <div className="grid grid-cols-2 gap-8 mb-12">
            {/* Infrastructure Selection */}
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="bg-gradient-to-r from-slate-50 to-gray-50 px-8 py-6 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Infrastructure Analysis</h2>
                <p className="text-gray-600 text-sm mt-2">Select infrastructure discovery file</p>
              </div>

              <div className="p-8 space-y-3">
                {files
                  .filter((f) => f.type === 'Infrastructure')
                  .map((file) => (
                    <div
                      key={file.file_id}
                      className={`flex items-center p-4 border-2 rounded-lg transition-all ${
                        selectedInfra === file.id
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="infrastructure"
                        value={file.id}
                        checked={selectedInfra === file.id}
                        onChange={(e) => setSelectedInfra(parseInt(e.target.value))}
                        className="mr-4 accent-blue-600 cursor-pointer"
                      />
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900">
                          {file.filename}
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {file.uploaded_at}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-semibold">
                          {file.status}
                        </span>
                        <button
                          onClick={() => handleDeleteFile(file.file_id)}
                          disabled={deleting === file.file_id}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Delete file"
                        >
                          {deleting === file.file_id ? (
                            <div className="h-5 w-5 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                          ) : (
                            <X size={20} />
                          )}
                        </button>
                      </div>
                    </div>
                  ))}

                {!hasInfraFiles && (
                  <div className="text-center py-12 text-gray-500">
                    <p className="text-sm">No infrastructure files uploaded yet</p>
                  </div>
                )}
              </div>
            </div>

            {/* Code Analysis Selection */}
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="bg-gradient-to-r from-slate-50 to-gray-50 px-8 py-6 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Code Intelligence</h2>
                <p className="text-gray-600 text-sm mt-2">Select code analysis file</p>
              </div>

              <div className="p-8 space-y-3">
                {files
                  .filter((f) => f.type === 'Code Analysis')
                  .map((file) => (
                    <div
                      key={file.file_id}
                      className={`flex items-center p-4 border-2 rounded-lg transition-all ${
                        selectedCode === file.id
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="code"
                        value={file.id}
                        checked={selectedCode === file.id}
                        onChange={(e) => setSelectedCode(parseInt(e.target.value))}
                        className="mr-4 accent-blue-600 cursor-pointer"
                      />
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900">
                          {file.filename}
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {file.uploaded_at}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-semibold">
                          {file.status}
                        </span>
                        <button
                          onClick={() => handleDeleteFile(file.file_id)}
                          disabled={deleting === file.file_id}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Delete file"
                        >
                          {deleting === file.file_id ? (
                            <div className="h-5 w-5 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                          ) : (
                            <X size={20} />
                          )}
                        </button>
                      </div>
                    </div>
                  ))}

                {!hasCodeFiles && (
                  <div className="text-center py-12 text-gray-500">
                    <p className="text-sm">No code analysis files uploaded yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Correlation Button */}
        {(hasInfraFiles || hasCodeFiles) && (
          <button
            onClick={handleCorrelate}
            disabled={!selectedInfra || !selectedCode || analyzing}
            className={`w-full font-semibold py-4 rounded-lg transition-all duration-300 flex items-center justify-center gap-2 text-lg mb-12 ${
              selectedInfra && selectedCode && !analyzing
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {analyzing ? (
              <>
                <div className="animate-spin rounded-full h-6 w-6 border-2 border-white border-t-transparent"></div>
                <span>Analyzing and Correlating...</span>
              </>
            ) : (
              <>
                <span>🔗</span>
                <span>Correlate Files & Start Analysis</span>
              </>
            )}
          </button>
        )}

        {/* Analysis Results */}
        {analysisResult && (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gradient-to-r from-slate-50 to-gray-50 px-8 py-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">Correlation Results</h2>
            </div>

            <div className="p-8">
              {/* Summary Stats */}
              <div className="grid grid-cols-4 gap-6 mb-10">
                <StatCard
                  title="Match Score"
                  value={`${analysisResult.match_score}%`}
                  icon="📊"
                  color="blue"
                />
                <StatCard
                  title="Matched Pairs"
                  value={analysisResult.summary.matched_pairs}
                  icon="🔗"
                  color="emerald"
                />
                <StatCard
                  title="Servers"
                  value={analysisResult.summary.total_servers}
                  icon="🖥️"
                  color="slate"
                />
                <StatCard
                  title="Applications"
                  value={analysisResult.summary.total_applications}
                  icon="📦"
                  color="purple"
                />
              </div>

              {/* Correlations Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-6 py-4 text-left font-semibold text-gray-900">Server</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-900">Type</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-900">Application</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-900">Match Score</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-900">Matched On</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysisResult.correlations.map((corr, idx) => (
                      <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 font-semibold text-gray-900">
                          {corr.server}
                        </td>
                        <td className="px-6 py-4">
                          <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-xs font-semibold">
                            {corr.server_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-semibold text-gray-900">
                          {corr.application}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-24 bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-emerald-500 h-2 rounded-full transition-all"
                                style={{
                                  width: `${corr.match_score}%`,
                                }}
                              ></div>
                            </div>
                            <span className="font-bold text-gray-900 min-w-12">
                              {corr.match_score}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-gray-600 text-xs">
                          {corr.match_criteria.join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon, color }) => {
  const colors = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
  };

  return (
    <div className={`${colors[color]} border rounded-lg p-6 text-center`}>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-sm font-semibold opacity-75">{title}</div>
      <div className="text-3xl font-bold mt-2">{value}</div>
    </div>
  );
};

export default Analysis;


