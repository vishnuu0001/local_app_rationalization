import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  LayoutPanelTop,
  LogOut,
  Rocket,
  Sparkles,
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';

const APP_RATIONALIZATION = 'APP_RATIONALIZATION';
const CODE_ANALYSIS = 'CODE_ANALYSIS';

const codeAnalysisUrl =
  process.env.REACT_APP_CODE_ANALYSIS_URL ||
  'http://localhost:5173';

const launchGuidance = [
  'Launch App Rationalization to work with inventory, correlation, templates, capability mapping, and traceability.',
  'Launch Code Analysis to inspect repository health, debt, architecture, and migration readiness.',
  'Module access remains controlled by the permissions assigned to the signed-in user.',
];

const LaunchModulesPage = () => {
  const navigate = useNavigate();
  const { user, token, hasAccess, logout } = useAuth();

  const canUseAppRationalization = hasAccess(APP_RATIONALIZATION);
  const canUseCodeAnalysis = hasAccess(CODE_ANALYSIS);

  const openCodeAnalysis = () => {
    if (!token) {
      return;
    }

    const hash = `#authToken=${encodeURIComponent(token)}`;
    window.location.assign(`${codeAnalysisUrl}${hash}`);
  };

  const onLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="portal-app-shell">
      <div className="portal-content">
        <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
          <div className="portal-page-width px-5 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-sky-500 flex items-center justify-center shadow-lg shadow-cyan-950/30">
                <LayoutPanelTop size={20} className="text-white" />
              </div>
              <div>
                <p className="portal-section-label">Launch modules</p>
                <h1 className="text-2xl font-semibold text-white">Open the right workspace for the next decision</h1>
              </div>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-slate-300">Signed in as {user?.username}</span>
              <span className="portal-chip hidden lg:inline-flex">
                <Sparkles size={14} className="text-cyan-300" />
                Dedicated launcher
              </span>
              <button
                type="button"
                onClick={() => navigate('/home')}
                className="portal-btn-secondary px-4 py-2 rounded-xl text-sm font-medium inline-flex items-center gap-2"
              >
                <ArrowLeft size={15} />
                Homepage
              </button>
              {user?.role === 'admin' && (
                <button
                  type="button"
                  onClick={() => navigate('/admin')}
                  className="portal-btn-secondary px-4 py-2 rounded-xl text-sm font-medium"
                >
                  Admin Console
                </button>
              )}
              <button
                type="button"
                onClick={onLogout}
                className="portal-btn-danger px-4 py-2 rounded-xl text-sm font-medium inline-flex items-center gap-2"
              >
                <LogOut size={15} />
                Logout
              </button>
            </div>
          </div>
        </header>

        <main className="portal-page-width px-5 py-10 space-y-8">
          <section className="grid xl:grid-cols-[0.34fr_0.66fr] gap-6 items-start">
            <article className="portal-panel-soft rounded-[28px] p-6 lg:p-7">
              <p className="portal-section-label">Launch guidance</p>
              <h2 className="mt-3 text-2xl font-semibold text-white">Use the launcher as the module entry point</h2>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                This page centralizes application entry so users can move directly into the correct workspace while retaining portal session and access policy.
              </p>

              <div className="mt-6 space-y-3">
                {launchGuidance.map((item) => (
                  <div key={item} className="portal-note p-4">
                    <p className="text-xs leading-6 text-slate-300">{item}</p>
                  </div>
                ))}
              </div>

              <div className="portal-illustration-frame mt-6 p-3">
                <img
                  src="/manufacturing-modernization.svg"
                  alt="Launch page manufacturing illustration"
                  className="w-full rounded-[18px] object-cover"
                />
              </div>
            </article>

            <section>
              <div className="grid md:grid-cols-2 gap-6">
                <article className="portal-panel rounded-[28px] p-6 flex flex-col">
                  <div className="portal-illustration-frame h-44 p-3">
                    <img
                      src="/manufacturing-modernization.svg"
                      alt="App Rationalization workspace preview"
                      className="h-full w-full rounded-[18px] object-cover"
                    />
                  </div>
                  <div className="mt-5 flex items-center justify-between gap-3">
                    <div>
                      <p className="portal-section-label">Module 01</p>
                      <h3 className="mt-2 text-xl font-semibold text-white">App Rationalization</h3>
                    </div>
                    <span className="portal-chip">Manufacturing estate</span>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-slate-300 flex-1">
                    Upload infrastructure and application datasets, align templates, build correlation views,
                    and generate capability and traceability decisions for portfolio action.
                  </p>
                  <button
                    type="button"
                    disabled={!canUseAppRationalization}
                    onClick={() => navigate('/app-rationalization')}
                    className="portal-btn-primary mt-6 px-4 py-3 rounded-xl text-sm font-semibold inline-flex items-center justify-center gap-2"
                  >
                    {canUseAppRationalization ? 'Open App Rationalization' : 'Access Not Granted'}
                    {canUseAppRationalization && <ArrowRight size={16} />}
                  </button>
                </article>

                <article className="portal-panel rounded-[28px] p-6 flex flex-col">
                  <div className="portal-illustration-frame h-44 p-3">
                    <img
                      src="/code-analysis-graph.svg"
                      alt="Code Analysis workspace preview"
                      className="h-full w-full rounded-[18px] object-cover"
                    />
                  </div>
                  <div className="mt-5 flex items-center justify-between gap-3">
                    <div>
                      <p className="portal-section-label">Module 02</p>
                      <h3 className="mt-2 text-xl font-semibold text-white">Code Analysis</h3>
                    </div>
                    <span className="portal-chip">Repository intelligence</span>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-slate-300 flex-1">
                    Analyze repositories for modernization debt, architecture health, dependency posture,
                    and cloud migration readiness before committing to roadmap choices.
                  </p>
                  <button
                    type="button"
                    disabled={!canUseCodeAnalysis}
                    onClick={openCodeAnalysis}
                    className="portal-btn-primary mt-6 px-4 py-3 rounded-xl text-sm font-semibold inline-flex items-center justify-center gap-2"
                  >
                    {canUseCodeAnalysis ? 'Open Code Analysis' : 'Access Not Granted'}
                    {canUseCodeAnalysis && <ArrowRight size={16} />}
                  </button>
                </article>
              </div>

              <div className="portal-note mt-6 p-5 flex items-start gap-3">
                <div className="h-10 w-10 rounded-2xl bg-indigo-500/15 border border-indigo-400/15 flex items-center justify-center shrink-0">
                  <Rocket size={18} className="text-indigo-300" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">Launch behavior</p>
                  <p className="mt-2 text-xs leading-6 text-slate-400">
                    Both modules open in the same browser window and reuse the current portal session. Code Analysis continues to receive the signed session token during navigation.
                  </p>
                </div>
              </div>
            </section>
          </section>
        </main>
      </div>
    </div>
  );
};

export default LaunchModulesPage;