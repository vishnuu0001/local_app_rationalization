import React, { useState, useEffect } from 'react';
import EmptyState from './EmptyState';
import { getDashboardData } from '../services/api';
import apiClient from '../services/api';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCard, setSelectedCard] = useState(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleReset = async () => {
    if (!window.confirm('Reset all data? This will clear the entire dashboard back to zero.')) return;
    try {
      setResetting(true);
      await apiClient.post('/reset');
      sessionStorage.removeItem('app_reset_done');
      await fetchDashboardData();
    } catch (err) {
      console.error('Reset failed:', err);
    } finally {
      setResetting(false);
    }
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await getDashboardData();
      setDashboardData(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const summary = dashboardData?.summary || {};
  const recommendations = dashboardData?.recommendations || [];
  
  // Extract nested data from infrastructure and code insights
  const infrastructureInsights = dashboardData?.data?.infrastructure_insights || {};
  const codeInsights = dashboardData?.data?.code_insights || {};
  
  const servers = infrastructureInsights?.dashboard_format?.server_app_mapping || [];
  const technologies = Object.keys(infrastructureInsights?.dashboard_format?.tech_stack || {});
  const deploymentFootprint = infrastructureInsights?.dashboard_format?.deployment_footprint || {};
  
  const programmingLanguages = Object.keys(codeInsights?.dashboard_format?.programming_languages || codeInsights?.programming_languages || {});
  const architectureComponents = codeInsights?.dashboard_format?.architecture_components || [];
  const internalDependencies = codeInsights?.dashboard_format?.internal_dependencies || {};

  return (
    <div className="min-h-screen bg-white">
      {/* Header Section */}
      <div className="border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50 px-12 py-10 relative">
        <h1 className="text-3xl font-bold text-gray-900">Assessment Dashboard</h1>
        <p className="text-gray-600 mt-3">Comprehensive infrastructure and application analysis</p>
        <button
          onClick={handleReset}
          disabled={resetting}
          title="Reset all data to zero"
          className="absolute top-4 right-6 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50 hover:border-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
        >
          {resetting ? (
            <>
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
              Resetting...
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 1 0 .49-4.95"/>
              </svg>
              Reset
            </>
          )}
        </button>
      </div>

      {/* Content Section */}
      <div className="px-12 py-10">
        {loading && (
          <div className="text-center py-10">
            <p className="text-gray-600">Loading dashboard data...</p>
          </div>
        )}

        {!loading && error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {!loading && !error && dashboardData && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-5 gap-6 mb-10">
              <SummaryCard
                title="Applications"
                value={summary.total_applications || 0}
                icon="💾"
                color="slate"
                onClick={() => setSelectedCard('applications')}
                isSelected={selectedCard === 'applications'}
              />
              <SummaryCard
                title="Servers"
                value={summary.total_servers || 0}
                icon="🖥️"
                color="blue"
                onClick={() => setSelectedCard('servers')}
                isSelected={selectedCard === 'servers'}
              />
              <SummaryCard
                title="Cloud Ready"
                value={`${summary.cloud_ready_percentage?.toFixed(1) || 0}%`}
                icon="☁️"
                color="emerald"
                onClick={() => setSelectedCard('cloudready')}
                isSelected={selectedCard === 'cloudready'}
              />
              <SummaryCard
                title="Risk Apps"
                value={summary.high_risk_applications || 0}
                icon="⚠️"
                color="amber"
                onClick={() => setSelectedCard('riskApps')}
                isSelected={selectedCard === 'riskApps'}
              />
            </div>

            {/* Detailed Card View */}
            {selectedCard && (
              <div className="mb-10 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-8">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-900">
                    {selectedCard === 'applications' && '💾 Applications Details'}
                    {selectedCard === 'servers' && '🖥️ Servers Details'}
                    {selectedCard === 'cloudready' && '☁️ Cloud Readiness Details'}
                    {selectedCard === 'riskApps' && '⚠️ High-Risk Applications'}
                  </h3>
                  <button
                    onClick={() => setSelectedCard(null)}
                    className="text-gray-600 hover:text-gray-900 text-2xl font-bold"
                  >
                    ✕
                  </button>
                </div>

                {selectedCard === 'applications' && (
                  <div className="grid grid-cols-1 gap-4">
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div className="bg-white p-4 rounded-lg border border-blue-200">
                        <p className="text-sm text-gray-600">Infrastructure (Corent)</p>
                        <p className="text-3xl font-bold text-blue-600">{summary.infrastructure_applications}</p>
                      </div>
                      <div className="bg-white p-4 rounded-lg border border-blue-200">
                        <p className="text-sm text-gray-600">Code Analysis (CAST)</p>
                        <p className="text-3xl font-bold text-blue-600">{summary.code_applications}</p>
                      </div>
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 mb-3">📋 Application List</h4>
                      <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto">
                        {servers.map((app, idx) => (
                          <div key={idx} className="bg-white p-3 rounded border border-gray-200 text-sm">
                            <p className="font-semibold text-gray-900">{app.app_id}</p>
                            <p className="text-gray-600 text-xs">{app.app_name || app.app_id}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {selectedCard === 'servers' && (
                  <div>
                    <h4 className="font-bold text-gray-900 mb-4">🖥️ Server & Application Mapping</h4>
                    <div className="grid grid-cols-1 gap-4 max-h-96 overflow-y-auto">
                      {servers.map((server, idx) => (
                        <div key={idx} className="bg-white p-4 rounded border border-gray-200">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <p className="font-bold text-gray-900">{server.app_id}</p>
                              <p className="text-sm text-gray-600">{server.app_name}</p>
                            </div>
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded font-semibold">Server</span>
                          </div>
                          <div className="text-sm text-gray-600 space-y-1">
                            <p>📍 <strong>{server.server}</strong></p>
                            <p>🖧 Type: {server.server_type}</p>
                            <p>🌍 Environment: {server.environment}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedCard === 'cloudready' && (
                  <div>
                    <h4 className="font-bold text-gray-900 mb-4">☁️ Cloud Readiness Breakdown</h4>
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      {servers.map((app) => {
                        const cloudClass = app.cloud_suitability?.toLowerCase() || 'unknown';
                        const colorMap = {
                          high: 'bg-emerald-100 text-emerald-800 border-emerald-300',
                          medium: 'bg-amber-100 text-amber-800 border-amber-300',
                          low: 'bg-red-100 text-red-800 border-red-300',
                          unknown: 'bg-gray-100 text-gray-800 border-gray-300'
                        };
                        return (
                          <div key={app.app_id} className={`p-4 rounded border ${colorMap[cloudClass] || colorMap.unknown}`}>
                            <p className="text-xs font-semibold mb-1">APP ID</p>
                            <p className="font-bold text-sm">{app.app_id}</p>
                            <p className="text-xs mt-2 font-semibold">{app.cloud_suitability || 'Not Rated'}</p>
                          </div>
                        );
                      })}
                    </div>
                    <div className="bg-white p-4 rounded border border-gray-200">
                      <p className="text-sm text-gray-600 mb-2"><strong>Overall Cloud Readiness: {summary.cloud_ready_percentage?.toFixed(1)}%</strong></p>
                      <div className="w-full bg-gray-300 rounded-full h-2">
                        <div 
                          className="bg-emerald-500 h-2 rounded-full" 
                          style={{width: `${summary.cloud_ready_percentage}%`}}
                        ></div>
                      </div>
                    </div>
                  </div>
                )}

                {selectedCard === 'riskApps' && (
                  <div>
                    <h4 className="font-bold text-gray-900 mb-4">⚠️ High-Risk Applications ({summary.high_risk_applications})</h4>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {servers.filter(app => 
                        app.cloud_suitability?.toLowerCase() === 'low' || 
                        (app.volume_external_dependencies && parseInt(app.volume_external_dependencies) > 15)
                      ).map((app, idx) => (
                        <div key={idx} className="bg-white p-4 rounded border-l-4 border-red-500">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <p className="font-bold text-gray-900">{app.app_id}</p>
                              <p className="text-sm text-gray-600">{app.app_name}</p>
                            </div>
                            <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded font-semibold">HIGH RISK</span>
                          </div>
                          <div className="text-sm text-gray-600 space-y-1">
                            <p>☁️ Cloud Suitability: <strong>{app.cloud_suitability || 'Unknown'}</strong></p>
                            <p>🔗 External Dependencies: <strong>{app.volume_external_dependencies || 0}</strong></p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}

        {/* Tabs */}
        {!loading && !error && dashboardData && (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="flex border-b border-gray-200 bg-gray-50">
              {['overview', 'infrastructure', 'code', 'recommendations'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 px-8 py-4 font-semibold transition-all text-center ${
                    activeTab === tab
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            <div className="p-12">
              {activeTab === 'overview' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-8">Overview</h2>
                  <div className="grid grid-cols-2 gap-6">
                    <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                      <h3 className="font-bold text-gray-900 mb-4">📊 Summary Statistics</h3>
                      <dl className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Total Applications:</dt>
                          <dd className="font-bold text-gray-900">{summary.total_applications}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Infrastructure Apps:</dt>
                          <dd className="font-bold text-gray-900">{summary.infrastructure_applications}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Code Analysis Apps:</dt>
                          <dd className="font-bold text-gray-900">{summary.code_applications}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Matched Applications:</dt>
                          <dd className="font-bold text-gray-900">{summary.matched_applications}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Match Percentage:</dt>
                          <dd className="font-bold text-gray-900">{summary.match_percentage?.toFixed(1)}%</dd>
                        </div>
                      </dl>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                      <h3 className="font-bold text-gray-900 mb-4">🎯 Data Quality</h3>
                      <dl className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Data Quality Score:</dt>
                          <dd className="font-bold text-emerald-600">{summary.data_quality_score?.toFixed(1)}%</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Unique Servers:</dt>
                          <dd className="font-bold text-gray-900">{summary.unique_servers}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Unique Technologies:</dt>
                          <dd className="font-bold text-gray-900">{summary.unique_technologies}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Programming Languages:</dt>
                          <dd className="font-bold text-gray-900">{summary.programming_languages}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-gray-600">Correlation Status:</dt>
                          <dd className="font-bold text-blue-600">{summary.correlation_status}</dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'infrastructure' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-8">Infrastructure Analysis</h2>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <h3 className="font-bold text-gray-900 mb-4">🖥️ Server & Application Mapping</h3>
                      {servers && servers.length > 0 ? (
                        <div className="space-y-3 max-h-96 overflow-y-auto">
                          {servers.map((server, idx) => (
                            <div key={idx} className="text-sm bg-gray-50 p-3 rounded border border-gray-200">
                              <p className="font-semibold text-gray-900">{server.app_id || 'N/A'}</p>
                              <p className="text-gray-600 text-xs mt-1">📍 {server.server || 'Unknown'}</p>
                              <p className="text-gray-600 text-xs">🖧 {server.server_type || 'Unknown'}</p>
                              <p className="text-gray-600 text-xs">☁️ {server.cloud_suitability || 'Not rated'}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-500">No server data available</p>
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 mb-4">🛠️ Technologies</h3>
                      {technologies && technologies.length > 0 ? (
                        <div className="space-y-2">
                          {technologies.map((tech, idx) => {
                            const count = infrastructureInsights?.dashboard_format?.tech_stack?.[tech] || 0;
                            return (
                              <div key={idx} className="flex justify-between items-center bg-gray-50 p-3 rounded border border-gray-200 text-sm">
                                <span className="text-gray-900 font-medium">{tech}</span>
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold">{count}</span>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-gray-500">No technology data available</p>
                      )}
                    </div>
                  </div>
                  <div className="mt-6">
                    <h3 className="font-bold text-gray-900 mb-4">📈 Deployment Footprint</h3>
                    <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
                      {Object.keys(deploymentFootprint).length > 0 ? (
                        <div className="grid grid-cols-2 gap-4">
                          {Object.entries(deploymentFootprint).map(([key, value]) => (
                            <div key={key} className="text-sm">
                              <p className="text-gray-600 font-semibold">{key}</p>
                              <p className="text-gray-900">{value} application{value !== 1 ? 's' : ''}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-500">No deployment footprint data available</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'code' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-8">Code Analysis</h2>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <h3 className="font-bold text-gray-900 mb-4">🔤 Programming Languages</h3>
                      {programmingLanguages && programmingLanguages.length > 0 ? (
                        <div className="space-y-2">
                          {programmingLanguages.map((lang, idx) => {
                            const count = codeInsights?.programming_languages?.[lang] || 0;
                            return (
                              <div key={idx} className="flex justify-between items-center bg-gray-50 p-3 rounded border border-gray-200 text-sm">
                                <span className="text-gray-900 font-medium">{lang}</span>
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold">{count}</span>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-gray-500">No language data available</p>
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 mb-4">📦 Architecture Components</h3>
                      {architectureComponents && architectureComponents.length > 0 ? (
                        <div className="space-y-3 max-h-72 overflow-y-auto">
                          {architectureComponents.slice(0, 5).map((comp, idx) => (
                            <div key={idx} className="text-sm bg-gray-50 p-3 rounded border border-gray-200">
                              <p className="font-semibold text-gray-900">{comp.app_id}</p>
                              <p className="text-gray-600 text-xs mt-1">💻 {comp.language || 'Unknown'}</p>
                              <p className="text-gray-600 text-xs">📐 Type: {comp.type || 'Unknown'}</p>
                              <p className="text-gray-600 text-xs">🔗 Coupling: {comp.component_coupling || 'N/A'}</p>
                            </div>
                          ))}
                          {architectureComponents.length > 5 && (
                            <p className="text-gray-500 text-sm">+{architectureComponents.length - 5} more components</p>
                          )}
                        </div>
                      ) : (
                        <p className="text-gray-500">No component data available</p>
                      )}
                    </div>
                  </div>
                  <div className="mt-6">
                    <h3 className="font-bold text-gray-900 mb-4">🔗 External Dependencies</h3>
                    <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
                      {Object.keys(internalDependencies).length > 0 ? (
                        <div className="space-y-3 max-h-60 overflow-y-auto">
                          {Object.entries(internalDependencies).map(([appId, deps]) => (
                            <div key={appId} className="flex justify-between items-center text-sm">
                              <span className="text-gray-700 font-medium">{deps.app_name || appId}</span>
                              <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded text-xs font-semibold">
                                {deps.dependency_count} dependencies
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-500">No dependency data available</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'recommendations' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-8">Key Recommendations</h2>
                  {recommendations && recommendations.length > 0 ? (
                    <div className="space-y-4">
                      {recommendations.map((rec, idx) => {
                        const priorityColors = {
                          high: 'bg-red-50 border-red-200 text-red-800',
                          medium: 'bg-amber-50 border-amber-200 text-amber-800',
                          low: 'bg-green-50 border-green-200 text-green-800',
                        };
                        const priorityIcons = {
                          high: '🔴',
                          medium: '🟡',
                          low: '🟢',
                        };
                        return (
                          <div
                            key={idx}
                            className={`border rounded-lg p-6 ${priorityColors[rec.priority] || priorityColors.low}`}
                          >
                            <div className="flex items-start">
                              <span className="text-2xl mr-4">{priorityIcons[rec.priority] || '•'}</span>
                              <div className="flex-1">
                                <p className="font-bold mb-2">
                                  [{rec.priority.toUpperCase()}] Recommendation {idx + 1}
                                </p>
                                <p className="text-sm">{rec.recommendation}</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <EmptyState
                      title="No Recommendations"
                      description="Recommendations will appear as analysis data is available."
                      icon="💡"
                    />
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {!loading && (
          <div className="mt-10 bg-gradient-to-r from-slate-50 to-gray-50 border border-gray-200 rounded-lg p-8">
            <h3 className="text-lg font-bold text-gray-900 mb-4">📋 Dashboard Information</h3>
            <p className="text-gray-700 mb-4">
              This dashboard provides real-time insights from your infrastructure and code analysis data. 
              {dashboardData && !dashboardData.data?.summary?.matched_applications && (
                <>
                  <br />
                  <strong>Note:</strong> For enhanced matching, upload both Corent infrastructure files and CAST code analysis files to correlate applications across your environment.
                </>
              )}
            </p>
            <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
              <div>
                <p className="font-bold text-gray-900 mb-2">✅ Available Data Sources:</p>
                <ul className="space-y-1">
                  {dashboardData?.data?.data_sources?.corent_populated && (
                    <li>✓ Infrastructure (Corent) data</li>
                  )}
                  {dashboardData?.data?.data_sources?.cast_populated && (
                    <li>✓ Code Analysis (CAST) data</li>
                  )}
                  {dashboardData?.data?.data_sources?.correlation_available && (
                    <li>✓ Correlation data</li>
                  )}
                </ul>
              </div>
              <div>
                <p className="font-bold text-gray-900 mb-2">📊 To add more data:</p>
                <ul className="space-y-1">
                  <li>• CAST files: Go to CAST Analysis tab</li>
                  <li>• Corent files: Go to Corent Analysis tab</li>
                  <li>• Run correlation: Go to Correlation Layer tab</li>
                </ul>
              </div>
            </div>
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
};

const SummaryCard = ({ title, value, icon, color, onClick, isSelected }) => {
  const colors = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  };

  return (
    <div 
      onClick={onClick}
      className={`${colors[color]} border-2 rounded-lg p-6 transition-all cursor-pointer ${
        isSelected 
          ? 'shadow-lg border-2 scale-105 ring-2 ring-offset-2 ring-blue-400' 
          : 'hover:shadow-md hover:scale-102'
      }`}
    >
      <div className="text-3xl mb-3">{icon}</div>
      <p className="text-sm font-semibold opacity-75">{title}</p>
      <p className="text-3xl font-bold mt-2">{value}</p>
    </div>
  );
};

export default Dashboard;
