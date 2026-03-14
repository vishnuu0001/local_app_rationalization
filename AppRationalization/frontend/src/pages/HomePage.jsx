import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BarChart3,
  Bot,
  Factory,
  GitBranch,
  LayoutPanelTop,
  LogOut,
  Network,
  Rocket,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';

const businessThemes = [
  {
    icon: Factory,
    title: 'Landscape baseline',
    description: 'Inventory applications, plant systems, integrations, and support footprints across the manufacturing estate.',
  },
  {
    icon: ShieldCheck,
    title: 'Risk posture',
    description: 'Expose duplication, unsupported technologies, and operational fragility before transformation spend is committed.',
  },
  {
    icon: Rocket,
    title: 'Action path',
    description: 'Sequence retain, retire, rehost, replatform, or replace decisions with business and engineering evidence.',
  },
];

const executionFlow = [
  {
    title: 'Collect enterprise signals',
    description: 'Bring together inventory, CAST findings, industry templates, and correlation views into a single workspace.',
  },
  {
    title: 'Add code-level evidence',
    description: 'Use Code Analysis to quantify health, debt, architecture, OSS risk, and cloud fitment before roadmap decisions.',
  },
  {
    title: 'Drive modernization choices',
    description: 'Translate insight into clear capability maps, traceability, and priority actions for manufacturing portfolios.',
  },
];

const HomePage = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

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
                <Factory size={20} className="text-white" />
              </div>
              <div>
                <p className="portal-section-label">Unified Modernization Workspace</p>
                <h1 className="text-2xl font-semibold text-white">Application Rationalization Portal</h1>
              </div>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-slate-300">Signed in as {user?.username}</span>
              <span className="portal-chip hidden lg:inline-flex">
                <Sparkles size={14} className="text-cyan-300" />
                Manufacturing modernization
              </span>
              <button
                type="button"
                onClick={() => navigate('/launch-modules')}
                className="portal-btn-secondary px-4 py-2 rounded-xl text-sm font-medium inline-flex items-center gap-2"
              >
                <LayoutPanelTop size={15} />
                Launch Modules
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

        <main className="portal-page-width px-5 py-10 space-y-10">
          <section className="grid xl:grid-cols-[1.18fr_0.82fr] gap-6">
            <article className="portal-glass rounded-[28px] p-8 lg:p-10">
              <div className="flex flex-wrap gap-2">
                <span className="portal-chip">
                  <Network size={14} className="text-cyan-300" />
                  Portfolio evidence
                </span>
                <span className="portal-chip">
                  <GitBranch size={14} className="text-indigo-300" />
                  Rationalization decisions
                </span>
                <span className="portal-chip">
                  <Bot size={14} className="text-sky-300" />
                  AI-assisted insights
                </span>
              </div>

              <h2 className="mt-6 text-4xl lg:text-5xl font-semibold leading-tight text-white max-w-4xl">
                Manufacturing modernization with
                <span className="portal-accent-text"> portfolio-wide evidence</span>
              </h2>

              <p className="mt-5 max-w-4xl text-sm lg:text-base leading-8 text-slate-300">
                Manufacturing organizations operate a dense mix of ERP platforms, plant systems, quality tooling,
                engineering applications, and bespoke integrations. This portal brings business rationalization and
                code-level intelligence together so modernization plans are grounded in cost, risk, technical debt,
                and operational criticality rather than intuition alone.
              </p>

              <div className="mt-8 grid md:grid-cols-3 gap-4">
                {businessThemes.map(({ icon: Icon, title, description }) => (
                  <div key={title} className="portal-stat-card">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-2xl bg-cyan-400/10 border border-cyan-300/10 flex items-center justify-center">
                        <Icon size={18} className="text-cyan-300" />
                      </div>
                      <p className="text-base font-semibold text-white">{title}</p>
                    </div>
                    <p className="mt-3 text-sm leading-7 text-slate-400">{description}</p>
                  </div>
                ))}
              </div>

              <div className="mt-8 grid lg:grid-cols-[0.72fr_1fr] gap-4 items-stretch">
                <div className="portal-panel-soft rounded-[24px] p-5">
                  <p className="portal-section-label">Decision path</p>
                  <div className="mt-4 space-y-4">
                    {executionFlow.map((step, index) => (
                      <div key={step.title} className="flex gap-3">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-xs font-bold text-white shrink-0">
                          {index + 1}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-white">{step.title}</p>
                          <p className="mt-1 text-xs leading-6 text-slate-400">{step.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="portal-illustration-frame min-h-[260px] p-4 flex items-center justify-center">
                  <img
                    src="/manufacturing-modernization.svg"
                    alt="Manufacturing application rationalization illustration"
                    className="w-full h-full object-cover rounded-[20px] portal-float"
                  />
                </div>
              </div>
            </article>

            <article className="portal-panel rounded-[28px] p-7 lg:p-8 flex flex-col gap-6">
              <div>
                <p className="portal-section-label">Code intelligence</p>
                <h3 className="mt-3 text-2xl font-semibold text-white">How Code Analysis sharpens rationalization</h3>
                <p className="mt-4 text-sm leading-7 text-slate-300">
                  Code Analysis adds the engineering lens: architecture shape, technical debt, cloud readiness,
                  dependency risk, sustainability signals, and modernization effort. That context helps teams separate
                  what should be optimized from what should be retired, and what requires deeper redesign before migration.
                </p>
              </div>

              <div className="portal-illustration-frame p-3">
                <img
                  src="/code-analysis-graph.svg"
                  alt="Code analysis intelligence illustration"
                  className="w-full rounded-[20px] object-cover"
                />
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div className="portal-stat-card">
                  <div className="flex items-center gap-3">
                    <BarChart3 size={18} className="text-cyan-300" />
                    <p className="text-base font-semibold text-white">Portfolio scoring</p>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-slate-400">Compare health, debt, cloud fitment, and business impact across repositories.</p>
                </div>
                <div className="portal-stat-card">
                  <div className="flex items-center gap-3">
                    <ShieldCheck size={18} className="text-indigo-300" />
                    <p className="text-base font-semibold text-white">Risk visibility</p>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-slate-400">Surface vulnerable dependencies, stale stacks, and architecture hotspots early.</p>
                </div>
              </div>
            </article>
          </section>

          <section className="grid lg:grid-cols-[0.74fr_1.26fr] gap-6 items-start">
            <article className="portal-panel-soft rounded-[28px] p-6 lg:p-7">
              <p className="portal-section-label">Operating model</p>
              <h3 className="mt-3 text-2xl font-semibold text-white">One secure launch point for business and engineering teams</h3>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                Use the portal as the common control surface for portfolio managers, enterprise architects, and modernization leads.
                Launch the module you need, carry your access policy with you, and move across rationalization and code analysis without breaking session context.
              </p>
              <div className="mt-6 space-y-3">
                <div className="portal-note p-4">
                  <p className="text-sm font-semibold text-white">Shared identity and access</p>
                  <p className="mt-1 text-xs leading-6 text-slate-400">Role-based access defines who can launch each module and who can administer user permissions.</p>
                </div>
                <div className="portal-note p-4">
                  <p className="text-sm font-semibold text-white">Evidence-backed decisioning</p>
                  <p className="mt-1 text-xs leading-6 text-slate-400">Combine infrastructure data, template alignment, traceability, and code intelligence into one modernization story.</p>
                </div>
              </div>
            </article>

            <article className="portal-panel rounded-[28px] p-7 lg:p-8 flex flex-col gap-6">
              <div>
                <p className="portal-section-label">Launch modules</p>
                <h2 className="mt-3 text-2xl font-semibold text-white">Open the right workspace from a dedicated launch page</h2>
                <p className="mt-4 text-sm leading-7 text-slate-300">
                  The module launcher now lives on its own page so users can choose the right workspace without crowding the homepage narrative.
                  Use it to enter App Rationalization or Code Analysis from a single controlled surface.
                </p>
              </div>

              <div className="portal-illustration-frame min-h-[250px] p-4 flex items-center justify-center">
                <img
                  src="/code-analysis-graph.svg"
                  alt="Launch modules page preview"
                  className="w-full h-full object-cover rounded-[20px]"
                />
              </div>

              <div className="portal-note p-5">
                <p className="text-sm font-semibold text-white">Dedicated launcher benefits</p>
                <div className="mt-3 space-y-2 text-xs leading-6 text-slate-400">
                  <p>1. Clear separation between portfolio context and application entry.</p>
                  <p>2. Faster access for users who just need to start a module.</p>
                  <p>3. Consistent routing for both applications from the same page.</p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => navigate('/launch-modules')}
                className="portal-btn-primary px-4 py-3 rounded-xl text-sm font-semibold inline-flex items-center justify-center gap-2"
              >
                Go to Launch Modules
                <ArrowRight size={16} />
              </button>
            </article>
          </section>
        </main>
      </div>
    </div>
  );
};

export default HomePage;
