import React, { useState, useCallback, useEffect } from 'react';
import { toast } from 'react-toastify';
import {
  generateGoldenData,
  getGoldenDataDownloadUrl,
  clearGoldenData,
  getGoldenDataRecords,
  updateGoldenDataRecord,
  regenerateGoldenExcel,
} from '../services/api';

/* ---------------------------------------------------------------------------
   Column definitions  (xlsCol = 0-based index in the 64-column APR layout)
--------------------------------------------------------------------------- */
const FIELDS = [
  { key: 'app_id',   label: 'App ID',   source: 'corent', type: 'text', xlsCol: 0  },
  { key: 'app_name', label: 'App Name', source: 'corent', type: 'text', xlsCol: 1  },
  { key: 'server_type',                          label: 'Server Type',                           source: 'corent', type: 'text', xlsCol: 2  },
  { key: 'operating_system',                     label: 'Operating System',                      source: 'corent', type: 'text', xlsCol: 3  },
  { key: 'cpu_core',                             label: 'CPU Core',                              source: 'corent', type: 'text', xlsCol: 4  },
  { key: 'memory',                               label: 'Memory',                                source: 'corent', type: 'text', xlsCol: 5  },
  { key: 'internal_storage',                     label: 'Internal Storage',                      source: 'corent', type: 'text', xlsCol: 6  },
  { key: 'external_storage',                     label: 'External Storage',                      source: 'corent', type: 'text', xlsCol: 7  },
  { key: 'storage_type',                         label: 'Storage Type',                          source: 'corent', type: 'text', xlsCol: 8  },
  { key: 'db_storage',                           label: 'DB Storage',                            source: 'corent', type: 'text', xlsCol: 9  },
  { key: 'db_engine',                            label: 'DB Engine',                             source: 'corent', type: 'text', xlsCol: 10 },
  { key: 'environment_install_type',             label: 'Environment (Install Type)',            source: 'corent', type: 'text', xlsCol: 11 },
  { key: 'virtualization_attributes',            label: 'Virtualization Attributes',             source: 'corent', type: 'text', xlsCol: 12 },
  { key: 'compute_server_hardware_architecture', label: 'Compute Server HW Architecture',       source: 'corent', type: 'text', xlsCol: 13 },
  { key: 'application_stability',                label: 'Application Stability',                 source: 'corent', type: 'text', xlsCol: 14 },
  { key: 'virtualization_state',                 label: 'Virtualization State',                  source: 'corent', type: 'text', xlsCol: 15 },
  { key: 'storage_decomposition',                label: 'Storage Decomposition',                 source: 'corent', type: 'text', xlsCol: 16 },
  { key: 'flash_storage_used',                   label: 'Flash Storage Used',                    source: 'corent', type: 'text', xlsCol: 17 },
  { key: 'cpu_requirement',                      label: 'CPU Requirement',                       source: 'corent', type: 'text', xlsCol: 18 },
  { key: 'memory_ram_requirement',               label: 'Memory/RAM Requirement',                source: 'corent', type: 'text', xlsCol: 19 },
  { key: 'mainframe_dependency',                 label: 'Mainframe Dependency',                  source: 'corent', type: 'text', xlsCol: 20 },
  { key: 'desktop_dependency',                   label: 'Desktop Dependency',                    source: 'corent', type: 'text', xlsCol: 21 },
  { key: 'app_os_platform_cloud_suitability',    label: 'App OS Platform Cloud Suitability',     source: 'corent', type: 'text', xlsCol: 22 },
  { key: 'database_cloud_readiness',             label: 'Database Cloud Readiness',              source: 'corent', type: 'text', xlsCol: 23 },
  { key: 'integration_middleware_cloud_readiness', label: 'Integration/Middleware Cloud Readiness', source: 'corent', type: 'text', xlsCol: 24 },
  { key: 'application_architecture',             label: 'Application Architecture',              source: 'cast',   type: 'text', xlsCol: 25 },
  { key: 'application_hardware_dependency',      label: 'Application Hardware Dependency',       source: 'corent', type: 'text', xlsCol: 26 },
  { key: 'app_cots_vs_non_cots',                 label: 'App COTS vs Non-COTS',                  source: 'corent', type: 'text', xlsCol: 27 },
  { key: 'source_code_availability',             label: 'Source Code Availability',              source: 'cast',   type: 'text', xlsCol: 28 },
  { key: 'programming_language',                 label: 'Programming Language',                  source: 'cast',   type: 'text', xlsCol: 29 },
  { key: 'component_coupling',                   label: 'Component Coupling',                    source: 'cast',   type: 'text', xlsCol: 30 },
  { key: 'cloud_suitability',                    label: 'Cloud Suitability',                     source: 'joint',  type: 'text', xlsCol: 31 },
  { key: 'volume_external_dependencies',         label: 'Volume of External Dependencies',       source: 'joint',  type: 'text', xlsCol: 32 },
  { key: 'app_service_api_readiness',            label: 'App Service/API Readiness',             source: 'cast',   type: 'text', xlsCol: 33 },
  { key: 'app_load_predictability_elasticity',   label: 'App Load Predictability/Elasticity',    source: 'corent', type: 'text', xlsCol: 34 },
  { key: 'degree_of_code_protocols',             label: 'Degree of Code Protocols',              source: 'cast',   type: 'text', xlsCol: 35 },
  { key: 'code_design',                          label: 'Code Design',                           source: 'cast',   type: 'text', xlsCol: 36 },
  { key: 'application_code_complexity_volume',   label: 'Application Code Complexity/Volume',    source: 'cast',   type: 'text', xlsCol: 37 },
  { key: 'financially_optimizable_hardware_usage', label: 'Financially Optimizable HW Usage',   source: 'corent', type: 'text', xlsCol: 38 },
  { key: 'distributed_architecture_design',      label: 'Distributed Architecture Design',       source: 'joint',  type: 'text', xlsCol: 39 },
  { key: 'latency_requirements',                 label: 'Latency Requirements',                  source: 'corent', type: 'text', xlsCol: 40 },
  { key: 'ubiquitous_access_requirements',       label: 'Ubiquitous Access Requirements',        source: 'corent', type: 'text', xlsCol: 41 },
  // SURVEY fields (xlsCol 42-51, 55, 59-63)
  { key: 'level_of_data_residency_compliance',   label: 'Level of Data Residency Compliance',    source: 'survey', type: 'text', xlsCol: 42 },
  { key: 'data_classification',                  label: 'Data Classification',                   source: 'survey', type: 'text', xlsCol: 43 },
  { key: 'app_regulatory_contractual_requirements', label: 'App Regulatory & Contractual Req.',  source: 'survey', type: 'text', xlsCol: 44 },
  { key: 'impact_due_to_data_loss',              label: 'Impact Due to Data Loss',               source: 'survey', type: 'text', xlsCol: 45 },
  { key: 'financial_impact_due_to_unavailability', label: 'Financial Impact Due to Unavailability', source: 'survey', type: 'text', xlsCol: 46 },
  { key: 'business_criticality',                 label: 'Business Criticality',                  source: 'survey', type: 'text', xlsCol: 47 },
  { key: 'customer_facing',                      label: 'Customer Facing',                       source: 'survey', type: 'text', xlsCol: 48 },
  { key: 'application_status_lifecycle_state',   label: 'Application Status & Lifecycle State',  source: 'survey', type: 'text', xlsCol: 49 },
  { key: 'availability_requirements',            label: 'Availability Requirements',             source: 'survey', type: 'text', xlsCol: 50 },
  { key: 'support_level',                        label: 'Support Level',                         source: 'survey', type: 'text', xlsCol: 51 },
  // Back to CORENT (xlsCol 52-54, 56-58)
  { key: 'no_of_production_environments',        label: '# Production Environments',             source: 'corent', type: 'int',  xlsCol: 52 },
  { key: 'no_of_non_production_environments',    label: '# Non-Production Environments',         source: 'corent', type: 'int',  xlsCol: 53 },
  { key: 'ha_dr_requirements',                   label: 'HA/DR Requirements',                    source: 'corent', type: 'text', xlsCol: 54 },
  { key: 'business_function_readiness',          label: 'Business Function Readiness',           source: 'survey', type: 'text', xlsCol: 55 },
  { key: 'rto_requirements',                     label: 'RTO Requirements',                      source: 'corent', type: 'text', xlsCol: 56 },
  { key: 'rpo_requirements',                     label: 'RPO Requirements',                      source: 'corent', type: 'text', xlsCol: 57 },
  { key: 'deployment_geography',                 label: 'Deployment Geography',                  source: 'corent', type: 'text', xlsCol: 58 },
  // SURVEY (xlsCol 59-63)
  { key: 'level_of_internal_governance',         label: 'Level of Internal Governance',          source: 'survey', type: 'text', xlsCol: 59 },
  { key: 'no_of_internal_users',                 label: 'No. of Internal Users',                 source: 'survey', type: 'text', xlsCol: 60 },
  { key: 'no_of_external_users',                 label: 'No. of External Users',                 source: 'survey', type: 'text', xlsCol: 61 },
  { key: 'estimated_app_growth',                 label: 'Estimated App Growth',                  source: 'survey', type: 'text', xlsCol: 62 },
  { key: 'impact_to_users',                      label: 'Impact to Users',                       source: 'survey', type: 'text', xlsCol: 63 },
];

const SOURCE_BADGE = {
  corent: { label: 'CORENT',      cls: 'bg-blue-100 text-blue-700'     },
  cast:   { label: 'CAST',        cls: 'bg-green-100 text-green-700'   },
  joint:  { label: 'CORENT+CAST', cls: 'bg-purple-100 text-purple-700' },
  survey: { label: 'SURVEY',      cls: 'bg-orange-100 text-orange-700' },
};

/** Determine cell CSS class from DB record + field definition */
function cellCls(rec, fieldDef) {
  const val = rec[fieldDef.key];
  const isEmpty = val === null || val === undefined || val === '';
  // Check AI-fill from ai_filled_cols (list of Excel column indices)
  const ai_filled_cols = rec.ai_filled_cols || [];
  if (Array.isArray(ai_filled_cols) && ai_filled_cols.includes(fieldDef.xlsCol)) {
    return 'bg-yellow-200 text-yellow-900 font-medium';  // Yellow = AI populated
  }
  if (isEmpty && fieldDef.source === 'survey') {
    return 'bg-amber-100 text-amber-800';  // Amber = empty survey cell
  }
  return isEmpty ? 'bg-gray-50 text-gray-400' : 'bg-white text-gray-800';
}

/* ---------------------------------------------------------------------------
   Edit Modal
--------------------------------------------------------------------------- */
function EditModal({ record, onClose, onSaved }) {
  const [form, setForm] = useState(() => {
    const init = {};
    FIELDS.forEach(f => { init[f.key] = record[f.key] ?? ''; });
    return init;
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {};
      FIELDS.forEach(f => {
        if (!f.readOnly) {
          payload[f.key] = f.type === 'int'
            ? (form[f.key] === '' ? null : parseInt(form[f.key], 10) || null)
            : (form[f.key] === '' ? null : form[f.key]);
        }
      });
      await updateGoldenDataRecord(record.app_id, payload);
      toast.success(`Updated ${form.app_id || record.app_id}`);
      onSaved();
    } catch (err) {
      toast.error('Save failed: ' + (err?.response?.data?.message || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b bg-blue-900 rounded-t-2xl">
          <div>
            <h2 className="text-white font-bold text-lg">Edit Record</h2>
            <p className="text-blue-200 text-sm">{record.app_id} — {record.app_name}</p>
          </div>
          <button onClick={onClose} className="text-blue-200 hover:text-white text-2xl leading-none">&times;</button>
        </div>
        <div className="overflow-y-auto flex-1 px-6 py-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FIELDS.filter(f => !f.readOnly).map(f => {
              const badge = SOURCE_BADGE[f.source] || SOURCE_BADGE.survey;
              return (
                <div key={f.key} className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-gray-600 flex items-center gap-1">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.cls}`}>{badge.label}</span>
                    {f.label}
                  </label>
                  <input
                    type={f.type === 'int' ? 'number' : 'text'}
                    value={form[f.key] ?? ''}
                    onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              );
            })}
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t bg-gray-50 rounded-b-2xl">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors">
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving}
            className="px-5 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold transition-colors disabled:opacity-50">
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Main component
--------------------------------------------------------------------------- */
export default function GoldenData() {
  const [status, setStatus]               = useState('idle');
  const [records, setRecords]             = useState([]);
  const [loading, setLoading]             = useState(true);
  const [message, setMessage]             = useState('');
  const [filterText, setFilterText]       = useState('');
  const [visibleCols, setVisibleCols]     = useState(() => new Set(FIELDS.map(f => f.key)));
  const [showColPicker, setShowColPicker] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [needsRegenerate, setNeedsRegenerate] = useState(false);
  const [regenerating, setRegenerating]   = useState(false);

  const loadRecords = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const { data } = await getGoldenDataRecords(1, 500, '');
      const recs = data.records || data.items || (Array.isArray(data) ? data : []);
      setRecords(recs);
      if (recs.length > 0) setStatus('done');
    } catch (_) { /* no data yet */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  const handleGenerate = useCallback(async () => {
    setStatus('generating'); setMessage('');
    try {
      const { data } = await generateGoldenData();
      if (!data.success) throw new Error(data.message);
      setMessage(data.message || '');
      setNeedsRegenerate(false);
      await loadRecords(true);
      setStatus('done');
      toast.success(`${data.row_count} rows generated`);
    } catch (err) {
      const msg = err?.response?.data?.message || err.message || 'Generation failed';
      setMessage(msg); setStatus('error');
      toast.error(msg);
    }
  }, [loadRecords]);

  const handleClear = useCallback(async () => {
    if (!window.confirm('This will delete all Golden Data records from the database and remove the generated Excel file. Continue?')) return;
    try {
      await clearGoldenData();
      setStatus('idle'); setRecords([]); setNeedsRegenerate(false); setMessage('');
      toast.info('All Golden Data cleared — DB records and Excel file deleted.');
    } catch (err) {
      toast.error('Clear failed: ' + (err?.response?.data?.message || err.message));
    }
  }, []);

  const handleDownload = useCallback(() => {
    const a = document.createElement('a');
    a.href = getGoldenDataDownloadUrl();
    a.download = 'APRAttributes_GoldenData.xlsx';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }, []);

  const handleRegenerate = useCallback(async () => {
    setRegenerating(true);
    try {
      const { data } = await regenerateGoldenExcel();
      if (!data.success) throw new Error(data.message);
      setNeedsRegenerate(false);
      toast.success(`Excel rebuilt from ${data.row_count} records`);
    } catch (err) {
      toast.error('Regenerate failed: ' + (err?.response?.data?.message || err.message));
    } finally { setRegenerating(false); }
  }, []);

  const handleEditSaved = useCallback(async () => {
    setEditingRecord(null); setNeedsRegenerate(true);
    await loadRecords(true);
  }, [loadRecords]);

  const toggleCol = key => setVisibleCols(prev => {
    const next = new Set(prev);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });
  const selectAllCols = () => setVisibleCols(new Set(FIELDS.map(f => f.key)));
  const clearAllCols  = () => setVisibleCols(new Set(['app_id', 'app_name']));

  const visibleFields    = FIELDS.filter(f => visibleCols.has(f.key));
  const filteredRecords  = filterText.trim()
    ? records.filter(rec => FIELDS.some(f => {
        const v = rec[f.key];
        return v != null && String(v).toLowerCase().includes(filterText.toLowerCase());
      }))
    : records;

  const Spinner = () => (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
    </svg>
  );

  return (
    <div className="flex flex-col h-full bg-gray-50">

      {/* Top bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <span>🏅</span> Golden Data
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Consolidated CORENT + CAST data →{' '}
            <span className="font-medium">APRAttributes / Inputs from Sources</span>
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {records.length > 0 && (
            <>
              <button onClick={handleDownload}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium text-sm shadow-sm transition-colors">
                ⬇️ Download Excel
              </button>
              <button onClick={handleClear}
                className="flex items-center gap-2 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium text-sm shadow-sm transition-colors">
                🗑️ Clear
              </button>
            </>
          )}
          <button onClick={handleGenerate} disabled={status === 'generating'}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg font-semibold text-white text-sm shadow-sm transition-colors ${
              status === 'generating' ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-700 hover:bg-blue-800'
            }`}>
            {status === 'generating' ? <><Spinner /> Generating...</> : <>⚡ Generate</>}
          </button>
        </div>
      </div>

      {/* Regenerate banner */}
      {needsRegenerate && (
        <div className="bg-yellow-50 border-b border-yellow-300 px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
          <span className="text-yellow-800 text-sm font-medium">
            ⚠️ Records edited — click <strong>Regenerate Excel</strong> to apply to the file.
          </span>
          <button onClick={handleRegenerate} disabled={regenerating}
            className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-1.5 rounded-lg font-semibold text-sm shadow-sm transition-colors disabled:opacity-50">
            {regenerating ? <><Spinner /> Regenerating...</> : <>🔄 Regenerate Excel</>}
          </button>
        </div>
      )}

      {/* Status strip */}
      {status !== 'idle' && (
        <div className={`px-6 py-2 text-sm flex items-center gap-4 flex-wrap border-b ${
          status === 'error'      ? 'bg-red-50 border-red-200 text-red-700' :
          status === 'generating' ? 'bg-blue-50 border-blue-200 text-blue-700' :
                                    'bg-green-50 border-green-200 text-green-700'
        }`}>
          {status === 'done' && (
            <span>✅ <strong>{records.length}</strong> rows in DB — file: <code>UpdatedData/APRAttributes.xlsx</code></span>
          )}
          {status === 'generating' && <span>🔄 Generating…</span>}
          {status === 'error'      && <span>❌ {message}</span>}
        </div>
      )}

      {/* Idle placeholder */}
      {!loading && records.length === 0 && status !== 'generating' && (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 text-gray-400">
          <span className="text-5xl">🏅</span>
          <p className="text-lg font-medium">No Golden Data yet.</p>
          <p className="text-sm">Click <strong>⚡ Generate</strong> to populate from CORENT + CAST.</p>
        </div>
      )}

      {/* Preview table */}
      {records.length > 0 && (
        <div className="flex flex-col flex-1 overflow-hidden px-6 py-4 gap-3">

          {/* Toolbar */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
              <input type="text" placeholder="Filter rows..." value={filterText}
                onChange={e => setFilterText(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56" />
            </div>

            <div className="relative">
              <button onClick={() => setShowColPicker(p => !p)}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white hover:bg-gray-50 transition-colors">
                🗂️ Columns ({visibleCols.size}/{FIELDS.length}) {showColPicker ? '▲' : '▼'}
              </button>
              {showColPicker && (
                <div className="absolute z-40 top-full mt-1 left-0 bg-white border border-gray-200 rounded-xl shadow-xl p-4 w-96 max-h-80 overflow-y-auto">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm text-gray-700">Toggle Columns</span>
                    <div className="flex gap-2">
                      <button onClick={selectAllCols} className="text-xs text-blue-600 hover:underline">All</button>
                      <button onClick={clearAllCols}  className="text-xs text-gray-500 hover:underline">Min</button>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-1">
                    {FIELDS.map(f => {
                      const badge = SOURCE_BADGE[f.source] || SOURCE_BADGE.survey;
                      return (
                        <label key={f.key} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-gray-50 px-1 rounded">
                          <input type="checkbox" checked={visibleCols.has(f.key)} onChange={() => toggleCol(f.key)} className="accent-blue-600" />
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.cls}`}>{badge.label}</span>
                          <span className="text-gray-700 truncate">{f.label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <span className="text-sm text-gray-500 ml-auto">{filteredRecords.length} of {records.length} rows</span>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-3 text-xs flex-wrap">
            <span className="text-gray-500 font-medium">Source:</span>
            {Object.values(SOURCE_BADGE).map(({ label, cls }) => (
              <span key={label} className={`px-2 py-0.5 rounded font-medium ${cls}`}>{label}</span>
            ))}
            <span className="ml-3 text-gray-500 font-medium">Cell:</span>
            <span className="px-2 py-0.5 rounded font-medium bg-yellow-200 text-yellow-900 border border-yellow-400">🤖 AI Populated</span>
            <span className="px-2 py-0.5 rounded font-medium bg-amber-100 text-amber-800 border border-amber-300">⚠️ Empty Survey</span>
            <span className="px-2 py-0.5 rounded font-medium bg-white text-gray-800 border border-gray-300">✅ DB Value</span>
            <span className="ml-2 text-gray-400 italic text-[11px]">✏️ click to edit row</span>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto rounded-xl border border-gray-200 shadow-sm bg-white">
            <table className="min-w-full text-xs border-collapse">
              <thead className="sticky top-0 z-10 bg-blue-900 text-white">
                <tr>
                  <th className="px-2 py-2 text-center border-r border-blue-700 w-8">#</th>
                  <th className="px-2 py-2 border-r border-blue-700 w-10 text-center">Edit</th>
                  {visibleFields.map(f => (
                    <th key={f.key} className="px-3 py-2 font-semibold border-r border-blue-700 whitespace-nowrap text-left min-w-[110px] max-w-[200px]">
                      <div className="truncate">{f.label}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((rec, rIdx) => (
                  <tr key={rec.app_id || rIdx} className="border-b border-gray-100 hover:brightness-95 transition-all">
                    <td className="px-2 py-1.5 text-center text-gray-400 font-mono border-r border-gray-200">{rIdx + 1}</td>
                    <td className="px-2 py-1.5 text-center border-r border-gray-200">
                      <button onClick={() => setEditingRecord(rec)} title="Edit"
                        className="text-blue-600 hover:text-blue-800 transition-colors text-base">✏️</button>
                    </td>
                    {visibleFields.map(f => {
                      const val = rec[f.key];
                      const empty = val === null || val === undefined || val === '';
                      return (
                        <td key={f.key}
                          className={`px-3 py-1.5 border-r border-gray-100 max-w-[200px] truncate ${cellCls(rec, f)}`}
                          title={String(val ?? '')}>
                          {empty ? '—' : String(val)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editingRecord && (
        <EditModal
          record={editingRecord}
          onClose={() => setEditingRecord(null)}
          onSaved={handleEditSaved}
        />
      )}
    </div>
  );
}
