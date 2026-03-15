import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Factory, Lock, ShieldCheck, Sparkles, Users } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { fetchOauthProviders, getGithubAuthUrl, getGoogleAuthUrl } from '../services/authApi';

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, oauthError } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [providerState, setProviderState] = useState({
    google: { enabled: false },
    github: { enabled: false },
  });

  const redirectTo = useMemo(() => {
    const from = location.state?.from?.pathname;
    return from && from !== '/login' ? from : '/home';
  }, [location.state]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/home', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    let active = true;
    fetchOauthProviders()
      .then((data) => {
        if (active) {
          setProviderState(data);
        }
      })
      .catch(() => {
        if (active) {
          setProviderState({
            google: { enabled: false },
            github: { enabled: false },
          });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const handleLogin = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err?.response?.data?.error || 'Login failed. Check username and password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="portal-app-shell flex items-center justify-center p-5 lg:p-8">
      <div className="portal-content portal-page-width grid xl:grid-cols-[1.08fr_0.92fr] gap-6">
        <section className="portal-glass rounded-[30px] p-8 sm:p-10 lg:p-12 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap gap-2">
              <span className="portal-chip">
                <Sparkles size={14} className="text-cyan-300" />
                Unified modernization suite
              </span>
              <span className="portal-chip">
                <ShieldCheck size={14} className="text-indigo-300" />
                Role-based access
              </span>
            </div>

            <div className="mt-8 flex items-center gap-3">
              <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-sky-500 flex items-center justify-center shadow-lg shadow-cyan-950/30">
                <Factory size={22} className="text-white" />
              </div>
              <div>
                <p className="portal-section-label">Vishnuu R & D</p>
                <h1 className="text-3xl sm:text-4xl font-semibold leading-tight text-white">Secure entry to infrastructure, code, and portfolio intelligence</h1>
              </div>
            </div>

            <p className="mt-6 max-w-2xl text-sm sm:text-base leading-8 text-slate-300">
              Sign in once to launch all three modernization workspaces with the same session, permission model,
              and decision context. Start with Infra Scan to assess cloud feasibility, move into Code Analysis
              for repository intelligence, then finalize portfolio decisions in App Rationalization.
            </p>

            <div className="mt-8 grid sm:grid-cols-3 gap-4">
              <div className="portal-stat-card">
                <Lock size={18} className="text-cyan-300" />
                <p className="mt-3 text-base font-semibold text-white">Signed access</p>
                <p className="mt-2 text-xs leading-6 text-slate-400">Managed login, logout, and controlled session handoff across all three modules.</p>
              </div>
              <div className="portal-stat-card">
                <Users size={18} className="text-indigo-300" />
                <p className="mt-3 text-base font-semibold text-white">Controlled launch</p>
                <p className="mt-2 text-xs leading-6 text-slate-400">Only the applications assigned to a user are visible and accessible from the launcher.</p>
              </div>
              <div className="portal-stat-card">
                <Sparkles size={18} className="text-sky-300" />
                <p className="mt-3 text-base font-semibold text-white">Three-step flow</p>
                <p className="mt-2 text-xs leading-6 text-slate-400">Infra Scan → Code Analysis → App Rationalization: each module feeds the next decision.</p>
              </div>
            </div>
          </div>

          <div className="portal-illustration-frame mt-8 p-3">
            <img
              src="/infra-scan-cloud.svg"
              alt="Infrastructure cloud feasibility assessment flow"
              className="w-full rounded-[20px] object-cover"
            />
          </div>
        </section>

        <section className="portal-panel rounded-[30px] p-8 sm:p-10 lg:p-12">
          <p className="portal-section-label">Portal access</p>
          <h2 className="mt-3 text-3xl font-semibold text-white">Welcome</h2>
          <p className="mt-3 text-sm leading-7 text-slate-400">
            Sign in to continue to the unified modernization workspace.
          </p>

          {(error || oauthError) && (
            <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error || `OAuth sign-in failed: ${oauthError}`}
            </div>
          )}

          <form className="mt-7 space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                className="portal-input"
                placeholder="Enter your username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="portal-input"
                placeholder="Enter your password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="portal-btn-primary w-full rounded-2xl py-3 font-semibold inline-flex items-center justify-center gap-2"
            >
              {loading ? 'Signing in...' : 'Sign in'}
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="mt-6 flex items-center gap-3 text-xs text-slate-500">
            <span className="h-px flex-1 bg-slate-800" />
            <span>or continue with</span>
            <span className="h-px flex-1 bg-slate-800" />
          </div>

          <div className="mt-4 grid sm:grid-cols-2 gap-3">
            <button
              type="button"
              disabled={!providerState.google?.enabled}
              onClick={() => {
                window.location.href = getGoogleAuthUrl();
              }}
              className="portal-btn-secondary rounded-2xl py-3 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue with Google
            </button>
            <button
              type="button"
              disabled={!providerState.github?.enabled}
              onClick={() => {
                window.location.href = getGithubAuthUrl();
              }}
              className="portal-btn-secondary rounded-2xl py-3 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue with GitHub
            </button>
          </div>

          <div className="portal-note mt-6 px-4 py-4 text-sm text-slate-300">
            <p className="font-semibold text-white">Default admin access</p>
            <p className="mt-2 text-xs leading-6 text-slate-400">Username: Vishnuu | Password: Asdf@0073</p>
          </div>
        </section>
      </div>
    </div>
  );
};

export default LoginPage;
