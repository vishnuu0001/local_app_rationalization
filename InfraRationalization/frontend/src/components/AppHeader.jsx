import { useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { Server, LogOut, Home, ArrowLeft, ScanSearch, ShieldCheck } from 'lucide-react'
import { AppContext } from '../App.jsx'
import { getPortalHomeUrl, logoutFromPortal } from '../api/client.js'

/**
 * Shared top navigation bar for all Infra Scan pages.
 *
 * Props:
 *   title      – main heading text
 *   subtitle   – optional secondary info shown below title
 *   backTo     – if provided, shows a ← back arrow button routing to this path
 *   rightSlot  – optional JSX rendered between the chip and Portal button (e.g. Export button)
 */
export default function AppHeader({ title, subtitle, backTo, rightSlot }) {
  const { user } = useContext(AppContext)
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-30 border-b border-surface-border bg-surface/90 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-5 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 flex-wrap">

        {/* ── Left: icon + labels ── */}
        <div className="flex items-center gap-3">
          {backTo && (
            <button
              onClick={() => navigate(backTo)}
              className="btn-ghost p-2 rounded-xl shrink-0"
              aria-label="Back"
            >
              <ArrowLeft size={17} />
            </button>
          )}
          <div className="h-11 w-11 rounded-2xl bg-gradient-brand flex items-center justify-center shadow-lg shadow-emerald-950/40 shrink-0">
            <Server size={20} className="text-white" />
          </div>
          <div>
            <p className="text-xs font-semibold text-emerald-400 uppercase tracking-widest">Module 03</p>
            <h1 className="text-xl font-semibold text-white leading-tight">{title}</h1>
            {subtitle && (
              <p className="text-xs text-slate-500 mt-0.5 truncate max-w-xs md:max-w-lg">{subtitle}</p>
            )}
          </div>
        </div>

        {/* ── Right: user info + nav buttons ── */}
        <div className="flex items-center gap-2 text-sm flex-wrap">

          {/* Signed in as */}
          {user?.username && (
            <span className="text-slate-400 text-xs hidden sm:inline px-1">
              Signed in as <span className="text-slate-200 font-medium">{user.username}</span>
            </span>
          )}

          {/* Chip */}
          <span className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-emerald-700/40 bg-emerald-950/30 text-emerald-300 text-xs font-medium">
            <ScanSearch size={13} />
            Infra Scanner
          </span>

          {/* Extra slot (e.g. Export button on detail page) */}
          {rightSlot}

          {/* ← Dashboard (only on sub-pages) */}
          {backTo && backTo !== '/' && (
            <button
              onClick={() => navigate('/')}
              className="btn-ghost px-3 py-2 text-xs flex items-center gap-1.5"
            >
              <Home size={13} /> Dashboard
            </button>
          )}

          {/* Portal home */}
          <a
            href={getPortalHomeUrl()}
            className="btn-ghost px-3 py-2 text-xs flex items-center gap-1.5"
          >
            <Home size={13} /> Portal
          </a>

          {/* Admin Console (admin users only) */}
          {user?.role === 'admin' && (
            <a
              href={`${getPortalHomeUrl().replace('/home', '')}/admin`}
              className="btn-ghost px-3 py-2 text-xs flex items-center gap-1.5"
            >
              <ShieldCheck size={13} /> Admin Console
            </a>
          )}

          {/* Logout */}
          <button
            onClick={logoutFromPortal}
            className="px-3 py-2 text-xs rounded-xl flex items-center gap-1.5 font-medium
                       bg-red-950/40 text-red-400 border border-red-800/40
                       hover:bg-red-900/50 hover:text-red-300 transition-colors"
          >
            <LogOut size={13} /> Logout
          </button>
        </div>
      </div>
    </header>
  )
}
