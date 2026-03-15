import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Upload, Download, CheckCircle2, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { createScan, getTemplateUrl } from '../api/client.js'

export default function UploadPage() {
  const navigate = useNavigate()
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [parsed, setParsed] = useState(null)
  const [parseError, setParseError] = useState('')
  const [saving, setSaving] = useState(false)
  const inputRef = useRef(null)

  const handleFile = (f) => {
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.json')) {
      setParseError('Only JSON files are supported.')
      setParsed(null)
      setFile(null)
      return
    }
    setFile(f)
    setParseError('')
    setParsed(null)
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)
        setParsed(data)
      } catch {
        setParseError('Invalid JSON — could not parse the file.')
      }
    }
    reader.readAsText(f)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleSave = async () => {
    if (!parsed) return
    setSaving(true)
    try {
      const result = await createScan(parsed)
      toast.success('Scan imported successfully')
      navigate(`/scans/${result.scan_id}`)
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to save scan')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-30 border-b border-surface-border bg-surface/90 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-5 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="btn-ghost p-2">
            <ArrowLeft size={18} />
          </button>
          <h1 className="text-lg font-semibold text-white">Upload Infrastructure Scan</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-5 py-8 space-y-5">
        {/* Info panel */}
        <div className="glass p-5">
          <p className="text-sm text-slate-300 font-medium mb-1">JSON Format</p>
          <p className="text-sm text-slate-400 leading-relaxed">
            Upload a JSON infrastructure feasibility report following the MaaS™ scan schema.
            Download the template below to see all supported fields and sample values.
          </p>
          <a
            href={getTemplateUrl()}
            className="inline-flex items-center gap-2 mt-3 text-sm text-brand-green hover:underline"
          >
            <Download size={14} /> Download JSON template
          </a>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-14 text-center cursor-pointer transition-colors ${
            dragging
              ? 'border-brand-green bg-emerald-950/20'
              : 'border-surface-border hover:border-slate-500'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          <Upload size={36} className="mx-auto text-slate-500 mb-3" />
          <p className="text-slate-300 font-medium">Drop your JSON file here</p>
          <p className="text-slate-500 text-sm mt-1">or click to browse</p>
        </div>

        {/* Parse error */}
        {parseError && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-red-950/30 border border-red-800/40 text-red-300 text-sm">
            <AlertCircle size={16} className="shrink-0" />
            {parseError}
          </div>
        )}

        {/* Parsed preview */}
        {parsed && !parseError && (
          <div className="glass p-5">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
              <p className="text-white font-semibold">File parsed successfully</p>
            </div>
            <div className="grid sm:grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wide mb-1">Report Name</p>
                <p className="text-white">{parsed.report_name || '—'}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wide mb-1">Source → Target</p>
                <p className="text-white">{parsed.source_environment || '—'} → {parsed.target_cloud || '—'}{parsed.region ? ` (${parsed.region})` : ''}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wide mb-1">Total Servers</p>
                <p className="text-white">{parsed.summary?.total_servers ?? '—'}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wide mb-1">File</p>
                <p className="text-slate-300 truncate text-xs font-mono">{file?.name}</p>
              </div>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary mt-5 px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2"
            >
              {saving ? 'Saving…' : 'Import Scan Report'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
