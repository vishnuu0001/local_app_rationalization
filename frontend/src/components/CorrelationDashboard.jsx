import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { getCorrelationData, startCorrelation } from '../services/api';
import { useAppStore } from '../store';
import CorentDashboard from './dashboards/CorentDashboard';
import CASTDashboard from './dashboards/CASTDashboard';
import CorrelationLayer from './dashboards/CorrelationLayer';
import MasterMatrix from './dashboards/MasterMatrix';
import CorrelationStatistics from './dashboards/CorrelationStatistics';
import { Zap, BarChart3, Database, Trash2 } from 'lucide-react';

const CorrelationDashboard = () => {
  const [loading, setLoading] = useState(false);
  const [correlating, setCorrelating] = useState(false);
  const [correlationData, setCorrelationData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const correlationDataVersion = useAppStore((state) => state.correlationDataVersion);
  
  // Clear correlation data when a file is deleted
  useEffect(() => {
    setCorrelationData(null);
  }, [correlationDataVersion]);
  
  // Fetch latest correlation on mount
  useEffect(() => {
    fetchLatestCorrelation();
  }, []);
  
  const fetchLatestCorrelation = async () => {
    setLoading(true);
    try {
      const response = await getCorrelationData();
      if (response.data.status === 'success') {
        setCorrelationData(response.data);
        setActiveTab('overview');
      }
    } catch (error) {
      console.log('No previous correlation found - ready to create new one');
    }
    setLoading(false);
  };
  
  const handleStartCorrelation = async () => {
    setCorrelating(true);
    try {
      const response = await startCorrelation();
      
      if (response.data.status === 'success') {
        toast.success(
          `Correlation completed! ${response.data.summary.matched_count}/${response.data.summary.total_count} items matched`,
          { autoClose: 5000 }
        );
        
        // Fetch the complete correlation data
        await fetchLatestCorrelation();
      } else {
        toast.error(response.data.message || 'Correlation failed');
      }
    } catch (error) {
      toast.error(error.response?.data?.message || 'Correlation failed. Ensure both Corent Infrastructure PDFs and CAST Code Analysis PDFs are uploaded.');
      console.error('Correlation error:', error);
    } finally {
      setCorrelating(false);
    }
  };
  
  const handleClearDashboard = () => {
    if (!correlationData) {
      toast.info('No data to clear');
      return;
    }
    
    if (window.confirm('Are you sure you want to clear all correlation data? This cannot be undone.')) {
      setCorrelationData(null);
      setActiveTab('overview');
      toast.success('Correlation data cleared successfully');
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600 text-lg">Loading correlation data...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 flex items-center gap-3">
                <BarChart3 size={40} className="text-blue-600" />
                Infrastructure & Code Analysis Correlation
              </h1>
              <p className="text-gray-600 mt-2">
                Correlate Corent infrastructure data with CAST code analysis to identify application deployments
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={handleStartCorrelation}
                disabled={correlating}
                className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all ${
                  correlating
                    ? 'bg-gray-700 text-white cursor-not-allowed opacity-70'
                    : 'bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:shadow-lg active:shadow-sm'
                }`}
              >
                {correlating ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                    <span>Correlating...</span>
                  </>
                ) : (
                  <>
                    <Zap size={20} />
                    <span>Correlate Files & Start Analysis</span>
                  </>
                )}
              </button>
              
              <button
                onClick={handleClearDashboard}
                disabled={!correlationData || correlating}
                className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all ${
                  !correlationData || correlating
                    ? 'bg-gray-300 text-gray-600 cursor-not-allowed opacity-60'
                    : 'bg-gradient-to-r from-red-600 to-red-700 text-white hover:shadow-lg active:shadow-sm'
                }`}
              >
                <Trash2 size={20} />
                <span>Clear</span>
              </button>
            </div>
          </div>
          
          {/* Status */}
          {correlationData && (
            <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
              <p className="text-emerald-800 font-medium">
                ✓ Last correlation: {new Date(correlationData.correlation.created_at).toLocaleString()}
              </p>
              <p className="text-emerald-700 text-sm mt-1">
                {correlationData.correlation.matched_count} of {correlationData.correlation.total_count} items matched 
                ({correlationData.correlation.match_percentage}%)
              </p>
            </div>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {!correlationData ? (
          <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
            <Database size={64} className="mx-auto mb-6 text-gray-400" />
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Ready to Correlate</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              Upload Corent Infrastructure PDFs and CAST Code Analysis PDFs, 
              then click "Correlate Files & Start Analysis" to begin the correlation process.
            </p>
            <p className="text-gray-500 text-sm">
              The system will match applications based on APP ID as the primary key, 
              with fallback to app name matching for unmatched items.
            </p>
          </div>
        ) : (
          <>
            {/* Tab Navigation */}
            <div className="bg-white rounded-t-xl border-b border-gray-200">
              <div className="flex overflow-x-auto">
                {[
                  { id: 'overview', label: 'Overview', icon: null },
                  { id: 'corent', label: 'Corent Dashboard', icon: null },
                  { id: 'cast', label: 'CAST Dashboard', icon: null },
                  { id: 'correlation', label: 'Correlation Layer', icon: null },
                  { id: 'matrix', label: 'Master Matrix', icon: null },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-6 py-4 font-semibold border-b-2 transition-colors whitespace-nowrap ${
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Tab Content */}
            <div className="bg-white rounded-b-xl border-x border-b border-gray-200 p-6">
              {activeTab === 'overview' && (
                <CorrelationStatistics data={correlationData} />
              )}
              
              {activeTab === 'corent' && (
                <CorentDashboard data={correlationData.corent_dashboard} />
              )}
              
              {activeTab === 'cast' && (
                <CASTDashboard data={correlationData.cast_dashboard} />
              )}
              
              {activeTab === 'correlation' && (
                <CorrelationLayer data={correlationData.correlation_layer} />
              )}
              
              {activeTab === 'matrix' && (
                <MasterMatrix data={correlationData} />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CorrelationDashboard;
