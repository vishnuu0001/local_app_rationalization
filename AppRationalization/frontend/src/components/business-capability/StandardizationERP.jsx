import React, { useState, useCallback, useEffect } from 'react';
import { TrendingDown, ArrowRight } from 'lucide-react';
import api from '../../services/api';

const StandardizationERP = () => {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    const cached = localStorage.getItem('cache_standardization');
    if (cached) { try { setAnalysisData(JSON.parse(cached)); } catch (_) {} }
  }, []);

  const fetchAnalysis = useCallback(async () => {
    try {
      setGenerating(true);
      setLoading(true);
      const response = await api.get('/standardization-analysis');
      if (response.data && response.data.analysis) {
        setAnalysisData(response.data.analysis);
        localStorage.setItem('cache_standardization', JSON.stringify(response.data.analysis));
      }
    } catch (err) {
      console.error('Failed to load standardization analysis data:', err);
    } finally {
      setGenerating(false);
      setLoading(false);
    }
  }, []);

  const handleGenerate = () => fetchAnalysis();

  const handleClear = async () => {
    if (!window.confirm('Clear all standardization data? This will also reset Dashboard infrastructure stats.')) return;
    try {
      setClearing(true);
      await api.delete('/standardization-analysis/clear');
      setAnalysisData(null);
      localStorage.removeItem('cache_standardization');
    } catch (err) {
      console.error('Clear failed:', err);
    } finally {
      setClearing(false);
    }
  };

  const infra = analysisData?.infrastructure_analysis || {};
  const tech = analysisData?.technology_standardization || {};
  const code = analysisData?.code_analysis || {};
  const llm  = analysisData?.llm_insights || {};
  const hasData = !!analysisData;
  const hasLLM  = llm?.available === true;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
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
              <button onClick={handleGenerate} disabled={generating || clearing}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm">
                {generating ? (<><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg> Generating...</>) : (<><svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg> Generate</>)}
              </button>
              <button onClick={handleClear} disabled={generating || clearing}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm">
                {clearing ? (<><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg> Clearing...</>) : (<><svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg> Clear</>)}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <svg className="animate-spin h-10 w-10 text-purple-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <p className="text-gray-500 text-sm font-medium">Generating analysis…</p>
          </div>
        )}
        {!loading && !hasData && (
          <div className="bg-white rounded-xl shadow-md p-10 border border-dashed border-gray-300 text-center text-gray-600">
            <p className="text-lg font-semibold mb-2">No standardization data yet</p>
            <p className="text-sm">Click <strong>Generate</strong> to load the latest Corent / CAST analysis.</p>
          </div>
        )}

        {!loading && hasData && (
          <>
            <div className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <span className="text-3xl">&#8592;</span> Current Infrastructure State
              </h2>
              <div className="bg-white rounded-xl shadow-md p-8 border-l-4 border-red-500">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-6 border border-red-200">
                    <div className="text-4xl font-bold text-red-600 mb-2">{infra.total_applications ?? 0}</div>
                    <div className="text-gray-700 font-semibold mb-3">Total Applications</div>
                    <p className="text-sm text-gray-600">Scattered across {infra.unique_servers ?? 0} infrastructure servers</p>
                  </div>
                  <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-6 border border-orange-200">
                    <div className="text-4xl font-bold text-orange-600 mb-2">{tech.database_engines ? Object.keys(tech.database_engines).length : 0}</div>
                    <div className="text-gray-700 font-semibold mb-3">Database Engines</div>
                    <p className="text-sm text-gray-600">Top engines by usage across the estate</p>
                  </div>
                  <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-6 border border-yellow-200">
                    <div className="text-4xl font-bold text-yellow-600 mb-2">{tech.operating_systems ? Object.keys(tech.operating_systems).length : 0}</div>
                    <div className="text-gray-700 font-semibold mb-3">OS Variants</div>
                    <p className="text-sm text-gray-600">Distinct operating systems observed</p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
                    <div className="text-4xl font-bold text-blue-600 mb-2">{code.cloud_readiness_percentage || '0%'}</div>
                    <div className="text-gray-700 font-semibold mb-3">Cloud-Ready</div>
                    <p className="text-sm text-gray-600">{code.source_code_availability || '0%'} have source code access</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-center my-8">
              <div className="flex flex-col items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg shadow-lg">
                <ArrowRight size={32} className="rotate-90" />
                <span className="font-semibold">After Standardization &amp; Consolidation</span>
              </div>
            </div>

            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <span className="text-3xl">&#8594;</span> Recommended Consolidated State
              </h2>
              <div className="bg-white rounded-xl shadow-md p-8 border-l-4 border-emerald-500">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg p-6 border border-emerald-200">
                    <div className="text-4xl font-bold text-emerald-600 mb-2">5</div>
                    <div className="text-gray-700 font-semibold mb-3">Standardized Platforms</div>
                    <p className="text-sm text-gray-600">Consolidate to 5 primary infrastructure platforms for unified management</p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
                    <div className="text-4xl font-bold text-blue-600 mb-2">3-4</div>
                    <div className="text-gray-700 font-semibold mb-3">Database Standards</div>
                    <p className="text-sm text-gray-600">Standardized database engines with cloud-ready architecture</p>
                  </div>
                  <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border border-purple-200">
                    <div className="text-4xl font-bold text-purple-600 mb-2">2</div>
                    <div className="text-gray-700 font-semibold mb-3">OS Standards</div>
                    <p className="text-sm text-gray-600">Unified OS standards with consistent patching and versioning</p>
                  </div>
                  <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-lg p-6 border border-indigo-200">
                    <div className="text-4xl font-bold text-indigo-600 mb-2">2</div>
                    <div className="text-gray-700 font-semibold mb-3">Specialized Teams</div>
                    <p className="text-sm text-gray-600">Infrastructure and consolidation specialists focused on cloud readiness</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-12 bg-white rounded-xl shadow-md p-8 border-l-4 border-green-500">
              <h3 className="text-2xl font-bold text-gray-900 mb-6">Business Value &amp; ROI</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex gap-4">
                  <span className="text-2xl">🎯</span>
                  <div>
                    <h4 className="font-semibold text-gray-900">Infrastructure Simplification</h4>
                    <p className="text-sm text-gray-600 mt-1">Reduce platform complexity from {infra.total_servers ?? 0} to 5 standardized infrastructure endpoints</p>
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
                    <p className="text-sm text-gray-600 mt-1">Modern architecture supports rapid cloud adoption</p>
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

            {/* ── LLM Insights Panel ── */}
            {hasLLM && (
              <div className="mt-12 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl shadow-md p-8 border border-indigo-200">
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-3xl">🤖</span>
                  <div>
                    <h3 className="text-2xl font-bold text-indigo-900">AI-Powered Recommendations</h3>
                    <p className="text-sm text-indigo-600">Generated by LLM model: <strong>{llm.model_used}</strong></p>
                  </div>
                </div>

                {llm.executive_summary && (
                  <div className="mb-6 bg-white rounded-lg p-5 border border-indigo-100 shadow-sm">
                    <h4 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span>📋</span> Executive Summary
                    </h4>
                    <p className="text-gray-700 leading-relaxed">{llm.executive_summary}</p>
                  </div>
                )}

                {llm.standardization_strategy && (
                  <div className="mb-6 bg-white rounded-lg p-5 border border-indigo-100 shadow-sm">
                    <h4 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span>🎯</span> Standardization Strategy
                    </h4>
                    <p className="text-gray-700 leading-relaxed">{llm.standardization_strategy}</p>
                  </div>
                )}

                {llm.top_recommendations?.length > 0 && (
                  <div className="mb-6">
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <span>✅</span> Top LLM Recommendations
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {llm.top_recommendations.map((rec, i) => (
                        <div key={i} className="bg-white rounded-lg p-4 border border-indigo-100 shadow-sm">
                          <div className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">{rec.priority || i + 1}</span>
                            <div>
                              <p className="font-semibold text-gray-800">{rec.title}</p>
                              {rec.action && <p className="text-sm text-indigo-700 mt-1"><strong>Action:</strong> {rec.action}</p>}
                              {rec.rationale && <p className="text-sm text-gray-600 mt-1">{rec.rationale}</p>}
                              {rec.timeline && <p className="text-xs text-emerald-600 mt-1 font-medium">⏱ {rec.timeline}</p>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {llm.consolidation_roadmap?.length > 0 && (
                  <div className="mb-6">
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <span>🗺️</span> Consolidation Roadmap
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {llm.consolidation_roadmap.map((phase, i) => (
                        <div key={i} className="bg-white rounded-lg p-4 border-t-4 border-indigo-500 shadow-sm">
                          <p className="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-1">Phase {phase.phase} · {phase.duration}</p>
                          <p className="font-semibold text-gray-800 mb-2">{phase.title}</p>
                          {phase.focus && <p className="text-sm text-gray-600 mb-2">{phase.focus}</p>}
                          {phase.expected_outcome && <p className="text-xs text-emerald-700 bg-emerald-50 rounded px-2 py-1">{phase.expected_outcome}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {llm.risk_highlights?.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <span>⚠️</span> Risk Highlights
                    </h4>
                    <ul className="space-y-2">
                      {llm.risk_highlights.map((risk, i) => (
                        <li key={i} className="flex items-start gap-2 bg-white rounded-lg px-4 py-3 border border-amber-200 shadow-sm">
                          <span className="text-amber-500 mt-0.5 flex-shrink-0">▲</span>
                          <span className="text-sm text-gray-700">{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default StandardizationERP;
