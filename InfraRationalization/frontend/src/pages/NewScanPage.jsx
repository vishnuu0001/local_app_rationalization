import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Cloud, Network, Database } from 'lucide-react'
import toast from 'react-hot-toast'
import { startScan } from '../api/client.js'
import AppHeader from '../components/AppHeader.jsx'

const TABS = [
  { id: 'onprem', label: 'On-Premises', icon: Network },
  { id: 'aws',    label: 'AWS',         icon: Cloud },
  { id: 'azure',  label: 'Azure',       icon: Cloud },
  { id: 'gcp',    label: 'GCP',         icon: Cloud },
  { id: 'multi',  label: 'Multi-Cloud', icon: Database },
]

const Field = ({ label, type = 'text', value, onChange, placeholder = '', hint = '' }) => (
  <div>
    <label className="block text-xs font-medium text-slate-300 mb-1">{label}</label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
    />
    {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
  </div>
)

const Section = ({ title, children }) => (
  <div className="space-y-4">
    <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-widest border-b border-slate-700 pb-2">{title}</h3>
    {children}
  </div>
)

export default function NewScanPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('onprem')
  const [reportName, setReportName] = useState('')
  const [loading, setLoading] = useState(false)

  // OnPrem
  const [networkRange, setNetworkRange] = useState('192.168.1.0/24')
  const [sshUser, setSshUser] = useState('')
  const [sshPass, setSshPass] = useState('')
  const [sshKey, setSshKey] = useState('')
  const [winrmUser, setWinrmUser] = useState('')
  const [winrmPass, setWinrmPass] = useState('')

  // AWS
  const [awsKey, setAwsKey] = useState('')
  const [awsSecret, setAwsSecret] = useState('')
  const [awsRegions, setAwsRegions] = useState('us-east-1,eu-west-1')

  // Azure
  const [azTenant, setAzTenant] = useState('')
  const [azClient, setAzClient] = useState('')
  const [azSecret, setAzSecret] = useState('')
  const [azSub, setAzSub] = useState('')

  // GCP
  const [gcpProject, setGcpProject] = useState('')
  const [gcpSaJson, setGcpSaJson] = useState('')
  const [gcpRegions, setGcpRegions] = useState('us-central1')

  // Options
  const [deepScan, setDeepScan] = useState(true)
  const [portScan, setPortScan] = useState(true)
  const [timeout, setTimeout_] = useState('30')

  const handleSubmit = async () => {
    const name = reportName.trim() || `Scan ${new Date().toLocaleString()}`
    const base = {
      provider: tab,
      report_name: name,
      deep_scan: deepScan,
      port_scan: portScan,
      timeout_seconds: parseInt(timeout) || 30,
    }

    let payload = { ...base }

    if (tab === 'onprem' || tab === 'multi') {
      payload = {
        ...payload,
        network_range: networkRange.trim(),
        ssh_username: sshUser.trim(),
        ssh_password: sshPass,
        ssh_key_path: sshKey.trim(),
        winrm_username: winrmUser.trim(),
        winrm_password: winrmPass,
      }
    }
    if (tab === 'aws' || tab === 'multi') {
      payload = {
        ...payload,
        aws_access_key_id: awsKey.trim(),
        aws_secret_access_key: awsSecret,
        aws_regions: awsRegions.split(',').map(r => r.trim()).filter(Boolean),
      }
    }
    if (tab === 'azure' || tab === 'multi') {
      payload = {
        ...payload,
        azure_tenant_id: azTenant.trim(),
        azure_client_id: azClient.trim(),
        azure_client_secret: azSecret,
        azure_subscription_id: azSub.trim(),
      }
    }
    if (tab === 'gcp' || tab === 'multi') {
      payload = {
        ...payload,
        gcp_project_id: gcpProject.trim(),
        gcp_service_account_json: gcpSaJson.trim(),
        gcp_regions: gcpRegions.split(',').map(r => r.trim()).filter(Boolean),
      }
    }

    setLoading(true)
    try {
      const { scan_id } = await startScan(payload)
      toast.success('Scan started!')
      navigate(`/scans/progress/${scan_id}`)
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to start scan')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <AppHeader title="New Infrastructure Scan" subtitle="Configure your scan target and credentials" backTo="/" />

      <main className="max-w-4xl mx-auto px-5 py-8 space-y-6">
        {/* Report name */}
        <div className="glass p-6">
          <Field
            label="Report Name"
            value={reportName}
            onChange={setReportName}
            placeholder={`Infrastructure Scan — ${new Date().toLocaleDateString()}`}
          />
        </div>

        {/* Provider tabs */}
        <div className="glass p-6 space-y-6">
          <div className="flex gap-2 flex-wrap">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                  tab === id
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>

          {/* OnPrem fields */}
          {(tab === 'onprem' || tab === 'multi') && (
            <Section title="On-Premises Network">
              <Field
                label="CIDR Range"
                value={networkRange}
                onChange={setNetworkRange}
                placeholder="192.168.1.0/24"
                hint="Network range to scan. Use /24 to scan up to 254 hosts."
              />
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="SSH Username" value={sshUser} onChange={setSshUser} placeholder="root" />
                <Field label="SSH Password" type="password" value={sshPass} onChange={setSshPass} placeholder="••••••••" />
              </div>
              <Field
                label="SSH Private Key Path (optional)"
                value={sshKey}
                onChange={setSshKey}
                placeholder="/home/user/.ssh/id_rsa"
              />
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="WinRM Username (Windows)" value={winrmUser} onChange={setWinrmUser} placeholder="Administrator" />
                <Field label="WinRM Password" type="password" value={winrmPass} onChange={setWinrmPass} placeholder="••••••••" />
              </div>
            </Section>
          )}

          {/* AWS fields */}
          {(tab === 'aws' || tab === 'multi') && (
            <Section title="AWS Credentials">
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Access Key ID" value={awsKey} onChange={setAwsKey} placeholder="AKIA..." />
                <Field label="Secret Access Key" type="password" value={awsSecret} onChange={setAwsSecret} placeholder="••••••••" />
              </div>
              <Field
                label="Regions (comma separated)"
                value={awsRegions}
                onChange={setAwsRegions}
                placeholder="us-east-1,eu-west-1,ap-south-1"
              />
            </Section>
          )}

          {/* Azure fields */}
          {(tab === 'azure' || tab === 'multi') && (
            <Section title="Azure Credentials">
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Tenant ID" value={azTenant} onChange={setAzTenant} placeholder="xxxxxxxx-xxxx-..." />
                <Field label="Client ID (App Registration)" value={azClient} onChange={setAzClient} placeholder="xxxxxxxx-xxxx-..." />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Client Secret" type="password" value={azSecret} onChange={setAzSecret} placeholder="••••••••" />
                <Field label="Subscription ID" value={azSub} onChange={setAzSub} placeholder="xxxxxxxx-xxxx-..." />
              </div>
            </Section>
          )}

          {/* GCP fields */}
          {(tab === 'gcp' || tab === 'multi') && (
            <Section title="GCP Credentials">
              <Field
                label="Project ID"
                value={gcpProject}
                onChange={setGcpProject}
                placeholder="my-gcp-project-123"
              />
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Service Account JSON</label>
                <textarea
                  value={gcpSaJson}
                  onChange={e => setGcpSaJson(e.target.value)}
                  rows={4}
                  placeholder='{ "type": "service_account", ... }'
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <Field
                label="Regions (comma separated)"
                value={gcpRegions}
                onChange={setGcpRegions}
                placeholder="us-central1,europe-west1"
              />
            </Section>
          )}
        </div>

        {/* Scan options */}
        <div className="glass p-6">
          <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-widest border-b border-slate-700 pb-2 mb-4">
            Scan Options
          </h3>
          <div className="grid sm:grid-cols-3 gap-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={deepScan}
                onChange={e => setDeepScan(e.target.checked)}
                className="accent-emerald-500 w-4 h-4"
              />
              <div>
                <p className="text-sm text-white font-medium">Deep Scan</p>
                <p className="text-xs text-slate-400">SSH/WinRM enrichment</p>
              </div>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={portScan}
                onChange={e => setPortScan(e.target.checked)}
                className="accent-emerald-500 w-4 h-4"
              />
              <div>
                <p className="text-sm text-white font-medium">Port Scan</p>
                <p className="text-xs text-slate-400">nmap service detection</p>
              </div>
            </label>
            <Field
              label="Timeout (seconds)"
              type="number"
              value={timeout}
              onChange={setTimeout_}
              placeholder="30"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={() => navigate('/')}
            className="btn-ghost px-5 py-2.5 rounded-xl text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="btn-primary px-6 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 disabled:opacity-60"
          >
            {loading ? (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-r-transparent" />
            ) : (
              <Play size={15} />
            )}
            {loading ? 'Starting…' : 'Start Scan'}
          </button>
        </div>
      </main>
    </div>
  )
}
