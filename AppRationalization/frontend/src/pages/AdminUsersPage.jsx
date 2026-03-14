import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, LayoutGrid, LogOut, ShieldCheck, UserPlus, Users } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { createUser, fetchApplications, listUsers, updateUser } from '../services/authApi';

const emptyCreateState = {
  username: '',
  password: '',
  role: 'user',
  apps: ['APP_RATIONALIZATION'],
};

const normalizeApps = (apps) => {
  if (!Array.isArray(apps)) {
    return [];
  }
  return [...new Set(apps)];
};

const AdminUsersPage = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [applications, setApplications] = useState([]);
  const [users, setUsers] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [createState, setCreateState] = useState(emptyCreateState);

  const appOptions = useMemo(() => {
    if (applications.length > 0) {
      return applications;
    }
    return [
      { key: 'APP_RATIONALIZATION', name: 'App Rationalization' },
      { key: 'CODE_ANALYSIS', name: 'Code Analysis' },
    ];
  }, [applications]);

  const activeUsers = users.filter((entry) => entry.is_active).length;
  const adminUsers = users.filter((entry) => entry.role === 'admin').length;

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [appsResponse, usersResponse] = await Promise.all([fetchApplications(), listUsers()]);
      const apps = appsResponse?.applications || [];
      const userRows = usersResponse?.users || [];
      setApplications(apps);
      setUsers(userRows);
      const nextDrafts = {};
      userRows.forEach((u) => {
        nextDrafts[u.id] = {
          role: u.role,
          is_active: Boolean(u.is_active),
          apps: normalizeApps(u.apps),
          password: '',
        };
      });
      setDrafts(nextDrafts);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const updateDraft = (userId, patch) => {
    setDrafts((prev) => ({
      ...prev,
      [userId]: {
        ...(prev[userId] || {}),
        ...patch,
      },
    }));
  };

  const toggleDraftApp = (userId, appKey) => {
    const current = normalizeApps(drafts[userId]?.apps || []);
    const has = current.includes(appKey);
    const next = has ? current.filter((a) => a !== appKey) : [...current, appKey];
    updateDraft(userId, { apps: next });
  };

  const toggleCreateApp = (appKey) => {
    const current = normalizeApps(createState.apps);
    const has = current.includes(appKey);
    const next = has ? current.filter((a) => a !== appKey) : [...current, appKey];
    setCreateState((prev) => ({ ...prev, apps: next }));
  };

  const handleCreateUser = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await createUser({
        username: createState.username,
        password: createState.password,
        role: createState.role,
        apps: normalizeApps(createState.apps),
      });
      setCreateState(emptyCreateState);
      setSuccess('User created successfully');
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create user');
    } finally {
      setBusy(false);
    }
  };

  const handleUpdateUser = async (userId) => {
    const draft = drafts[userId];
    if (!draft) {
      return;
    }

    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await updateUser(userId, {
        role: draft.role,
        is_active: draft.is_active,
        apps: normalizeApps(draft.apps),
        ...(draft.password ? { password: draft.password } : {}),
      });
      setSuccess('User updated successfully');
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to update user');
    } finally {
      setBusy(false);
    }
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
                <ShieldCheck size={20} className="text-white" />
              </div>
              <div>
                <p className="portal-section-label">Administration</p>
                <h1 className="text-2xl font-semibold text-white">User Access Management</h1>
              </div>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-slate-300">Admin: {user?.username}</span>
              <button
                type="button"
                onClick={() => navigate('/home')}
                className="portal-btn-secondary px-4 py-2 rounded-xl inline-flex items-center gap-2"
              >
                <ArrowLeft size={15} />
                Back to Home
              </button>
              <button
                type="button"
                onClick={onLogout}
                className="portal-btn-danger px-4 py-2 rounded-xl inline-flex items-center gap-2"
              >
                <LogOut size={15} />
                Logout
              </button>
            </div>
          </div>
        </header>

        <main className="portal-page-width p-5 space-y-6">
          <section className="grid md:grid-cols-3 gap-4">
            <div className="portal-stat-card">
              <div className="flex items-center gap-3">
                <Users size={18} className="text-cyan-300" />
                <p className="text-base font-semibold text-white">Users</p>
              </div>
              <p className="mt-3 text-3xl font-semibold text-white">{users.length}</p>
              <p className="mt-2 text-xs leading-6 text-slate-400">Accounts managed through the portal.</p>
            </div>
            <div className="portal-stat-card">
              <div className="flex items-center gap-3">
                <CheckCircle2 size={18} className="text-emerald-300" />
                <p className="text-base font-semibold text-white">Active</p>
              </div>
              <p className="mt-3 text-3xl font-semibold text-white">{activeUsers}</p>
              <p className="mt-2 text-xs leading-6 text-slate-400">Enabled users with current portal access.</p>
            </div>
            <div className="portal-stat-card">
              <div className="flex items-center gap-3">
                <LayoutGrid size={18} className="text-indigo-300" />
                <p className="text-base font-semibold text-white">Applications</p>
              </div>
              <p className="mt-3 text-3xl font-semibold text-white">{appOptions.length}</p>
              <p className="mt-2 text-xs leading-6 text-slate-400">Assignable modules across this modernization suite.</p>
            </div>
          </section>

        {(error || success) && (
          <div
            className={`rounded-2xl px-4 py-3 text-sm border ${
              error
                ? 'bg-rose-500/10 border-rose-400/20 text-rose-200'
                : 'bg-emerald-500/10 border-emerald-400/20 text-emerald-200'
            }`}
          >
            {error || success}
          </div>
        )}

        <section className="portal-glass rounded-[28px] p-5 lg:p-6">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-2xl bg-indigo-500/15 border border-indigo-400/15 flex items-center justify-center">
              <UserPlus size={18} className="text-indigo-300" />
            </div>
            <div>
              <p className="portal-section-label">Provision access</p>
              <h2 className="text-lg font-semibold text-white">Create New User</h2>
            </div>
          </div>
          <form className="mt-4 grid md:grid-cols-2 lg:grid-cols-4 gap-4" onSubmit={handleCreateUser}>
            <input
              type="text"
              value={createState.username}
              onChange={(e) => setCreateState((prev) => ({ ...prev, username: e.target.value }))}
              placeholder="Username"
              required
              className="portal-input"
            />
            <input
              type="password"
              value={createState.password}
              onChange={(e) => setCreateState((prev) => ({ ...prev, password: e.target.value }))}
              placeholder="Temporary password"
              required
              className="portal-input"
            />
            <select
              value={createState.role}
              onChange={(e) => setCreateState((prev) => ({ ...prev, role: e.target.value }))}
              className="portal-input"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
            <button
              type="submit"
              disabled={busy}
              className="portal-btn-primary rounded-2xl text-sm py-2.5 font-semibold disabled:opacity-60"
            >
              Create User
            </button>

            <div className="md:col-span-2 lg:col-span-4">
              <p className="portal-section-label mb-3">Application Access</p>
              <div className="flex flex-wrap gap-3">
                {appOptions.map((app) => (
                  <label key={app.key} className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/50 px-4 py-2 text-sm text-slate-200">
                    <input
                      type="checkbox"
                      checked={createState.apps.includes(app.key)}
                      onChange={() => toggleCreateApp(app.key)}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-950 accent-cyan-400"
                    />
                    {app.name}
                  </label>
                ))}
              </div>
            </div>
          </form>
        </section>

        <section className="portal-panel rounded-[28px] p-5 lg:p-6">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
            <div>
              <p className="portal-section-label">User directory</p>
              <h2 className="text-lg font-semibold text-white">Existing Users</h2>
            </div>
            <p className="text-sm text-slate-400">Admins can update role, status, password resets, and application assignments.</p>
          </div>

          {loading ? (
            <div className="mt-4 text-sm text-slate-400">Loading users...</div>
          ) : (
            <div className="mt-4 space-y-4">
              {users.map((u) => {
                const draft = drafts[u.id] || { role: u.role, is_active: u.is_active, apps: u.apps || [], password: '' };
                return (
                  <article key={u.id} className="portal-table-row p-4 lg:p-5">
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium text-white">{u.username}</p>
                          {u.role === 'admin' && <span className="portal-chip">Admin</span>}
                          {!u.is_active && <span className="portal-chip">Inactive</span>}
                        </div>
                        <p className="text-xs text-slate-400 mt-1">Provider: {u.oauth_provider || 'local'} | Admin accounts: {adminUsers}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <select
                          value={draft.role}
                          onChange={(e) => updateDraft(u.id, { role: e.target.value })}
                          className="portal-input min-w-[132px] py-2 px-3 text-sm"
                        >
                          <option value="user">User</option>
                          <option value="admin">Admin</option>
                        </select>
                        <label className="inline-flex items-center gap-2 text-sm text-slate-200 rounded-full border border-slate-700 bg-slate-900/50 px-3 py-2">
                          <input
                            type="checkbox"
                            checked={Boolean(draft.is_active)}
                            onChange={(e) => updateDraft(u.id, { is_active: e.target.checked })}
                            className="h-4 w-4 rounded border-slate-600 bg-slate-950 accent-cyan-400"
                          />
                          Active
                        </label>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-3">
                      {appOptions.map((app) => (
                        <label key={app.key} className="inline-flex items-center gap-2 text-sm text-slate-200 rounded-full border border-slate-700 bg-slate-900/50 px-4 py-2">
                          <input
                            type="checkbox"
                            checked={(draft.apps || []).includes(app.key)}
                            onChange={() => toggleDraftApp(u.id, app.key)}
                            disabled={draft.role === 'admin'}
                            className="h-4 w-4 rounded border-slate-600 bg-slate-950 accent-cyan-400"
                          />
                          {app.name}
                        </label>
                      ))}
                    </div>

                    <div className="mt-3 grid md:grid-cols-[1fr_auto] gap-3">
                      <input
                        type="password"
                        value={draft.password || ''}
                        onChange={(e) => updateDraft(u.id, { password: e.target.value })}
                        placeholder="Set new password (optional)"
                        className="portal-input"
                      />
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleUpdateUser(u.id)}
                        className="portal-btn-primary rounded-2xl px-4 py-2 text-sm font-semibold disabled:opacity-60"
                      >
                        Save Changes
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
        </main>
      </div>
    </div>
  );
};

export default AdminUsersPage;
