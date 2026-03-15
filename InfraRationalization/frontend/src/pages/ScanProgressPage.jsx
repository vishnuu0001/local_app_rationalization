import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle, XCircle, FileText } from 'lucide-react'
import { getScanJob, getScanStreamUrl, getPortalToken } from '../api/client.js'
import AppHeader from '../components/AppHeader.jsx'

const STATUS_COLOR = {
  pending:   'text-slate-400',
  running:   'text-emerald-400',
  completed: 'text-emerald-300',
  failed:    'text-red-400',
}

export default function ScanProgressPage() {
  const { scanId } = useParams()
  const navigate = useNavigate()
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('Connecting…')
  const [status, setStatus] = useState('pending')
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const logsEndRef = useRef(null)
  const esRef = useRef(null)

  useEffect(() => {
    // Poll job status immediately
    getScanJob(scanId).then(j => {
      setStatus(j.status)
      setProgress(j.progress || 0)
      setMessage(j.progress_message || '')
    }).catch(() => {})

    // Connect SSE with auth token in query string (EventSource doesn't support headers)
    const token = getPortalToken()
    const url = `${getScanStreamUrl(scanId)}${token ? `?token=${encodeURIComponent(token)}` : ''}`
    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.progress !== undefined) setProgress(data.progress)
        if (data.message) {
          setMessage(data.message)
          setLogs(prev => [...prev.slice(-199), `[${new Date().toLocaleTimeString()}] ${data.message}`])
        }
        if (data.status) setStatus(data.status)
        if (data.error) setError(data.error)
        if (data.progress >= 100 || data.status === 'completed' || data.status === 'failed') {
          es.close()
        }
      } catch { /* non-JSON keepalive */ }
    }

    es.onerror = () => {
      // Re-check job status after SSE error
      getScanJob(scanId).then(j => {
        setStatus(j.status)
        setProgress(j.progress || 0)
        setMessage(j.progress_message || '')
        if (j.error) setError(j.error)
        if (j.status === 'completed' || j.status === 'failed') es.close()
      }).catch(() => {})
    }

    return () => es.close()
  }, [scanId])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const isFinished = status === 'completed' || status === 'failed'

  return (
    <div className="min-h-screen bg-surface">
      <AppHeader title="Scan in Progress" subtitle={`Job ID: ${scanId}`} backTo="/" />

      <main className="max-w-3xl mx-auto px-5 py-8 space-y-6">
        {/* Status card */}
        <div className="glass p-8 text-center space-y-6">
          {status === 'completed' ? (
            <CheckCircle size={48} className="mx-auto text-emerald-400" />
          ) : status === 'failed' ? (
            <XCircle size={48} className="mx-auto text-red-400" />
          ) : (
            <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-emerald-500 border-r-transparent mx-auto" />
          )}

          <div>
            <p className={`text-xl font-semibold capitalize ${STATUS_COLOR[status] || 'text-white'}`}>
              {status}
            </p>
            <p className="text-slate-400 text-sm mt-1 max-w-md mx-auto">{message}</p>
          </div>

          {/* Progress bar */}
          <div className="max-w-md mx-auto">
            <div className="flex justify-between text-xs text-slate-400 mb-2">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  status === 'failed' ? 'bg-red-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-sm text-red-300 text-left">
              <strong>Error:</strong> {error}
            </div>
          )}

          {isFinished && (
            <div className="flex gap-3 justify-center">
              <button onClick={() => navigate('/')} className="btn-ghost px-5 py-2.5 rounded-xl text-sm">
                Back to Dashboard
              </button>
              {status === 'completed' && (
                <button
                  onClick={() => navigate(`/scans/${scanId}`)}
                  className="btn-primary px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2"
                >
                  <FileText size={15} />
                  View Report
                </button>
              )}
            </div>
          )}
        </div>

        {/* Log stream */}
        {logs.length > 0 && (
          <div className="glass p-5">
            <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-widest mb-3">
              Scan Log
            </h3>
            <div className="bg-slate-900 rounded-lg p-4 font-mono text-xs text-slate-300 max-h-64 overflow-y-auto space-y-1">
              {logs.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
