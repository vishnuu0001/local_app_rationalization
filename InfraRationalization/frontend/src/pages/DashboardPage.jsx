import { useState, useEffect, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, ChevronRight, Database, Activity, CheckCircle, XCircle, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { AppContext } from '../App.jsx'
import { listScans, listScanJobs, deleteScan } from '../api/client.js'
import AppHeader from '../components/AppHeader.jsx'

const PROVIDER_BADGE = {
  onprem: 'bg-slate-700/80 text-slate-200',
  aws:    'bg-orange-900/60 text-orange-300',
  azure:  'bg-blue-900/60 text-blue-300',
  gcp:    'bg-green-900/60 text-green-300',
  multi:  'bg-purple-900/60 text-purple-300',
  OnPrem: 'bg-slate-700/80 text-slate-200',
  Azure:  'bg-blue-900/60 text-blue-300',
  AWS:    'bg-orange-900/60 text-orange-300',
  GCP:    'bg-green-900/60 text-green-300',
}

const STATUS_ICON = {
  pending:   <Clock size={14} className="text-slate-400" />,
  running:   <Activity size={14} className="text-emerald-400 animate-pulse" />,
  completed: <CheckCircle size={14} className="text-emerald-400" />,
  failed:    <XCircle size={14} className="text-red-400" />,
}

const STATUS_BADGE = {
  pending:   'bg-slate-700 text-slate-300',
  running:   'bg-emerald-900/60 text-emerald-300',
  completed: 'bg-emerald-900/40 text-emerald-200',
  failed:    'bg-red-900/40 text-red-300',
}

export default function DashboardPage() {
  const { user } = useContext(AppContext)
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [jobsData, scansData] = await Promise.allSettled([listScanJobs(), listScans()])
      if (jobsData.status === 'fulfilled') setJobs(jobsData.value.jobs || [])
      if (scansData.status === 'fulfilled') setScans(scansData.value.scans || [])
    } catch {
      toast.error('Failed to load scans')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // Auto-refresh every 5s while any job is running
    const interval = setInterval(() => {
      listScanJobs().then(d => setJobs(d.jobs || [])).catch(() => {})
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleDelete = async (e, scanId) => {
    e.stopPropagation()
    if (!window.confirm('Delete this scan report?')) return
    try {
      await deleteScan(scanId)
      setScans(prev => prev.filter(s => s.scan_id !== scanId))
      toast.success('Scan deleted')
    } catch {
      toast.error('Failed to delete scan')
    }
  }

  const activeJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const finishedJobs = jobs.filter(j => j.status === 'completed' || j.status === 'failed')

  return (
    <div className="min-h-screen bg-surface">
      <AppHeader
        title="Infra Scan"
        subtitle="Deep-scan your infrastructure and get a cloud-readiness report"
      />
      <main className="max-w-7xl mx-auto px-5 py-8 space-y-8">
        {/* Heading */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-2xl font-semibold text-white">Infrastructure Scans</h2>
            <p className="text-slate-400 text-sm mt-1">
              Deep-scan your on-premises, AWS, Azure, or GCP infrastructure and get a cloud migration report.
            </p>
          </div>
          <button
            onClick={() => navigate('/new-scan')}
            className="btn-primary px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2"
          >
            <Plus size={16} /> New Scan
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-brand-green border-r-transparent" />
          </div>
        ) : (
          <>
            {/* Active jobs */}
            {activeJobs.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-widest mb-3">
                  Active Scans
                </h3>
                <div className="space-y-3">
                  {activeJobs.map(job => (
                    <div
                      key={job.scan_id}
                      onClick={() => navigate(`/scans/progress/${job.scan_id}`)}
                      className="glass p-4 cursor-pointer hover:border-emerald-600 transition-all"
                    >
                      <div className="flex items-center justify-between gap-4 flex-wrap">
                        <div className="flex items-center gap-3">
                          {STATUS_ICON[job.status]}
                          <div>
                            <p className="font-medium text-white text-sm">{job.report_name}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{job.progress_message || 'Initialising…'}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[job.status]}`}>
                            {job.status}
                          </span>
                          <span className="text-sm font-medium text-emerald-400">{job.progress || 0}%</span>
                        </div>
                      </div>
                      <div className="mt-3 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                          style={{ width: `${job.progress || 0}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Completed scan jobs */}
            {finishedJobs.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-3">
                  Recent Scans
                </h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {finishedJobs.map(job => (
                    <div
                      key={job.scan_id}
                      onClick={() => job.status === 'completed' ? navigate(`/scans/${job.scan_id}`) : navigate(`/scans/progress/${job.scan_id}`)}
                      className="glass p-5 cursor-pointer hover:border-slate-500 transition-all group"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-white truncate">{job.report_name}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[job.status]}`}>
                              {job.status}
                            </span>
                          </div>
                        </div>
                        {STATUS_ICON[job.status]}
                      </div>
                      <div className="mt-4 flex items-center justify-between text-xs">
                        <span className="text-slate-400">
                          <span className="font-semibold text-slate-200">{job.server_count ?? 0}</span> servers
                          {job.completed_at && (
                            <>
                              <span className="mx-2 text-slate-600">·</span>
                              {new Date(job.completed_at).toLocaleDateString()}
                            </>
                          )}
                        </span>
                        <ChevronRight size={14} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Persisted (manually uploaded) scans */}
            {scans.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
                  Saved Reports
                </h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {scans.map(scan => (
                    <div
                      key={scan.scan_id}
                      onClick={() => navigate(`/scans/${scan.scan_id}`)}
                      className="glass p-5 cursor-pointer hover:border-slate-500 transition-all group"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-white truncate">{scan.report_name}</p>
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_BADGE[scan.source_environment] || 'bg-slate-700/80 text-slate-200'}`}>
                              {scan.source_environment}
                            </span>
                            {scan.target_cloud && (
                              <>
                                <span className="text-slate-500 text-xs">→</span>
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_BADGE[scan.target_cloud] || 'bg-slate-700/80 text-slate-200'}`}>
                                  {scan.target_cloud}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={e => handleDelete(e, scan.scan_id)}
                          className="shrink-0 p-1.5 text-slate-600 hover:text-red-400 transition-colors rounded-lg hover:bg-red-950/30"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      <div className="mt-4 flex items-center justify-between text-xs">
                        <span className="text-slate-400">
                          <span className="font-semibold text-slate-200">{scan.total_servers}</span> servers
                          <span className="mx-2 text-slate-600">·</span>
                          {new Date(scan.created_at).toLocaleDateString()}
                        </span>
                        <ChevronRight size={14} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Empty state */}
            {activeJobs.length === 0 && finishedJobs.length === 0 && scans.length === 0 && (
              <div className="text-center py-24">
                <Database size={40} className="mx-auto text-slate-600 mb-4" />
                <p className="text-slate-300 font-medium mb-2">No scans yet</p>
                <p className="text-slate-500 text-sm mb-6">
                  Configure a scan target and discover your infrastructure automatically.
                </p>
                <button
                  onClick={() => navigate('/new-scan')}
                  className="btn-primary px-5 py-2.5 rounded-xl text-sm font-semibold inline-flex items-center gap-2"
                >
                  <Plus size={15} /> Start First Scan
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

