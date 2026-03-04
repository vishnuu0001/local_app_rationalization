import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

/* ── Chevron SVG ── */
const Chevron = ({ open }) => (
  <svg
    className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
  </svg>
);

const Layout = ({ children }) => {
  const [expandedSections, setExpandedSections] = useState({
    baseline: false,
    cast: false,
    correlation: false,
    capability: false,
    industry: false,
  });
  const location = useLocation();

  const toggleSection = (section) =>
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));

  const isActive    = (path) => location.pathname === path;
  const isUnder     = (prefix) => location.pathname.startsWith(prefix);

  /* ── reusable style helpers ── */
  const navItem = (active) =>
    `group flex items-center gap-3 px-4 py-2.5 mx-3 rounded-lg text-sm font-medium transition-all duration-150 ${
      active
        ? 'bg-blue-600 text-white shadow-md shadow-blue-900/40'
        : 'text-slate-300 hover:bg-white/8 hover:text-white'
    }`;

  const sectionBtn = (active) =>
    `w-full flex items-center gap-3 px-4 py-2.5 mx-0 rounded-none text-sm font-semibold transition-all duration-150 pl-7 ${
      active
        ? 'text-white'
        : 'text-slate-200 hover:text-white hover:bg-white/5'
    }`;

  const subItem = (active) =>
    `flex items-center gap-2.5 pl-10 pr-4 py-2 mx-3 rounded-lg text-xs font-medium transition-all duration-150 ${
      active
        ? 'bg-blue-500/30 text-blue-200 border-l-2 border-blue-400'
        : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
    }`;

  const sectionLabel = (text) => (
    <p className="px-7 pt-5 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-500 select-none">{text}</p>
  );

  return (
    <div className="flex h-screen bg-slate-100">
      {/* ── Sidebar ── */}
      <div className="w-64 bg-[#0d1b2e] text-white flex flex-col overflow-hidden shadow-2xl">

        {/* Logo / Brand */}
        <div className="px-5 pt-5 pb-4 border-b border-white/8 bg-white/95">
          <img
            src="/techmahindra-logo.svg"
            alt="Tech Mahindra"
            className="h-10 w-auto object-contain"
          />
          <p className="text-[10px] text-slate-500 mt-2 font-medium tracking-wide">App Rationalization Platform</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 space-y-0.5 scrollbar-thin">

          {/* Overview */}
          <div className="px-0">
            <Link to="/" className={navItem(isActive('/'))}>
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Overview
            </Link>
          </div>

          {/* ── DATA COLLECTION ── */}
          {sectionLabel('Data Collection')}

          {/* Infra Discovery */}
          <div>
            <button onClick={() => toggleSection('baseline')} className={sectionBtn(isUnder('/upload'))}>
              <svg className="w-4 h-4 shrink-0 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
              <span className="flex-1 text-left">Infra Discovery</span>
              <Chevron open={expandedSections.baseline} />
            </button>
            {expandedSections.baseline && (
              <Link to="/upload" className={subItem(isActive('/upload'))}>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                Corent Analysis
              </Link>
            )}
          </div>

          {/* App Insights */}
          <div>
            <button onClick={() => toggleSection('cast')} className={sectionBtn(isUnder('/cast-analysis'))}>
              <svg className="w-4 h-4 shrink-0 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <span className="flex-1 text-left">App Insights</span>
              <Chevron open={expandedSections.cast} />
            </button>
            {expandedSections.cast && (
              <Link to="/cast-analysis" className={subItem(isActive('/cast-analysis'))}>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                CAST Analysis
              </Link>
            )}
          </div>

          {/* Templates */}
          <div>
            <button onClick={() => toggleSection('industry')} className={sectionBtn(isUnder('/industry-templates'))}>
              <svg className="w-4 h-4 shrink-0 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span className="flex-1 text-left">Templates</span>
              <Chevron open={expandedSections.industry} />
            </button>
            {expandedSections.industry && (
              <Link to="/industry-templates" className={subItem(isActive('/industry-templates'))}>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                Template Upload
              </Link>
            )}
          </div>

          {/* ── ANALYSIS ── */}
          {sectionLabel('Analysis')}

          {/* Insights Link */}
          <div>
            <button onClick={() => toggleSection('correlation')} className={sectionBtn(isUnder('/correlation'))}>
              <svg className="w-4 h-4 shrink-0 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="flex-1 text-left">Insights Link</span>
              <Chevron open={expandedSections.correlation} />
            </button>
            {expandedSections.correlation && (
              <Link to="/correlation" className={subItem(isActive('/correlation'))}>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                Correlation & Analysis
              </Link>
            )}
          </div>

          {/* Golden Data */}
          <div className="px-0">
            <Link to="/golden-data" className={navItem(isActive('/golden-data'))}>
              <svg className="w-4 h-4 shrink-0 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
              Golden Data
            </Link>
          </div>

          {/* ── OUTCOMES ── */}
          {sectionLabel('Outcomes')}

          {/* Capability Map */}
          <div>
            <button onClick={() => toggleSection('capability')} className={sectionBtn(isUnder('/capability'))}>
              <svg className="w-4 h-4 shrink-0 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              <span className="flex-1 text-left">Capability Map</span>
              <Chevron open={expandedSections.capability} />
            </button>
            {expandedSections.capability && (
              <>
                <Link to="/capability/standardization" className={subItem(isActive('/capability/standardization'))}>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  Standardization & ERP
                </Link>
                <Link to="/capability/inventory" className={subItem(isActive('/capability/inventory'))}>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                  Business Capability
                </Link>
                <Link to="/capability/traceability" className={subItem(isActive('/capability/traceability'))}>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
                  Traceability Matrix
                </Link>
              </>
            )}
          </div>

        </nav>

        {/* Footer */}
        <div className="border-t border-white/8 px-5 py-3">
          <p className="text-[10px] text-slate-500 text-center">v1.0 · App Rationalization Platform</p>
        </div>
      </div>

      {/* ── Main Content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Layout;
