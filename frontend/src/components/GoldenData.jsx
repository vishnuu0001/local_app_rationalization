import React, { useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { generateGoldenData, getGoldenDataDownloadUrl, clearGoldenData } from '../services/api';

/* ─────────────────────────────────────────────────────────────────────────────
   Source badge colours
───────────────────────────────────────────────────────────────────────────── */
const SOURCE_COLS = {
  corent: new Set([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,
                   20,21,22,23,24,26,27,34,38,40,41,52,53,54,56,57,58]),
  cast:   new Set([25,28,29,30,33,35,36,37]),
  joint:  new Set([31,32,39]),
};

function sourceBadge(colIndex) {
  if (SOURCE_COLS.joint.has(colIndex))  return { label: 'CORENT+CAST', cls: 'bg-purple-100 text-purple-700' };
  if (SOURCE_COLS.cast.has(colIndex))   return { label: 'CAST',        cls: 'bg-green-100 text-green-700' };
  if (SOURCE_COLS.corent.has(colIndex)) return { label: 'CORENT',      cls: 'bg-blue-100 text-blue-700' };
  return { label: 'SURVEY', cls: 'bg-gray-100 text-gray-500' };
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main component
───────────────────────────────────────────────────────────────────────────── */
export default function GoldenData() {
  const [status, setStatus]         = useState('idle'); // idle | generating | done | error
  const [rowCount, setRowCount]     = useState(0);
  const [headers, setHeaders]       = useState([]);
  const [rows, setRows]             = useState([]);
  const [missingCast, setMissingCast] = useState([]);
  const [message, setMessage]       = useState('');
  const [filterText, setFilterText] = useState('');
  const [visibleCols, setVisibleCols] = useState(() =>
    // Show first 15 columns by default; user can toggle
    new Set(Array.from({ length: 15 }, (_, i) => i))
  );
  const [showColPicker, setShowColPicker] = useState(false);

  /* ── Generate ─────────────────────────────────────────────────────────── */
  const handleGenerate = useCallback(async () => {
    setStatus('generating');
    setRows([]);
    setHeaders([]);
    setMessage('');
    try {
      const { data } = await generateGoldenData();
      if (!data.success) throw new Error(data.message);

      setHeaders(data.preview_headers || []);
      setRows(data.preview_rows || []);
      setRowCount(data.row_count || 0);
      setMissingCast(data.missing_cast || []);
      setMessage(data.message || '');
      setStatus('done');
      // Show first 15 cols on fresh generate
      setVisibleCols(new Set(Array.from({ length: Math.min(15, (data.preview_headers || []).length) }, (_, i) => i)));
      toast.success(`✅ ${data.row_count} rows generated successfully`);
    } catch (err) {
      const msg = err?.response?.data?.message || err.message || 'Generation failed';
      setMessage(msg);
      setStatus('error');
      toast.error(`❌ ${msg}`);
    }
  }, []);

  /* ── Clear ────────────────────────────────────────────────────────────── */
  const handleClear = useCallback(async () => {
    try {
      await clearGoldenData();
      setStatus('idle');
      setRows([]);
      setHeaders([]);
      setRowCount(0);
      setMissingCast([]);
      setMessage('');
      toast.info('🗑️ Output file cleared');
    } catch (err) {
      toast.error('Failed to clear: ' + (err?.response?.data?.message || err.message));
    }
  }, []);

  /* ── Download ─────────────────────────────────────────────────────────── */
  const handleDownload = useCallback(() => {
    const url = getGoldenDataDownloadUrl();
    // Create a temporary anchor and click it so the browser saves the file
    const a = document.createElement('a');
    a.href = url;
    a.download = 'APRAttributes_GoldenData.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, []);

  /* ── Column picker ────────────────────────────────────────────────────── */
  const toggleCol = (i) => {
    setVisibleCols(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  const selectAllCols = () => setVisibleCols(new Set(headers.map((_, i) => i)));
  const clearAllCols  = () => setVisibleCols(new Set([0, 1])); // keep APP ID + name

  /* ── Filtered rows ────────────────────────────────────────────────────── */
  const filteredRows = filterText.trim()
    ? rows.filter(row =>
        row.some(cell =>
          cell !== null && cell !== undefined &&
          String(cell).toLowerCase().includes(filterText.toLowerCase())
        )
      )
    : rows;

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col h-full bg-gray-50">

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <span>🏅</span> Golden Data
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Consolidated CORENT + CAST data mapped to <span className="font-medium">APRAttributes → Inputs from Sources</span>
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {status === 'done' && (
            <>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
              >
                <span>⬇️</span> Download Excel
              </button>
              <button
                onClick={handleClear}
                className="flex items-center gap-2 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
              >
                <span>🗑️</span> Clear
              </button>
            </>
          )}
          <button
            onClick={handleGenerate}
            disabled={status === 'generating'}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg font-semibold text-white shadow-sm transition-colors ${
              status === 'generating'
                ? 'bg-blue-400 cursor-not-allowed'
                : 'bg-blue-700 hover:bg-blue-800'
            }`}
          >
            {status === 'generating' ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Generating…
              </>
            ) : (
              <><span>⚡</span> Generate</>
            )}
          </button>
        </div>
      </div>

      {/* ── Status / summary strip ────────────────────────────────────────── */}
      {status !== 'idle' && (
        <div className={`px-6 py-3 text-sm flex items-center gap-4 flex-wrap border-b ${
          status === 'error'      ? 'bg-red-50 border-red-200 text-red-700' :
          status === 'generating' ? 'bg-blue-50 border-blue-200 text-blue-700' :
                                    'bg-green-50 border-green-200 text-green-700'
        }`}>
          {status === 'done' && (
            <>
              <span>✅ <strong>{rowCount}</strong> application rows written to <code>UpdatedData/APRAttributes.xlsx</code></span>
              {missingCast.length > 0 && (
                <span className="text-orange-600">
                  ⚠️ <strong>{missingCast.length}</strong> app(s) had no CAST data
                </span>
              )}
            </>
          )}
          {status === 'generating' && <span>🔄 Fetching CORENT &amp; CAST data and populating template…</span>}
          {status === 'error'      && <span>❌ {message}</span>}
        </div>
      )}

      {/* ── Preview pane ─────────────────────────────────────────────────── */}
      {status === 'done' && rows.length > 0 && (
        <div className="flex flex-col flex-1 overflow-hidden px-6 py-4 gap-3">

          {/* Toolbar */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Search */}
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
              <input
                type="text"
                placeholder="Filter rows…"
                value={filterText}
                onChange={e => setFilterText(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
              />
            </div>

            {/* Column picker toggle */}
            <div className="relative">
              <button
                onClick={() => setShowColPicker(p => !p)}
                className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white hover:bg-gray-50 transition-colors"
              >
                <span>🗂️</span>
                Columns ({visibleCols.size}/{headers.length})
                <span className="ml-1 text-gray-400">{showColPicker ? '▲' : '▼'}</span>
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
                    {headers.map((h, i) => {
                      const { label, cls } = sourceBadge(i);
                      return (
                        <label key={i} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-gray-50 px-1 rounded">
                          <input
                            type="checkbox"
                            checked={visibleCols.has(i)}
                            onChange={() => toggleCol(i)}
                            className="accent-blue-600"
                          />
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${cls}`}>{label}</span>
                          <span className="text-gray-700 truncate">{h}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <span className="text-sm text-gray-500 ml-auto">
              Showing {filteredRows.length} of {rows.length} rows
              {rows.length < rowCount && ` (preview limited to ${rows.length})`}
            </span>
          </div>

          {/* Source legend */}
          <div className="flex items-center gap-3 text-xs flex-wrap">
            <span className="text-gray-500">Source:</span>
            {[
              { label: 'CORENT', cls: 'bg-blue-100 text-blue-700' },
              { label: 'CAST',   cls: 'bg-green-100 text-green-700' },
              { label: 'CORENT+CAST', cls: 'bg-purple-100 text-purple-700' },
              { label: 'SURVEY (blank)', cls: 'bg-gray-100 text-gray-500' },
            ].map(({ label, cls }) => (
              <span key={label} className={`px-2 py-0.5 rounded font-medium ${cls}`}>{label}</span>
            ))}
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto rounded-xl border border-gray-200 shadow-sm bg-white">
            <table className="min-w-full text-xs border-collapse">
              <thead className="sticky top-0 z-10 bg-blue-900 text-white">
                <tr>
                  <th className="px-3 py-2 text-center font-semibold border-r border-blue-700 w-10">#</th>
                  {headers.map((h, i) => {
                    if (!visibleCols.has(i)) return null;
                    return (
                      <th key={i} className="px-3 py-2 font-semibold border-r border-blue-700 whitespace-nowrap text-left min-w-[120px] max-w-[200px]">
                        <div className="truncate">{h}</div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row, rIdx) => (
                  <tr
                    key={rIdx}
                    className={`border-b border-gray-100 ${rIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition-colors`}
                  >
                    <td className="px-3 py-1.5 text-center text-gray-400 font-mono border-r border-gray-200">
                      {rIdx + 1}
                    </td>
                    {row.map((cell, cIdx) => {
                      if (!visibleCols.has(cIdx)) return null;
                      const isEmpty = cell === null || cell === undefined || cell === '';
                      return (
                        <td
                          key={cIdx}
                          className={`px-3 py-1.5 border-r border-gray-100 max-w-[200px] truncate ${
                            isEmpty ? 'text-gray-300' : 'text-gray-800'
                          }`}
                          title={String(cell ?? '')}
                        >
                          {isEmpty ? '—' : String(cell)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Missing CAST warning */}
          {missingCast.length > 0 && (
            <details className="text-xs text-orange-700 bg-orange-50 border border-orange-200 rounded-lg p-3">
              <summary className="cursor-pointer font-medium">
                ⚠️ {missingCast.length} app(s) had no matching CAST data — CAST columns left blank
              </summary>
              <div className="mt-2 flex flex-wrap gap-1">
                {missingCast.map(id => (
                  <span key={id} className="bg-orange-100 px-2 py-0.5 rounded font-mono">{id}</span>
                ))}
              </div>
            </details>
          )}
        </div>
      )}


    </div>
  );
}
