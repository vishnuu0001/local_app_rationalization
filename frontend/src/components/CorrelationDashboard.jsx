import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { getCorrelationData, startCorrelation, getOllamaStatus, getWorkspaceColumnUpdates, getLlmAnalysis, getWorkspaceRuns, rerunLlmAnalysis, getAppsByCloudGroup, getAppDetail, getWorkspaceCastRows, getWorkspaceCorentRows, getWorkspaceBizRows } from '../services/api';
import { useAppStore } from '../store';
import CorentDashboard from './dashboards/CorentDashboard';
import CASTDashboard from './dashboards/CASTDashboard';
import CorrelationLayer from './dashboards/CorrelationLayer';
import MasterMatrix from './dashboards/MasterMatrix';
import CorrelationStatistics from './dashboards/CorrelationStatistics';
import { Zap, BarChart3, Database, Trash2, Brain, CheckCircle, Circle, Loader, X, ChevronLeft, ExternalLink } from 'lucide-react';

// â”€â”€ Pipeline step labels shown while the backend is running â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const PIPELINE_STEPS = [
  { id: 'predict',     label: 'Predicting null values with AI (CORENT, CAST, Industry)' },
  { id: 'consolidate', label: 'Building Consolidated DB with composite key' },
  { id: 'correlate',   label: 'Running correlation matching' },
  { id: 'analyse',     label: 'Generating LLM correlation insights' },
];

// â”€â”€ Small helper: render each pipeline step â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const PipelineStepList = ({ activeStep }) => (
  <ul className="mt-4 space-y-2 text-sm text-left max-w-lg mx-auto">
    {PIPELINE_STEPS.map((step, idx) => {
      const stepIdx = PIPELINE_STEPS.findIndex(s => s.id === activeStep);
      const done = idx < stepIdx;
      const active = idx === stepIdx;
      return (
        <li key={step.id} className="flex items-center gap-2">
          {done ? (
            <CheckCircle size={16} className="text-green-500 shrink-0" />
          ) : active ? (
            <Loader size={16} className="text-blue-500 animate-spin shrink-0" />
          ) : (
            <Circle size={16} className="text-gray-400 shrink-0" />
          )}
          <span className={active ? 'text-blue-700 font-medium' : done ? 'text-green-700' : 'text-gray-500'}>
            {step.label}
          </span>
        </li>
      );
    })}
  </ul>
);

// â”€â”€ LLM Analysis panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

// -- Helper: infer which cloud tier a roadmap phase title corresponds to ------
const phaseToTier = (title = '') => {
  const t = title.toLowerCase();
  if (t.includes('high')) return 'High';
  if (t.includes('medium') || t.includes('moderate')) return 'Medium';
  if (t.includes('low')) return 'Low';
  return null;
};

// -- Drill-Down Modal (L2 = cloud group list, L3 = single app detail) ---------
const AppDrillDownModal = ({ open, mode, title, tier, appId, onClose }) => {
  const [groupData, setGroupData]               = useState(null);
  const [groupLoading, setGroupLoading]         = useState(false);
  const [appDetail, setAppDetail]               = useState(null);
  const [appDetailLoading, setAppDetailLoading] = useState(false);
  const [drillAppId, setDrillAppId]             = useState(null);

  useEffect(() => {
    if (!open || mode !== 'group') return;
    setGroupData(null); setDrillAppId(null); setAppDetail(null);
    setGroupLoading(true);
    getAppsByCloudGroup()
      .then(res => setGroupData(res.data.groups?.[tier] ?? []))
      .catch(() => setGroupData([]))
      .finally(() => setGroupLoading(false));
  }, [open, mode, tier]);

  useEffect(() => {
    const id = mode === 'app' ? appId : drillAppId;
    if (!open || !id) { if (!drillAppId && mode !== 'app') setAppDetail(null); return; }
    setAppDetail(null);
    setAppDetailLoading(true);
    getAppDetail(id)
      .then(res => setAppDetail(res.data.app))
      .catch(() => setAppDetail(null))
      .finally(() => setAppDetailLoading(false));
  }, [open, mode, appId, drillAppId]);

  if (!open) return null;
  const isL3 = mode === 'app' || !!drillAppId;

  const FieldRow = ({ label, value }) =>
    value ? (
      <div className="flex gap-2 text-xs py-1 border-b border-gray-100 last:border-0">
        <span className="text-gray-500 w-48 shrink-0">{label}</span>
        <span className="text-gray-800 font-medium">{value}</span>
      </div>
    ) : null;

  const renderAppDetail = (app) => {
    if (!app) return <p className="text-gray-400 text-sm italic">No data available.</p>;
    return (
      <div className="space-y-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <p className="text-xs font-bold text-blue-600 uppercase mb-2">Identity</p>
          <FieldRow label="App ID"           value={app.app_id} />
          <FieldRow label="App Name"         value={app.app_name} />
          <FieldRow label="Business Owner"   value={app.industry_business_owner} />
          <FieldRow label="Application Type" value={app.industry_application_type} />
          <FieldRow label="Install Type"     value={app.industry_install_type} />
          <FieldRow label="Capabilities"     value={app.industry_capabilities} />
        </div>
        <div className="bg-purple-50 rounded-lg p-4">
          <p className="text-xs font-bold text-purple-600 uppercase mb-2">CAST — Code Analysis</p>
          <FieldRow label="Cloud Suitability"    value={app.cast_cloud_suitability} />
          <FieldRow label="Architecture"         value={app.cast_application_architecture} />
          <FieldRow label="Programming Language" value={app.cast_programming_language} />
          <FieldRow label="Component Coupling"   value={app.cast_component_coupling} />
          <FieldRow label="Code Design"          value={app.cast_code_design} />
          <FieldRow label="Source Code Avail."   value={app.cast_source_code_availability} />
          <FieldRow label="Ext. Dependencies"    value={app.cast_volume_external_dependencies} />
        </div>
        <div className="bg-green-50 rounded-lg p-4">
          <p className="text-xs font-bold text-green-600 uppercase mb-2">CORENT — Infrastructure</p>
          <FieldRow label="Cloud Suitability"    value={app.corent_cloud_suitability} />
          <FieldRow label="Architecture"         value={app.corent_architecture_type} />
          <FieldRow label="Platform / Host"      value={app.corent_platform_host} />
          <FieldRow label="Operating System"     value={app.corent_operating_system} />
          <FieldRow label="Environment"          value={app.corent_environment} />
          <FieldRow label="Install Type"         value={app.corent_install_type} />
          <FieldRow label="DB Engine"            value={app.corent_db_engine} />
          <FieldRow label="App Stability"        value={app.corent_application_stability} />
          <FieldRow label="COTS / Non-COTS"      value={app.corent_app_cots_vs_non_cots} />
          <FieldRow label="Mainframe Dep."       value={app.corent_mainframe_dependency} />
          <FieldRow label="HA/DR Requirements"   value={app.corent_ha_dr_requirements} />
          <FieldRow label="Deployment Geography" value={app.corent_deployment_geography} />
          <FieldRow label="Server Name"          value={app.corent_server_name} />
        </div>
        {app.llm_annotation && (
          <div className="bg-amber-50 rounded-lg p-4">
            <p className="text-xs font-bold text-amber-600 uppercase mb-1">AI Annotation</p>
            <p className="text-amber-800 text-sm">{app.llm_annotation}</p>
          </div>
        )}
        {app.ai_predicted_columns?.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-bold text-gray-500 uppercase mb-1">AI-Predicted Fields ({app.ai_predicted_columns.length})</p>
            <div className="flex flex-wrap gap-1">
              {app.ai_predicted_columns.map(col => (
                <span key={col} className="px-2 py-0.5 text-xs bg-violet-100 text-violet-700 rounded-full">{col}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-10 px-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl mb-10">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            {mode === 'group' && drillAppId && (
              <button onClick={() => { setDrillAppId(null); setAppDetail(null); }}
                className="p-1 rounded hover:bg-gray-100 text-gray-500 mr-1" title="Back to group list">
                <ChevronLeft size={18} />
              </button>
            )}
            <h2 className="font-bold text-gray-800 text-lg">
              {mode === 'group' && drillAppId ? `${drillAppId} — App Detail` : title}
            </h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><X size={18} /></button>
        </div>
        <div className="px-6 py-5 max-h-[70vh] overflow-y-auto">
          {isL3 && (
            appDetailLoading
              ? <div className="flex justify-center py-16"><Loader size={32} className="animate-spin text-blue-500" /></div>
              : renderAppDetail(appDetail)
          )}
          {!isL3 && (
            groupLoading
              ? <div className="flex justify-center py-16"><Loader size={32} className="animate-spin text-blue-500" /></div>
              : groupData?.length > 0
                ? (
                  <div className="overflow-x-auto">
                    <p className="text-sm text-gray-500 mb-3">
                      {groupData.length} application{groupData.length !== 1 ? 's' : ''} — click a row to see full details
                    </p>
                    <table className="min-w-full text-xs border-collapse">
                      <thead className="bg-gray-100 sticky top-0">
                        <tr>{['#','App ID','App Name','CAST Cloud','CORENT Cloud','Architecture','OS / Platform','Env','Type'].map(h => (
                          <th key={h} className="px-3 py-2 text-left font-medium text-gray-600 border border-gray-200 whitespace-nowrap">{h}</th>
                        ))}</tr>
                      </thead>
                      <tbody>
                        {groupData.map((app, i) => (
                          <tr key={app.app_id ?? i} className="hover:bg-blue-50 cursor-pointer" onClick={() => setDrillAppId(app.app_id)}>
                            <td className="px-3 py-2 border border-gray-200 text-gray-400">{i + 1}</td>
                            <td className="px-3 py-2 border border-gray-200 font-mono text-blue-600">
                              <span className="flex items-center gap-1">{app.app_id} <ExternalLink size={10} /></span>
                            </td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-700 max-w-[160px] truncate">{app.app_name ?? '—'}</td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-600">{app.cast_cloud_suitability ?? '—'}</td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-600">{app.corent_cloud_suitability ?? '—'}</td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-600">{app.cast_application_architecture ?? '—'}</td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-600">{app.corent_operating_system ?? app.corent_platform_host ?? '—'}</td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-600">{app.corent_environment ?? '—'}</td>
                            <td className="px-3 py-2 border border-gray-200 text-gray-600">{app.industry_application_type ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
                : <p className="text-gray-400 text-sm italic py-8 text-center">No applications in this group.</p>
          )}
        </div>
      </div>
    </div>
  );
};
const PAGE_SIZE_PRIO  = 25;
const PAGE_SIZE_NOTES = 30;

const exportCSV = (headers, rows, filename) => {
  const escape = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const lines = [headers.map(escape).join(','), ...rows.map(r => r.map(escape).join(','))];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
};

const LLMAnalysisPanel = ({ llmAnalysis, pipelineStats, onRegenerate, rerunning, onDrillDown }) => {
  const [prioSearch, setPrioSearch]   = useState('');
  const [prioPage,   setPrioPage]     = useState(1);
  const [notesSearch, setNotesSearch] = useState('');
  const [notesPage,   setNotesPage]   = useState(1);

  if (!llmAnalysis) return null;
  if (!llmAnalysis.available) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-2">
          <Brain size={20} className="text-amber-600" />
          <h3 className="font-semibold text-amber-800">AI Analysis Unavailable</h3>
        </div>
        <p className="text-amber-700 text-sm">{llmAnalysis.summary}</p>
        <p className="text-amber-600 text-xs mt-2">
          Start Ollama on localhost and pull a model (e.g.{' '}
          <code className="bg-amber-100 px-1 rounded">ollama pull mistral</code>) to enable AI analysis.
        </p>
      </div>
    );
  }

  // Analysis record exists but content is empty — offer regeneration
  const isEmpty = !llmAnalysis.summary && !llmAnalysis.executive_summary;
  if (isEmpty) {
    return (
      <div className="space-y-4">
        {/* Pipeline stats banner still shown */}
        {pipelineStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Apps Consolidated', value: pipelineStats.total_apps ?? pipelineStats.total_consolidated_apps ?? '—' },
              { label: 'AI Columns Filled', value: pipelineStats.total_ai_fills ?? '—' },
              { label: 'Apps with AI Fill', value: pipelineStats.apps_with_ai_fill ?? '—' },
              { label: 'LLM Model Used', value: llmAnalysis.model_used ?? 'N/A' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-violet-50 border border-violet-200 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-violet-700">{value}</div>
                <div className="text-xs text-violet-600 mt-1">{label}</div>
              </div>
            ))}
          </div>
        )}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 text-center">
          <Brain size={32} className="text-blue-400 mx-auto mb-3" />
          <h3 className="font-semibold text-blue-800 mb-1">AI Analysis Content Not Available</h3>
          <p className="text-blue-600 text-sm mb-4">
            The previous analysis run did not generate content (likely a timeout). Click below to regenerate using existing consolidated data — no need to re-run the full pipeline.
          </p>
          <button
            onClick={onRegenerate}
            disabled={rerunning}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {rerunning ? <Loader size={15} className="animate-spin" /> : <Brain size={15} />}
            {rerunning ? 'Generating AI Analysis…' : 'Regenerate AI Analysis'}
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      {/* Pipeline stats banner */}
      {pipelineStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Apps Consolidated', value: pipelineStats.total_apps ?? pipelineStats.total_consolidated_apps ?? '—' },
            { label: 'AI Columns Filled', value: pipelineStats.total_ai_fills ?? '—' },
            { label: 'Apps with AI Fill', value: pipelineStats.apps_with_ai_fill ?? '—' },
            { label: 'LLM Model Used', value: llmAnalysis.model_used ?? 'N/A' },
          ].map(({ label, value }) => (
            <div key={label} className="bg-violet-50 border border-violet-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-violet-700">{value}</div>
              <div className="text-xs text-violet-600 mt-1">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Executive Summary */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h4 className="font-semibold text-blue-800 mb-2 flex items-center gap-2">
          <Brain size={16} /> Executive Summary
        </h4>
        <p className="text-blue-700 text-sm leading-relaxed">{llmAnalysis.summary}</p>
      </div>

      {/* Cloud Readiness */}
      {llmAnalysis.cloud_readiness && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
          <h4 className="font-semibold text-emerald-800 mb-2">Cloud Readiness Insights</h4>
          <p className="text-emerald-700 text-sm leading-relaxed">{llmAnalysis.cloud_readiness}</p>
        </div>
      )}

      {/* Risk Observations + Recommendations side by side */}
      <div className="grid md:grid-cols-2 gap-4">
        {llmAnalysis.risk_observations?.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5">
            <h4 className="font-semibold text-red-800 mb-3">Risk Observations</h4>
            <ul className="space-y-2">
              {llmAnalysis.risk_observations.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm text-red-700">
                  <span className="text-red-400 font-bold shrink-0">{i + 1}.</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {llmAnalysis.recommendations?.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <h4 className="font-semibold text-green-800 mb-3">Recommendations</h4>
            <ul className="space-y-2">
              {llmAnalysis.recommendations.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm text-green-700">
                  <span className="text-green-500 font-bold shrink-0">{i + 1}.</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Correlation quality */}
      {llmAnalysis.correlation_quality && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
          <h4 className="font-semibold text-gray-700 mb-2">Data Quality Assessment</h4>
          <p className="text-gray-600 text-sm">{llmAnalysis.correlation_quality}</p>
        </div>
      )}

      {/* Technical Debt Summary */}
      {llmAnalysis.technical_debt_summary && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-5">
          <h4 className="font-semibold text-orange-800 mb-2">Technical Debt Summary</h4>
          <p className="text-orange-700 text-sm leading-relaxed">{llmAnalysis.technical_debt_summary}</p>
        </div>
      )}

      {/* Migration Roadmap */}
      {llmAnalysis.migration_roadmap?.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
          <h4 className="font-semibold text-indigo-800 mb-3">Migration Roadmap</h4>
          <div className="space-y-3">
            {llmAnalysis.migration_roadmap.map((phase, i) => {
              const tier = phaseToTier(phase.title);
              return (
                <div
                  key={i}
                  className={`flex gap-3 items-start rounded-lg p-2 -mx-2 transition-colors ${tier ? 'cursor-pointer hover:bg-indigo-100' : ''}`}
                  onClick={tier ? () => onDrillDown({ mode: 'group', tier, title: `${phase.title} — ${tier} Suitability Apps` }) : undefined}
                  title={tier ? `Click to see all ${tier} cloud-suitability apps` : undefined}
                >
                  <div className="shrink-0 w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                    {phase.phase ?? i + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-indigo-800 text-sm flex items-center gap-2">
                      {phase.title}
                      {phase.app_count ? <span className="text-indigo-500 font-normal">({phase.app_count} apps)</span> : null}
                      {tier && <ExternalLink size={12} className="text-indigo-400" />}
                    </p>
                    {phase.rationale && <p className="text-indigo-700 text-xs mt-0.5">{phase.rationale}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Modernization Priorities */}
      {llmAnalysis.modernization_priorities?.length > 0 && (() => {
        const term = prioSearch.toLowerCase();
        const filtered = llmAnalysis.modernization_priorities.filter(item =>
          !term ||
          (item.app_id   && item.app_id.toLowerCase().includes(term))   ||
          (item.app_name && item.app_name.toLowerCase().includes(term)) ||
          (item.rationale && item.rationale.toLowerCase().includes(term)) ||
          (item.recommended_action && item.recommended_action.toLowerCase().includes(term))
        );
        const totalPages = Math.ceil(filtered.length / PAGE_SIZE_PRIO);
        const page = Math.min(prioPage, Math.max(1, totalPages));
        const visible = filtered.slice((page - 1) * PAGE_SIZE_PRIO, page * PAGE_SIZE_PRIO);
        return (
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h4 className="font-semibold text-gray-700">
                Top Modernization Priorities
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({filtered.length} / {llmAnalysis.modernization_priorities.length} apps)
                </span>
              </h4>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Search by app ID, name, action…"
                  value={prioSearch}
                  onChange={e => { setPrioSearch(e.target.value); setPrioPage(1); }}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm w-56 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <button
                  onClick={() => exportCSV(
                    ['#', 'App ID', 'App Name', 'Recommended Action', 'Rationale'],
                    filtered.map(item => [item.priority ?? '', item.app_id ?? '', item.app_name ?? '', item.recommended_action ?? '', item.rationale ?? ''])
                    , 'modernization_priorities.csv')}
                  className="text-xs px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
                >CSV</button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm border-collapse">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 border border-gray-200">#</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 border border-gray-200">App ID</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 border border-gray-200">App Name</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 border border-gray-200">Action</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600 border border-gray-200">Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((item, i) => {
                    const actionColor = {
                      Retire: 'bg-red-100 text-red-700',
                      Rehost: 'bg-green-100 text-green-700',
                      Replatform: 'bg-blue-100 text-blue-700',
                      Refactor: 'bg-yellow-100 text-yellow-700',
                      Replace: 'bg-purple-100 text-purple-700',
                    }[item.recommended_action] ?? 'bg-gray-100 text-gray-700';
                    return (
                      <tr
                        key={item.app_id || i}
                        className="hover:bg-blue-50 cursor-pointer"
                        onClick={() => item.app_id && onDrillDown({ mode: 'app', appId: item.app_id, title: `${item.app_id} — App Detail` })}
                      >
                        <td className="px-3 py-2 border border-gray-200 text-center font-bold text-gray-500">{item.priority ?? ((page - 1) * PAGE_SIZE_PRIO + i + 1)}</td>
                        <td className="px-3 py-2 border border-gray-200 font-mono text-xs text-blue-600">
                          <span className="flex items-center gap-1">{item.app_id} <ExternalLink size={10} /></span>
                        </td>
                        <td className="px-3 py-2 border border-gray-200 text-gray-700">{item.app_name ?? '—'}</td>
                        <td className="px-3 py-2 border border-gray-200">
                          {item.recommended_action && (
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${actionColor}`}>
                              {item.recommended_action}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 border border-gray-200 text-gray-600 text-xs">{item.rationale}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-2 text-sm text-gray-500">
                <span>Page {page} of {totalPages}</span>
                <div className="flex gap-1">
                  <button onClick={() => setPrioPage(p => Math.max(1, p - 1))}    disabled={page <= 1}          className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">‹</button>
                  <button onClick={() => setPrioPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">›</button>
                </div>
                <span>{filtered.length} apps</span>
              </div>
            )}
          </div>
        );
      })()}

      {/* Per-app notes table */}
      {llmAnalysis.per_app_notes && Object.keys(llmAnalysis.per_app_notes).length > 0 && (() => {
        const allEntries = Object.entries(llmAnalysis.per_app_notes)
          .filter(([k]) => !['app_id','application_id','id'].includes(k.toLowerCase()));
        const term = notesSearch.toLowerCase();
        const filtered = allEntries.filter(([appId, note]) =>
          !term ||
          appId.toLowerCase().includes(term) ||
          (typeof note === 'string' && note.toLowerCase().includes(term))
        );
        const totalPages = Math.ceil(filtered.length / PAGE_SIZE_NOTES);
        const page = Math.min(notesPage, Math.max(1, totalPages));
        const visible = filtered.slice((page - 1) * PAGE_SIZE_NOTES, page * PAGE_SIZE_NOTES);
        return (
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h4 className="font-semibold text-gray-700">
                Per-Application Annotations
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({filtered.length} / {allEntries.length} apps)
                </span>
              </h4>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Search by app ID or annotation…"
                  value={notesSearch}
                  onChange={e => { setNotesSearch(e.target.value); setNotesPage(1); }}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm w-56 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <button
                  onClick={() => exportCSV(
                    ['App ID', 'Annotation'],
                    filtered.map(([appId, note]) => [appId, note])
                    , 'per_app_annotations.csv')}
                  className="text-xs px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
                >CSV</button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm border-collapse">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-600 border border-gray-200 w-40">App ID</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-600 border border-gray-200">Annotation</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map(([appId, note]) => (
                    <tr
                      key={appId}
                      className="hover:bg-blue-50 cursor-pointer"
                      onClick={() => onDrillDown({ mode: 'app', appId, title: `${appId} — App Detail` })}
                    >
                      <td className="px-4 py-2 border border-gray-200 font-mono text-xs text-blue-600">
                        <span className="flex items-center gap-1">{appId} <ExternalLink size={10} /></span>
                      </td>
                      <td className="px-4 py-2 border border-gray-200 text-gray-700">{note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-2 text-sm text-gray-500">
                <span>Page {page} of {totalPages}</span>
                <div className="flex gap-1">
                  <button onClick={() => setNotesPage(p => Math.max(1, p - 1))}     disabled={page <= 1}          className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">‹</button>
                  <button onClick={() => setNotesPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">›</button>
                </div>
                <span>{filtered.length} apps</span>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
};

// ── Workspace Prediction Panel ────────────────────────────────────────────────
// Shows file-copy status, per-source LLM fill stats, and column traceability.
const WorkspacePredictionPanel = ({ workspaceData, columnUpdates, updatedRowsData = { cast: [], corent: [], biz: [] } }) => {
  if (!workspaceData) {
    return (
      <div className="text-center text-gray-500 py-16">
        <Database size={48} className="mx-auto mb-4 text-gray-300" />
        <p className="text-lg font-medium text-gray-400 mb-2">No workspace data yet</p>
        <p className="text-sm text-gray-400">
          Click <strong>"Correlate Files &amp; Start Analysis"</strong> to copy the source Excel files
          and run the full AI pipeline.
        </p>
      </div>
    );
  }

  const FILES = [
    { label: 'CASTReport.xlsx',          source: 'CAST',     icon: '⚙️',  rows: workspaceData.cast_rows,   predicted: workspaceData.cells_predicted?.CAST     ?? 0 },
    { label: 'CORENTReport.xlsx',        source: 'CORENT',   icon: '🖥️',  rows: workspaceData.corent_rows, predicted: workspaceData.cells_predicted?.CORENT   ?? 0 },
    { label: 'Business_Templates.xlsx',  source: 'Business', icon: '📊',  rows: workspaceData.biz_rows,    predicted: workspaceData.cells_predicted?.Business ?? 0 },
  ];

  // Group column updates: { source → { column_name → count } }
  const updatesBySource = columnUpdates.reduce((acc, u) => {
    if (!acc[u.source]) acc[u.source] = {};
    acc[u.source][u.column_name] = (acc[u.source][u.column_name] ?? 0) + 1;
    return acc;
  }, {});

  const SOURCE_BADGE = {
    CAST:     'bg-blue-100 text-blue-700',
    CORENT:   'bg-green-100 text-green-700',
    Business: 'bg-violet-100 text-violet-700',
  };

  return (
    <div className="space-y-6">
      {/* Run summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Run ID',            value: workspaceData.run_id,                           color: 'blue'    },
          { label: 'Matched Apps',      value: workspaceData.matched_count,                    color: 'green'   },
          { label: 'AI Cells Filled',   value: workspaceData.cells_predicted?.total ?? 0,      color: 'violet'  },
          { label: 'Match Rate',        value: `${workspaceData.match_pct ?? 0}%`,             color: 'emerald' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`bg-${color}-50 border border-${color}-200 rounded-lg p-4 text-center`}>
            <div className={`text-2xl font-bold text-${color}-700`}>{value}</div>
            <div className={`text-xs text-${color}-600 mt-1`}>{label}</div>
          </div>
        ))}
      </div>

      {/* Per-file cards */}
      <div>
        <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Database size={16} /> Files Copied &amp; Enriched → backend/data/UpdatedData/
        </h3>
        <div className="grid md:grid-cols-3 gap-4">
          {FILES.map(({ label, source, icon, rows, predicted }) => (
            <div key={source} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{icon}</span>
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{label}</p>
                </div>
              </div>
              <div className="space-y-1 text-sm mb-3">
                <div className="flex justify-between">
                  <span className="text-gray-500">Rows loaded into DB</span>
                  <span className="font-medium text-gray-800">{rows}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">AI cells filled</span>
                  <span className={`font-medium ${predicted > 0 ? 'text-violet-600' : 'text-gray-400'}`}>{predicted}</span>
                </div>
              </div>
              {/* Column breakdown */}
              {updatesBySource[source] && Object.keys(updatesBySource[source]).length > 0 && (
                <div className="border-t border-gray-100 pt-3">
                  <p className="text-xs font-medium text-gray-500 mb-2">Columns AI-predicted:</p>
                  <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                    {Object.entries(updatesBySource[source])
                      .sort(([, a], [, b]) => b - a)
                      .map(([col, count]) => (
                        <div key={col} className="flex justify-between text-xs">
                          <span className="text-gray-600 truncate mr-2">{col}</span>
                          <span className="text-violet-600 font-mono shrink-0">{count} rows</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
              {(!updatesBySource[source] || Object.keys(updatesBySource[source]).length === 0) && predicted === 0 && (
                <p className="text-xs text-gray-400 italic mt-2">No null cells — all values already present.</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Column update traceability table */}
      {columnUpdates.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Brain size={16} /> Column Update Traceability ({columnUpdates.length} cells AI-filled)
          </h3>
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {['File', 'App ID', 'Row', 'Column Updated', 'Original Value', 'AI Predicted Value', 'Confidence', 'Model'].map(h => (
                    <th key={h} className="px-3 py-2 text-left font-medium text-gray-600 border-b border-gray-200 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {columnUpdates.slice(0, 300).map((u, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-1.5">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${SOURCE_BADGE[u.source] ?? 'bg-gray-100 text-gray-600'}`}>
                        {u.source}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 font-mono text-gray-600">{u.app_id ?? '—'}</td>
                    <td className="px-3 py-1.5 text-gray-400">{u.row_index}</td>
                    <td className="px-3 py-1.5 font-medium text-gray-700">{u.column_name}</td>
                    <td className="px-3 py-1.5 text-gray-400 italic max-w-[120px] truncate">{u.original_value ?? 'null'}</td>
                    <td className="px-3 py-1.5 text-gray-800 max-w-[160px] truncate">{u.predicted_value}</td>
                    <td className="px-3 py-1.5 text-gray-500">{u.confidence != null ? `${(u.confidence * 100).toFixed(0)}%` : '—'}</td>
                    <td className="px-3 py-1.5 text-gray-400 font-mono">{u.llm_model ? u.llm_model.split(':')[0] : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {columnUpdates.length > 300 && (
              <div className="px-4 py-2 bg-gray-50 text-xs text-gray-500 border-t border-gray-200">
                Showing first 300 of {columnUpdates.length} updates
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Updated Rows per-row summary ─────────────────────────────── */}
      {(() => {
        const allUpdatedRows = [
          ...updatedRowsData.cast.map(r => ({ ...r, _source: 'CAST' })),
          ...updatedRowsData.corent.map(r => ({ ...r, _source: 'CORENT' })),
          ...updatedRowsData.biz.map(r => ({ ...r, _source: 'Industry' })),
        ];
        if (allUpdatedRows.length === 0) return null;
        return (
          <div>
            <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Brain size={16} /> Updated Rows — AI-Filled Summary ({allUpdatedRows.length} rows)
            </h3>
            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="min-w-full text-xs">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    {['#', 'Source', 'App ID', 'Columns Updated by AI', '# Cols'].map(h => (
                      <th key={h} className="px-3 py-2 text-left font-medium text-gray-600 border-b border-gray-200 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {allUpdatedRows.map((row, i) => {
                    const info = row.updated_rows ?? {};
                    const cols = info.updated_columns ?? [];
                    return (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-3 py-1.5 text-gray-400">{i + 1}</td>
                        <td className="px-3 py-1.5">
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${SOURCE_BADGE[row._source] ?? SOURCE_BADGE['Business'] ?? 'bg-gray-100 text-gray-600'}`}>
                            {row._source}
                          </span>
                        </td>
                        <td className="px-3 py-1.5 font-mono text-gray-700 font-medium">
                          {info.app_id ?? row.app_id ?? '—'}
                        </td>
                        <td className="px-3 py-2 max-w-xs">
                          <div className="flex flex-wrap gap-1">
                            {cols.map(col => (
                              <span key={col} className="inline-flex items-center px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 text-[10px] font-medium">
                                {col}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-1.5 text-violet-600 font-mono font-semibold">{cols.length}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })()}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
const CorrelationDashboard = () => {
  const [loading, setLoading] = useState(false);
  const [correlating, setCorrelating] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [drillDown, setDrillDown] = useState(null); // { mode, tier, appId, title } | null
  const [correlationStep, setCorrelationStep] = useState(null);  // pipeline step for progress UI
  const [correlationData, setCorrelationData] = useState(null);
  const [llmAnalysis, setLlmAnalysis] = useState(null);
  const [pipelineStats, setPipelineStats] = useState(null);
  const [workspaceData, setWorkspaceData] = useState(null);    // workspace run stats
  const [columnUpdates, setColumnUpdates] = useState([]);      // per-cell traceability
  const [updatedRowsData, setUpdatedRowsData] = useState({ cast: [], corent: [], biz: [] });
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const correlationDataVersion = useAppStore((state) => state.correlationDataVersion);

  // Clear correlation data when a file is deleted
  useEffect(() => {
    setCorrelationData(null);
    setLlmAnalysis(null);
    setPipelineStats(null);
    setWorkspaceData(null);
    setColumnUpdates([]);
    setUpdatedRowsData({ cast: [], corent: [], biz: [] });
  }, [correlationDataVersion]);

  // Fetch latest correlation + Ollama status on mount
  useEffect(() => {
    fetchLatestCorrelation();
    fetchOllamaStatus();
  }, []);

  const fetchOllamaStatus = async () => {
    try {
      const res = await getOllamaStatus();
      setOllamaStatus(res.data?.ollama ?? null);
    } catch {
      setOllamaStatus({ available: false });
    }
  };

  const handleRerunAnalysis = async () => {
    setRerunning(true);
    try {
      const res = await rerunLlmAnalysis();
      if (res.data.status === 'success') {
        const a = res.data.analysis;
        setLlmAnalysis(a);
        setPipelineStats(prev => ({
          ...(prev ?? {}),
          total_apps: a.total_apps_analyzed,
        }));
        toast.success('AI Analysis regenerated successfully!');
      } else {
        toast.error(res.data.message ?? 'Failed to regenerate AI analysis.');
      }
    } catch (err) {
      toast.error(err?.response?.data?.message ?? 'Failed to regenerate AI analysis.');
    } finally {
      setRerunning(false);
    }
  };

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

    // Restore LLM analysis from DB (independent of whether correlation loaded)
    try {
      const llmRes = await getLlmAnalysis();
      if (llmRes.data.status === 'success') {
        const a = llmRes.data.analysis;
        setLlmAnalysis(a);
        // Reconstruct pipeline stats banner from stored analysis metadata
        setPipelineStats(prev => ({
          ...(prev ?? {}),
          total_apps:       a.total_apps_analyzed,
          total_ai_fills:   a.total_predictions_used,
          apps_with_ai_fill: prev?.apps_with_ai_fill ?? a.total_apps_analyzed,
        }));
      }
    } catch {
      // No prior analysis — fine, leave llmAnalysis null
    }

    // Restore workspace stats (for the Workspace tab and apps_with_ai_fill)
    try {
      const runsRes = await getWorkspaceRuns(1);
      const latestRun = runsRes.data?.runs?.[0] ?? null;
      if (latestRun) {
        const totalPredicted = (latestRun.cast_predicted ?? 0)
          + (latestRun.corent_predicted ?? 0)
          + (latestRun.biz_predicted ?? 0);
        setWorkspaceData({
          run_id:         latestRun.id,
          matched_count:  latestRun.matched_count,
          match_pct:      latestRun.match_pct,
          cast_rows:      latestRun.cast_rows,
          corent_rows:    latestRun.corent_rows,
          biz_rows:       latestRun.biz_rows,
          cells_predicted: {
            CAST:     latestRun.cast_predicted ?? 0,
            CORENT:   latestRun.corent_predicted ?? 0,
            Business: latestRun.biz_predicted ?? 0,
            total:    totalPredicted,
          },
        });
        setPipelineStats(prev => ({
          ...(prev ?? {}),
          total_ai_fills: totalPredicted,
        }));
        // Fetch column traceability for restored workspace run
        try {
          const colRes = await getWorkspaceColumnUpdates(latestRun.id);
          setColumnUpdates(colRes.data?.updates ?? []);
        } catch { /* non-critical */ }
        // Fetch per-row updated_rows summary for all three sources
        try {
          const [castRes, corentRes, bizRes] = await Promise.all([
            getWorkspaceCastRows(latestRun.id),
            getWorkspaceCorentRows(latestRun.id),
            getWorkspaceBizRows(latestRun.id),
          ]);
          setUpdatedRowsData({
            cast:   (castRes.data?.rows   ?? []).filter(r => r.updated_rows),
            corent: (corentRes.data?.rows ?? []).filter(r => r.updated_rows),
            biz:    (bizRes.data?.rows    ?? []).filter(r => r.updated_rows),
          });
        } catch { /* non-critical */ }
      }
    } catch {
      // No workspace runs yet — fine
    }

    setLoading(false);
  };

  const handleStartCorrelation = async () => {
    setCorrelating(true);
    setCorrelationStep('copy');

    // Advance step indicators via timeouts (purely UX — actual work is on backend)
    const stepTimers = [
      setTimeout(() => setCorrelationStep('predict'),     3000),
      setTimeout(() => setCorrelationStep('consolidate'), 8000),
      setTimeout(() => setCorrelationStep('correlate'),   14000),
      setTimeout(() => setCorrelationStep('analyse'),     20000),
    ];

    try {
      const response = await startCorrelation();

      stepTimers.forEach(clearTimeout);
      setCorrelationStep(null);

      if (response.data.status === 'success') {
        const { summary, llm_analysis, pipeline, workspace } = response.data;

        setLlmAnalysis(llm_analysis ?? null);
        setPipelineStats(pipeline ?? null);
        setWorkspaceData(workspace ?? null);

        // Fetch column-level update traceability for the Workspace tab
        if (workspace?.run_id) {
          try {
            const colRes = await getWorkspaceColumnUpdates(workspace.run_id);
            setColumnUpdates(colRes.data?.updates ?? []);
          } catch (e) {
            console.warn('Could not fetch workspace column updates:', e);
          }
          // Fetch per-row updated_rows summary for all three sources
          try {
            const [castRes, corentRes, bizRes] = await Promise.all([
              getWorkspaceCastRows(workspace.run_id),
              getWorkspaceCorentRows(workspace.run_id),
              getWorkspaceBizRows(workspace.run_id),
            ]);
            setUpdatedRowsData({
              cast:   (castRes.data?.rows   ?? []).filter(r => r.updated_rows),
              corent: (corentRes.data?.rows ?? []).filter(r => r.updated_rows),
              biz:    (bizRes.data?.rows    ?? []).filter(r => r.updated_rows),
            });
          } catch (e) {
            console.warn('Could not fetch updated rows data:', e);
          }
        }

        toast.success(
          `Correlation + AI analysis done! ${summary.matched_count}/${summary.total_count} items matched`,
          { autoClose: 6000 }
        );

        // Fetch the complete correlation data and switch to Workspace tab
        await fetchLatestCorrelation();
        setActiveTab('workspace');
      } else {
        toast.error(response.data.message || 'Correlation failed');
      }
    } catch (error) {
      stepTimers.forEach(clearTimeout);
      setCorrelationStep(null);
      toast.error(
        error.response?.data?.message ||
        'Correlation failed. Ensure CORENT, CAST and Industry files are uploaded.'
      );
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
    if (window.confirm('Clear all correlation data? This cannot be undone.')) {
      setCorrelationData(null);
      setLlmAnalysis(null);
      setPipelineStats(null);
      setWorkspaceData(null);
      setColumnUpdates([]);
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
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 flex items-center gap-3">
                <BarChart3 size={40} className="text-blue-600" />
                Infrastructure & Code Analysis Correlation
              </h1>
              <p className="text-gray-600 mt-2">
                Correlate Corent infrastructure data with CAST code analysis — powered by local AI (Ollama)
              </p>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              {/* Ollama status badge */}
              {ollamaStatus && (
                <div
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border ${
                    ollamaStatus.available
                      ? 'bg-green-50 border-green-300 text-green-700'
                      : 'bg-amber-50 border-amber-300 text-amber-700'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full ${ollamaStatus.available ? 'bg-green-500' : 'bg-amber-500'}`} />
                  {ollamaStatus.available
                    ? `AI: ${ollamaStatus.selected_model ?? 'Ollama ready'}`
                    : 'AI: Ollama offline'}
                </div>
              )}

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
                    <span>Running pipeline...</span>
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

          {/* Pipeline progress (visible while correlating) */}
          {correlating && (
            <div className="mt-6 p-5 bg-blue-50 border border-blue-200 rounded-xl text-center">
              <p className="text-blue-800 font-semibold text-sm mb-2">
                Running full AI pipeline â€” this may take a minuteâ€¦
              </p>
              <PipelineStepList activeStep={correlationStep} />
            </div>
          )}

          {/* Status (visible after correlation is complete) */}
          {!correlating && correlationData && (
            <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
              <p className="text-emerald-800 font-medium">
                ✓ Last correlation: {new Date(correlationData.correlation.created_at).toLocaleString()}
              </p>
              <p className="text-emerald-700 text-sm mt-1">
                {correlationData.correlation.matched_count} of {correlationData.correlation.total_count} items matched
                ({correlationData.correlation.match_percentage}%)
              </p>
              {pipelineStats && (
                <p className="text-emerald-600 text-xs mt-1">
                  {pipelineStats.total_apps} apps consolidated · {pipelineStats.total_ai_fills ?? 0} fields AI-predicted
                </p>
              )}
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
            <p className="text-gray-600 mb-4 max-w-2xl mx-auto">
              Upload CORENT Infrastructure, CAST Code Analysis, and Industry Template files,
              then click <strong>"Correlate Files &amp; Start Analysis"</strong> to begin.
            </p>
            <p className="text-gray-500 text-sm max-w-xl mx-auto">
              The pipeline will: predict missing values with AI â†’ build a consolidated DB
              â†’ match applications by APP ID (with name-based fallback) â†’ generate an
              LLM-powered portfolio analysis.
            </p>
            {ollamaStatus && !ollamaStatus.available && (
              <div className="mt-6 inline-block bg-amber-50 border border-amber-200 rounded-lg px-5 py-3 text-sm text-amber-700">
                <strong>Ollama not detected.</strong> AI null-prediction and analysis will be skipped.
                Run <code className="bg-amber-100 px-1 rounded">ollama serve</code> and{' '}
                <code className="bg-amber-100 px-1 rounded">ollama pull mistral</code> to enable.
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Tab Navigation */}
            <div className="bg-white rounded-t-xl border-b border-gray-200">
              <div className="flex overflow-x-auto">
                {[
                  { id: 'overview', label: 'Overview' },
                  { id: 'corent', label: 'Corent Dashboard' },
                  { id: 'cast', label: 'CAST Dashboard' },
                  { id: 'correlation', label: 'Correlation Layer' },
                  { id: 'matrix', label: 'Master Matrix' },
                  { id: 'workspace', label: '📂 Workspace' },
                  { id: 'ai_analysis', label: '🤖 AI Analysis' },
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
              {activeTab === 'workspace' && (
                <WorkspacePredictionPanel workspaceData={workspaceData} columnUpdates={columnUpdates} updatedRowsData={updatedRowsData} />
              )}
              {activeTab === 'ai_analysis' && (
                <LLMAnalysisPanel
                  llmAnalysis={llmAnalysis}
                  pipelineStats={pipelineStats}
                  onRegenerate={handleRerunAnalysis}
                  rerunning={rerunning}
                  onDrillDown={setDrillDown}
                />
              )}
            </div>
          </>
        )}
      </div>

      {/* L2/L3 Drill-Down Modal */}
      <AppDrillDownModal
        open={!!drillDown}
        mode={drillDown?.mode}
        title={drillDown?.title}
        tier={drillDown?.tier}
        appId={drillDown?.appId}
        onClose={() => setDrillDown(null)}
      />
    </div>
  );
};

export default CorrelationDashboard;
