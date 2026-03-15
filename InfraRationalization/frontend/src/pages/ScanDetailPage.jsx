import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, PieChart, Pie, Cell, Tooltip, Legend,
  ResponsiveContainer, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import {
  Download, Server, ChevronDown, ChevronUp,
  Leaf, Package, AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getScan, getScanReport } from '../api/client.js'
import AppHeader from '../components/AppHeader.jsx'

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const MIGRATION_LABELS = {
  lift_and_shift:      'Lift & Shift',
  smart_shift:         'Smart Shift',
  smart_shift_effort:  'Smart Shift (Effort)',
  paas:                'PaaS',
  paas_effort:         'PaaS (Effort)',
  decommission:        'Decommission',
}

const MIGRATION_BADGE = {
  lift_and_shift:     'bg-emerald-950/60 text-emerald-300 border-emerald-700/40',
  smart_shift:        'bg-blue-950/60 text-blue-300 border-blue-700/40',
  smart_shift_effort: 'bg-amber-950/60 text-amber-300 border-amber-700/40',
  paas:               'bg-purple-950/60 text-purple-300 border-purple-700/40',
  paas_effort:        'bg-slate-800 text-slate-300 border-slate-600/40',
}

const CHART_TOOLTIP_STYLE = {
  background: '#1a1d26',
  border: '1px solid #2a2d3e',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: '12px',
}

/**
 * Normalize scanner report (new format) OR legacy JSON upload (old format)
 * into a single unified shape for rendering.
 */
function normalizeReport(raw) {
  // New scanner format has `sections` key
  if (raw.sections) {
    const s = raw.sections
    const ca = s.cloud_assessment || {}
    const cr = s.cloud_readiness || {}
    const cp = s.capacity_planning || {}

    // Build old-style summary from cloud_assessment
    const summary = {
      total_servers: ca.total_servers || 0,
      os_count: Object.keys(ca.os_distribution || {}).length,
      storage_tb: ca.total_storage_tb || 0,
      utilization_breakdown: {
        underutilized: ca.utilization_distribution?.underutilized || ca.utilization_distribution?.unknown || 0,
        moderate:      ca.utilization_distribution?.moderate || 0,
        utilized:      ca.utilization_distribution?.utilized || 0,
      },
      server_type: Object.keys(ca.server_type_distribution || {})[0] || 'Virtual',
      boot_type:   Object.keys(ca.boot_type_distribution || {})[0] || 'BIOS',
      ip_distribution_note: `${ca.total_ram_gb || 0} GB RAM total Â· ${ca.total_cpu_cores || 0} vCPUs`,
      os_distribution: ca.os_distribution,
    }

    // Normalize servers list
    const servers = (raw.servers || []).map(srv => ({
      ip:                 srv.ip_address,
      name:               srv.server_name,
      os:                 srv.os_name,
      cpu_cores:          srv.cpu_cores,
      ram_gb:             srv.ram_gb,
      disk_gb:            srv.total_storage_gb,
      utilization:        srv.utilization_band,
      migration_strategy: srv.migration_strategy,
      workloads:          (srv.workloads || []).map(w => `${w.name}${w.version ? ' ' + w.version : ''}`),
      cloud_provider:     srv.cloud_provider,
      region:             srv.region,
      instance_type:      srv.instance_type,
    }))

    // Workload consolidation (new format uses 'workload' not 'workload_name' etc)
    const wl_consolidation = (s.workload_consolidation || []).map(w => ({
      workload_name:          w.workload,
      current_server_count:   w.current_vm_count,
      recommended_server_count: w.recommended_vm_count,
      instances:              (w.servers || []).map(name => ({ server_name: name, server_ip: '', version: '', location: '' })),
      recommendation_note:    w.recommendation,
    }))

    // EOS advisories
    const eos_os = (s.eos_advisory_os || []).map(e => ({
      server_name:            e.server_name,
      server_ip:              e.ip_address,
      os:                     e.os_name,
      end_of_support:         e.end_of_support,
      end_of_extended_support: e.extended_support,
      migration_advisory:     e.migration_advisory,
    }))
    const eos_wl = (s.eos_advisory_workload || []).map(e => ({
      server_name:  e.server_name,
      server_ip:    e.ip_address,
      workload:     `${e.workload} ${e.version || ''}`.trim(),
      location:     '',
      end_of_support: e.end_of_support,
      end_of_extended_support: null,
    }))

    return {
      _newFormat: true,
      report_name:     raw.report_name,
      source_environment: raw.provider || '',
      target_cloud:    '',
      region:          '',
      summary,
      cloud_readiness: {
        cloud_ready:                 cr.cloud_ready || 0,
        cloud_ready_with_effort:     0,
        lift_and_shift:              cr.lift_and_shift || 0,
        smart_shift:                 cr.smart_shift || 0,
        smart_shift_with_effort:     0,
        paas_shift:                  cr.paas_shift || 0,
        paas_shift_with_effort:      0,
      },
      capacity_planning: cp,
      servers,
      pricing_plans: null,
      workload_consolidation: wl_consolidation,
      eos_advisories: { operating_systems: eos_os, workloads: eos_wl },
      // Extra new sections
      paas_recommendations: s.paas_recommendations || [],
      storage_recommendation: s.storage_recommendation || null,
      kubernetes_recommendation: s.kubernetes_recommendation || null,
      sustainability: s.sustainability || null,
      vm_flavors: s.vm_flavors || null,
      cloud_readiness_details: cr.details || [],
    }
  }

  // Legacy format â€” return as-is (old JSON upload)
  return { _newFormat: false, ...raw }
}

// â”€â”€ UI Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function StatCard({ label, value, sub, ring = 'border-slate-700' }) {
  return (
    <div className={`glass p-5 border ${ring}`}>
      <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

function Section({ title, children, defaultOpen = true, icon }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="glass overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-surface-hover transition-colors"
      >
        <h3 className="font-semibold text-white flex items-center gap-2">
          {icon && <span className="text-slate-400">{icon}</span>}
          {title}
        </h3>
        {open
          ? <ChevronUp size={15} className="text-slate-500 shrink-0" />
          : <ChevronDown size={15} className="text-slate-500 shrink-0" />
        }
      </button>
      {open && <div className="px-6 pb-6">{children}</div>}
    </div>
  )
}

function EOSBadge({ date }) {
  if (!date) return <span className="text-slate-600 text-xs">â€”</span>
  const diff = Math.floor((new Date(date) - Date.now()) / 86400000)
  if (diff < 0)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-red-950/60 text-red-300 border border-red-700/40">âš  Expired {date}</span>
  if (diff < 365)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-300 border border-amber-700/40">âš¡ {date}</span>
  return <span className="text-xs text-slate-400">{date}</span>
}

// â”€â”€ Main page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function ScanDetailPage() {
  const { scanId } = useParams()
  const navigate = useNavigate()
  const [scan, setScan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activePlan, setActivePlan] = useState(0)

  useEffect(() => {
    const load = async () => {
      try {
        // Try scanner job report first (live scan), then fall back to persisted scan
        let raw
        try {
          raw = await getScanReport(scanId)
        } catch {
          raw = await getScan(scanId)
        }
        setScan(normalizeReport(raw))
      } catch {
        toast.error('Failed to load scan')
        navigate('/')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scanId])

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(scan, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${(scan.report_name || 'infra_scan').replace(/\s+/g, '_')}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-brand-green border-r-transparent" />
      </div>
    )
  }

  if (!scan) return null

  const {
    summary, cloud_readiness, capacity_planning,
    servers, pricing_plans, workload_consolidation, eos_advisories,
    paas_recommendations, storage_recommendation, kubernetes_recommendation,
    sustainability, vm_flavors, cloud_readiness_details,
  } = scan

  const migrationChartData = [
    { name: 'Lift & Shift',    value: cloud_readiness?.lift_and_shift || 0,            fill: '#10b981' },
    { name: 'Smart Shift',     value: cloud_readiness?.smart_shift || 0,                fill: '#3b82f6' },
    { name: 'Smart (Effort)',  value: cloud_readiness?.smart_shift_with_effort || 0,    fill: '#f59e0b' },
    { name: 'PaaS',            value: cloud_readiness?.paas_shift || 0,                 fill: '#8b5cf6' },
    { name: 'PaaS (Effort)',   value: cloud_readiness?.paas_shift_with_effort || 0,     fill: '#6366f1' },
  ].filter(d => d.value > 0)

  const utilizationData = [
    { name: 'Underutilized', value: summary?.utilization_breakdown?.underutilized || 0, fill: '#f59e0b' },
    { name: 'Moderate',      value: summary?.utilization_breakdown?.moderate || 0,      fill: '#3b82f6' },
    { name: 'Utilized',      value: summary?.utilization_breakdown?.utilized || 0,      fill: '#10b981' },
    { name: 'Unknown',       value: summary?.utilization_breakdown?.unknown || 0,       fill: '#64748b' },
  ].filter(d => d.value > 0)

  const osChartData = summary?.os_distribution
    ? Object.entries(summary.os_distribution).map(([name, value], i) => ({
        name, value,
        fill: ['#3b82f6', '#f59e0b', '#10b981', '#8b5cf6', '#64748b'][i % 5],
      }))
    : []

  const capacityBarData = [
    { name: 'CPU Cores',
      'Equivalence Match': capacity_planning?.equivalence_match?.total_cpu_cores || 0,
      'Best Match':         capacity_planning?.best_match?.total_cpu_cores || 0 },
    { name: 'RAM (GB)',
      'Equivalence Match': capacity_planning?.equivalence_match?.total_ram_gb || 0,
      'Best Match':         capacity_planning?.best_match?.total_ram_gb || 0 },
  ]

  const currentPlan = pricing_plans?.[activePlan]

  const headerSubtitle = [
    scan.source_environment || 'Infrastructure Scan',
    scan.target_cloud && `-> ${scan.target_cloud}`,
    scan.region && `* ${scan.region}`,
  ].filter(Boolean).join(' ')

  return (
    <div className="min-h-screen bg-surface">
      <AppHeader
        title={scan.report_name}
        subtitle={headerSubtitle}
        backTo="/"
        rightSlot={
          <button onClick={handleExport} className="btn-ghost px-3 py-2 text-xs flex items-center gap-1.5">
            <Download size={13} /> Export JSON
          </button>
        }
      />

      <main className="max-w-7xl mx-auto px-5 py-8 space-y-5">

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Total Servers"
            value={summary?.total_servers ?? 0}
            sub={`${summary?.server_type || 'Virtual'} · ${summary?.boot_type || 'BIOS'}`}
            ring="border-blue-800/30"
          />
          <StatCard
            label="OS Families"
            value={summary?.os_count ?? 0}
            sub={summary?.ip_distribution_note || ''}
            ring="border-purple-800/30"
          />
          <StatCard
            label="Storage"
            value={`${summary?.storage_tb ?? 0} TB`}
            sub="Total disk size"
            ring="border-emerald-800/30"
          />
          <StatCard
            label="Cloud Ready"
            value={`${cloud_readiness?.cloud_ready ?? 0}/${summary?.total_servers ?? 0}`}
            sub={cloud_readiness?.cloud_ready_with_effort
              ? `+${cloud_readiness.cloud_ready_with_effort} with effort`
              : 'Ready for migration'}
            ring="border-amber-800/30"
          />
        </div>

        {/* Charts row */}
        <div className="grid md:grid-cols-2 gap-5">
          <Section title="Migration Strategy Breakdown">
            {migrationChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={migrationChartData} cx="50%" cy="50%" outerRadius={85}
                    dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                    {migrationChartData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={v => [`${v} servers`, '']} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-slate-500 text-sm py-12 text-center">No migration strategy data</p>
            )}
            <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs border-t border-surface-border pt-3">
              {[
                { label: 'Cloud Ready',          value: cloud_readiness?.cloud_ready,             color: 'text-emerald-400' },
                { label: 'Ready w/ Effort',      value: cloud_readiness?.cloud_ready_with_effort, color: 'text-teal-400' },
                { label: 'Lift & Shift',         value: cloud_readiness?.lift_and_shift,          color: 'text-green-400' },
                { label: 'Smart Shift',          value: cloud_readiness?.smart_shift,             color: 'text-blue-400' },
                { label: 'Smart Shift (Effort)', value: cloud_readiness?.smart_shift_with_effort, color: 'text-amber-400' },
                { label: 'PaaS Shift',           value: cloud_readiness?.paas_shift,              color: 'text-purple-400' },
                { label: 'PaaS (Effort)',        value: cloud_readiness?.paas_shift_with_effort,  color: 'text-indigo-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex justify-between py-0.5">
                  <span className="text-slate-400">{label}</span>
                  <span className={`font-semibold ${color}`}>{value ?? 0}</span>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Server Utilization">
            {utilizationData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={utilizationData} cx="50%" cy="50%" outerRadius={85}
                    dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                    {utilizationData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-slate-500 text-sm py-12 text-center">No utilization data</p>
            )}
          </Section>
        </div>

        {/* OS Distribution */}
        {osChartData.length > 0 && (
          <Section title="OS Distribution">
            <div className="grid md:grid-cols-2 gap-6">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={osChartData} cx="50%" cy="50%" outerRadius={80}
                    dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                    {osChartData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {osChartData.map(({ name, value, fill }) => (
                  <div key={name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full" style={{ background: fill }} />
                      <span className="text-slate-300">{name}</span>
                    </div>
                    <span className="font-semibold text-white">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Section>
        )}

        {/* Capacity Planning */}
        <Section title="Capacity Planning — Equivalence vs Best Match">
          <div className="grid md:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={capacityBarData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
                <Bar dataKey="Equivalence Match" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Best Match" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="space-y-3">
              {[
                { key: 'equivalence_match', label: 'Equivalence Match', color: 'blue' },
                { key: 'best_match', label: 'Best Match', color: 'emerald' },
              ].map(({ key, label, color }) => (
                <div key={key} className={`p-4 rounded-xl border border-${color}-800/30 bg-${color}-950/20`}>
                  <p className={`text-xs font-semibold text-${color}-400 uppercase tracking-wide mb-2`}>{label}</p>
                  <div className="grid grid-cols-2 gap-y-1 text-xs">
                    {[
                      ['Servers',   capacity_planning?.[key]?.total_servers],
                      ['CPU Cores', capacity_planning?.[key]?.total_cpu_cores],
                      ['RAM',       `${capacity_planning?.[key]?.total_ram_gb ?? '—'} GB`],
                      ['Disk',      `${capacity_planning?.[key]?.total_disk_tb ?? '—'} TB`],
                    ].map(([lbl, val]) => (
                      <><span key={lbl + 'l'} className="text-slate-400">{lbl}</span>
                      <span key={lbl + 'v'} className="text-white font-semibold">{val ?? '—'}</span></>
                    ))}
                  </div>
                  {key === 'best_match' && capacity_planning?.[key]?.estimated_saving_pct && (
                    <p className="text-xs text-emerald-400 mt-2 font-medium">
                      ~{capacity_planning[key].estimated_saving_pct}% estimated saving
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* Pricing Plans (legacy format) */}
        {pricing_plans?.length > 0 && (
          <Section title="Cloud Pricing Recommendations">
            <div className="flex gap-2 mb-5 flex-wrap">
              {pricing_plans.map((plan, i) => (
                <button key={i} onClick={() => setActivePlan(i)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    activePlan === i ? 'bg-brand-blue text-white' : 'bg-surface-hover text-slate-400 hover:text-white'
                  }`}>
                  {plan.plan_name}
                </button>
              ))}
            </div>
            {currentPlan && (
              <>
                <div className="grid sm:grid-cols-2 gap-4 mb-5">
                  <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-700/30">
                    <p className="text-xs text-slate-400 mb-1">Equivalence Match / month</p>
                    <p className="text-2xl font-bold text-white">
                      ${(currentPlan.equivalence_match_total_per_month || 0).toLocaleString()}
                      <span className="text-sm text-slate-400 font-normal">/mo</span>
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-700/30">
                    <p className="text-xs text-slate-400 mb-1">Best Match / month</p>
                    <p className="text-2xl font-bold text-white">
                      ${(currentPlan.best_match_total_per_month || 0).toLocaleString()}
                      <span className="text-sm text-slate-400 font-normal">/mo</span>
                    </p>
                  </div>
                </div>
                {currentPlan.flavors?.length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-surface-border text-slate-400">
                          {['Cloud','Flavor','OS','Family','Specs','Equiv. Match','Best Match'].map(h => (
                            <th key={h} className={`text-left py-2 pr-4 font-medium ${h.startsWith('Equiv') || h === 'Best Match' ? 'text-right' : ''}`}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {currentPlan.flavors.map((f, i) => (
                          <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-hover">
                            <td className="py-2 pr-4 text-slate-300">{f.cloud_name}</td>
                            <td className="py-2 pr-4 text-white font-mono text-xs">{f.flavor_name}</td>
                            <td className="py-2 pr-4 text-slate-400">{f.os_name}</td>
                            <td className="py-2 pr-4 text-slate-400">{f.flavor_family}</td>
                            <td className="py-2 pr-4 text-slate-400">{f.ram_gb}GB · {f.cpu_cores}C</td>
                            <td className="py-2 pr-4 text-right text-blue-300">
                              {f.equivalence_servers > 0 ? `${f.equivalence_servers}× $${(f.equivalence_cost_per_month || 0).toFixed(0)}` : '—'}
                            </td>
                            <td className="py-2 text-right text-emerald-300">
                              {f.best_servers > 0 ? `${f.best_servers}× $${(f.best_cost_per_month || 0).toFixed(0)}` : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </Section>
        )}

        {/* VM Flavors */}
        {vm_flavors?.flavors?.length > 0 && (
          <Section title="VM Size Profiles Discovered">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {vm_flavors.flavors.slice(0, 12).map((f, i) => (
                <div key={i} className="p-4 rounded-xl bg-surface-hover border border-surface-border">
                  <p className="text-sm font-medium text-white">{f.flavor}</p>
                  <p className="text-xs text-slate-400 mt-1">{f.count} server{f.count !== 1 ? 's' : ''}</p>
                  {f.servers?.length > 0 && (
                    <p className="text-xs text-slate-500 mt-1 truncate">{f.servers.join(', ')}</p>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* PaaS Recommendations */}
        {paas_recommendations?.length > 0 && (
          <Section title="PaaS Migration Candidates" icon={<Package size={16} />}>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-surface-border">
                    {['Server','IP','Workload','Version','PaaS Target','Benefit'].map(h => (
                      <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {paas_recommendations.map((r, i) => (
                    <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-hover">
                      <td className="py-2 pr-4 text-white font-medium">{r.server}</td>
                      <td className="py-2 pr-4 font-mono text-slate-400">{r.ip}</td>
                      <td className="py-2 pr-4 text-purple-300">{r.workload}</td>
                      <td className="py-2 pr-4 text-slate-400">{r.version || '—'}</td>
                      <td className="py-2 pr-4 text-slate-300 max-w-xs">{r.paas_target}</td>
                      <td className="py-2 text-slate-500">{r.benefit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        )}

        {/* Server Inventory */}
        {servers?.length > 0 && (
          <Section title={`Server Inventory (${servers.length})`} defaultOpen={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-border text-slate-400 text-xs">
                    {['IP / Hostname','Name','OS','Specs','Utilization','Migration','Workloads'].map(h => (
                      <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {servers.map((srv, i) => (
                    <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-hover">
                      <td className="py-2.5 pr-4 font-mono text-xs text-slate-400">{srv.ip}</td>
                      <td className="py-2.5 pr-4 text-white text-sm font-medium">
                        {srv.name}
                        {srv.cloud_provider && (
                          <span className="ml-2 text-xs text-slate-500">[{srv.cloud_provider}{srv.region ? ` · ${srv.region}` : ''}]</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-slate-400 text-xs">{srv.os}</td>
                      <td className="py-2.5 pr-4 text-xs text-slate-400">
                        {srv.cpu_cores ?? '?'}C · {srv.ram_gb ?? '?'}GB
                        {srv.disk_gb ? ` · ${srv.disk_gb}GB` : ''}
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          srv.utilization === 'underutilized' ? 'bg-amber-950/60 text-amber-300' :
                          srv.utilization === 'moderate'       ? 'bg-blue-950/60 text-blue-300' :
                          srv.utilization === 'utilized'       ? 'bg-emerald-950/60 text-emerald-300' :
                                                                  'bg-slate-700 text-slate-400'
                        }`}>
                          {srv.utilization || 'unknown'}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${MIGRATION_BADGE[srv.migration_strategy] || 'bg-slate-800 text-slate-300 border-slate-600/40'}`}>
                          {MIGRATION_LABELS[srv.migration_strategy] || srv.migration_strategy || '—'}
                        </span>
                      </td>
                      <td className="py-2.5 text-xs text-slate-400">
                        {Array.isArray(srv.workloads) ? srv.workloads.join(', ') || '—' : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        )}

        {/* Workload Consolidation */}
        {workload_consolidation?.length > 0 && (
          <Section title="Workload Consolidation Recommendations">
            <div className="space-y-4">
              {workload_consolidation.map((wl, i) => (
                <div key={i} className="p-4 rounded-xl bg-surface-hover border border-surface-border">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-8 w-8 rounded-lg bg-blue-900/50 flex items-center justify-center shrink-0">
                      <Server size={14} className="text-blue-300" />
                    </div>
                    <div>
                      <p className="font-semibold text-white text-sm">{wl.workload_name}</p>
                      <p className="text-xs text-slate-400">
                        Reduce from{' '}
                        <span className="text-amber-300 font-semibold">{wl.current_server_count}</span>{' '}
                        VMs to{' '}
                        <span className="text-emerald-300 font-semibold">{wl.recommended_server_count}</span>{' '}
                        VM{wl.recommended_server_count !== 1 ? 's' : ''}
                      </p>
                      {wl.recommendation_note && (
                        <p className="text-xs text-slate-500 mt-1">{wl.recommendation_note}</p>
                      )}
                    </div>
                  </div>
                  {wl.instances?.filter(inst => inst.server_name).length > 0 && (
                    <div className="overflow-x-auto mt-2">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-slate-500 border-b border-surface-border">
                            {['Server','IP','Version','Location'].map(h => (
                              <th key={h} className="text-left py-1.5 pr-4 font-medium">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {wl.instances.map((inst, j) => (
                            <tr key={j} className="border-b border-surface-border/30">
                              <td className="py-1.5 pr-4 text-slate-300">{inst.server_name}</td>
                              <td className="py-1.5 pr-4 font-mono text-slate-400">{inst.server_ip || '—'}</td>
                              <td className="py-1.5 pr-4 text-slate-400">{inst.version || '—'}</td>
                              <td className="py-1.5 font-mono text-slate-500">{inst.location || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Storage Recommendation */}
        {storage_recommendation && (
          <Section title="Storage Recommendations" defaultOpen={false}>
            <div className="grid sm:grid-cols-3 gap-4 mb-5">
              {[
                { label: 'Total Storage', value: `${storage_recommendation.total_storage_tb} TB`, color: 'blue' },
                { label: 'HDD', value: `${storage_recommendation.hdd_storage_tb} TB`, color: 'amber' },
                { label: 'SSD', value: `${storage_recommendation.ssd_storage_tb} TB`, color: 'emerald' },
              ].map(({ label, value, color }) => (
                <div key={label} className={`p-4 rounded-xl bg-${color}-950/20 border border-${color}-800/30`}>
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className={`text-2xl font-bold text-${color}-300`}>{value}</p>
                </div>
              ))}
            </div>
            <div className="space-y-3">
              {storage_recommendation.recommendations?.map((r, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-surface-hover">
                  <div className="shrink-0 mt-0.5 h-6 w-6 rounded bg-blue-900/50 flex items-center justify-center">
                    <span className="text-blue-300 text-xs font-bold">{i + 1}</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{r.type}</p>
                    <p className="text-xs text-slate-400">{r.target} · {r.applicable_tb} TB applicable</p>
                    <p className="text-xs text-slate-500 mt-0.5">{r.notes}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Kubernetes */}
        {kubernetes_recommendation?.containerization_candidates > 0 && (
          <Section title="Kubernetes / Containerization Opportunities" defaultOpen={false}>
            <div className="grid sm:grid-cols-3 gap-4 mb-5">
              <StatCard label="Container Candidates" value={kubernetes_recommendation.containerization_candidates} />
              {kubernetes_recommendation.recommended_cluster && (
                <>
                  <StatCard label="Recommended Nodes"
                    value={kubernetes_recommendation.recommended_cluster.node_count}
                    sub={kubernetes_recommendation.recommended_cluster.node_type} />
                  <StatCard label="Total CPU Request"
                    value={kubernetes_recommendation.recommended_cluster.total_cpu_request}
                    sub={`${kubernetes_recommendation.recommended_cluster.total_memory_request_mi} Mi memory`} />
                </>
              )}
            </div>
            {kubernetes_recommendation.candidates?.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-surface-border">
                      {['Server','Workload','Type','Pods','CPU Req','Mem Req'].map(h => (
                        <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {kubernetes_recommendation.candidates.map((c, i) => (
                      <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-hover">
                        <td className="py-2 pr-4 text-white">{c.server}</td>
                        <td className="py-2 pr-4 text-slate-300">{c.workload}</td>
                        <td className="py-2 pr-4 text-slate-400">{c.workload_type}</td>
                        <td className="py-2 pr-4 text-slate-400">{c.recommended_pods}</td>
                        <td className="py-2 pr-4 text-emerald-300">{c.cpu_request}</td>
                        <td className="py-2 text-blue-300">{c.memory_request}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        )}

        {/* Sustainability */}
        {sustainability && (
          <Section title="Sustainability & CO₂ Reduction" icon={<Leaf size={16} />} defaultOpen={false}>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Current Power',     value: `${sustainability.current_power_w} W`,          sub: 'estimated',  color: 'red' },
                { label: 'Cloud Equivalent',  value: `${sustainability.cloud_equivalent_power_w} W`,  sub: 'estimated',  color: 'blue' },
                { label: 'Annual kWh Saving', value: sustainability.annual_power_saving_kwh?.toLocaleString(), sub: 'kWh/year', color: 'emerald' },
                { label: 'CO₂ Reduction',     value: `${sustainability.annual_co2_saving_tonnes} t`,  sub: 'CO₂/year',   color: 'green' },
              ].map(({ label, value, sub, color }) => (
                <div key={label} className={`p-4 rounded-xl bg-${color}-950/20 border border-${color}-800/30`}>
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className={`text-2xl font-bold text-${color}-300`}>{value}</p>
                  <p className="text-xs text-slate-500 mt-1">{sub}</p>
                </div>
              ))}
            </div>
            {sustainability.notes && (
              <p className="text-xs text-slate-500 mt-4">{sustainability.notes}</p>
            )}
          </Section>
        )}

        {/* EOS Advisories */}
        {(eos_advisories?.operating_systems?.length > 0 || eos_advisories?.workloads?.length > 0) && (
          <Section title="End of Support Advisories" icon={<AlertTriangle size={16} />}>
            {eos_advisories.operating_systems?.length > 0 && (
              <div className="mb-6">
                <p className="text-sm font-semibold text-slate-300 mb-3">
                  Operating Systems ({eos_advisories.operating_systems.length})
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-slate-400 border-b border-surface-border">
                        {['Server','IP','OS','End of Support','Extended EOS','Recommendation'].map(h => (
                          <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {eos_advisories.operating_systems.map((item, i) => (
                        <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-hover">
                          <td className="py-2 pr-4 text-white font-medium">{item.server_name}</td>
                          <td className="py-2 pr-4 font-mono text-slate-400">{item.server_ip || '—'}</td>
                          <td className="py-2 pr-4 text-slate-300">{item.os || item.os_name}</td>
                          <td className="py-2 pr-4"><EOSBadge date={item.end_of_support} /></td>
                          <td className="py-2 pr-4"><EOSBadge date={item.end_of_extended_support} /></td>
                          <td className="py-2 text-slate-400 max-w-xs leading-relaxed">{item.migration_advisory}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {eos_advisories.workloads?.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-slate-300 mb-3">
                  Workloads ({eos_advisories.workloads.length})
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-slate-400 border-b border-surface-border">
                        {['Server','IP','Workload','Location','End of Support','Extended EOS'].map(h => (
                          <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {eos_advisories.workloads.map((item, i) => (
                        <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-hover">
                          <td className="py-2 pr-4 text-white font-medium">{item.server_name}</td>
                          <td className="py-2 pr-4 font-mono text-slate-400">{item.server_ip || '—'}</td>
                          <td className="py-2 pr-4 text-slate-300">{item.workload}</td>
                          <td className="py-2 pr-4 font-mono text-slate-500">{item.location || '—'}</td>
                          <td className="py-2 pr-4"><EOSBadge date={item.end_of_support} /></td>
                          <td className="py-2"><EOSBadge date={item.end_of_extended_support} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </Section>
        )}

      </main>
    </div>
  )
}
