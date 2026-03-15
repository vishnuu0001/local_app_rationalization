import { useState, useEffect, createContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import DashboardPage from './pages/DashboardPage.jsx'
import NewScanPage from './pages/NewScanPage.jsx'
import ScanProgressPage from './pages/ScanProgressPage.jsx'
import ScanDetailPage from './pages/ScanDetailPage.jsx'
import {
  clearPortalToken,
  consumePortalTokenFromHash,
  getPortalLoginUrl,
  getPortalToken,
  validateSession,
} from './api/client.js'

export const AppContext = createContext(null)

export default function App() {
  const [authReady, setAuthReady] = useState(false)
  const [authUser, setAuthUser] = useState(null)
  const [authError, setAuthError] = useState('')

  useEffect(() => {
    let active = true
    const bootstrap = async () => {
      consumePortalTokenFromHash()
      const token = getPortalToken()
      if (!token) {
        if (active) {
          setAuthError('No active portal session. Open this module from the StratApp portal.')
          setAuthReady(true)
        }
        return
      }
      try {
        const session = await validateSession()
        if (active) setAuthUser(session.user)
      } catch (err) {
        clearPortalToken()
        if (active)
          setAuthError(err?.response?.data?.error || 'Session expired or access denied for Infra Scan.')
      } finally {
        if (active) setAuthReady(true)
      }
    }
    bootstrap()
    return () => { active = false }
  }, [])

  if (!authReady) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-brand-green border-r-transparent mb-4" />
          <p className="text-slate-400 text-sm">Authenticating…</p>
        </div>
      </div>
    )
  }

  if (!authUser) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-4">
        <div className="glass p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">🔐</div>
          <h2 className="text-xl font-semibold text-white mb-2">Access Required</h2>
          <p className="text-slate-400 text-sm mb-6">{authError}</p>
          <a
            href={getPortalLoginUrl()}
            className="inline-block btn-primary px-6 py-3 rounded-xl text-sm font-semibold"
          >
            Go to Portal Login
          </a>
        </div>
      </div>
    )
  }

  return (
    <AppContext.Provider value={{ user: authUser }}>
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/new-scan" element={<NewScanPage />} />
          <Route path="/upload" element={<NewScanPage />} />
          <Route path="/scans/progress/:scanId" element={<ScanProgressPage />} />
          <Route path="/scans/:scanId" element={<ScanDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AppContext.Provider>
  )
}
