# Vercel Deployment Guide (Backend + Frontend) with SQLite

This guide is simple, copy-paste friendly, and matches your current project structure.

## Important (SQLite on Vercel)

- Vercel serverless functions are **stateless**.
- SQLite file data in `/tmp` is **temporary** and can reset on cold starts/redeploys.
- This setup is fine for demo/testing, not for long-term persistent production data.

---

## 1) Prerequisites

- GitHub repo pushed with this structure (`backend/`, `frontend/`).
- Vercel account connected to your GitHub.
- Python dependencies already in `backend/requirements.txt`.

---

## 2) Pre-deploy check (already done)

`frontend/src/services/api.js` now uses:

```js
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';
```

So frontend can point to your deployed backend using `REACT_APP_API_URL`.

---

## 3) Deploy Backend project on Vercel

1. In Vercel dashboard, click **Add New Project**.
2. Select your repo.
3. Set **Root Directory** to `backend`.
4. Keep `backend/vercel.json` in place (it already routes to `api/index.py`).
5. Add these Environment Variables in **Project Settings → Environment Variables**:

   - `FLASK_ENV=production`
   - `FLASK_DEBUG=false`
   - `DATABASE_PROVIDER=sqlite`
   - `DATABASE_PATH=/tmp/infra_assessment.db`
   - `SECRET_KEY=<your-strong-random-string>`
   - `CORS_ORIGINS=https://<your-frontend-project>.vercel.app`
   - `SQLALCHEMY_POOL_SIZE=1`
   - `SQLALCHEMY_POOL_RECYCLE=60`

6. Deploy.

`backend/vercel.json` is already configured to use Project Settings env vars (no `@secret` placeholders).

After successful deploy, copy backend URL:

- Example: `https://your-backend.vercel.app`

Health check:

- `https://your-backend.vercel.app/api/health`

---

## 4) Deploy Frontend project on Vercel

1. Add another **New Project** in Vercel.
2. Select same repo.
3. Set **Root Directory** to `frontend`.
4. Add environment variables:

   - `REACT_APP_API_URL=https://your-backend.vercel.app/api`
   - `REACT_APP_ENVIRONMENT=production`

5. Deploy.

`frontend/vercel.json` is already configured to use Project Settings env vars (no `@secret` placeholders).

---

## 5) Final verification

1. Open frontend URL from Vercel.
2. Confirm API calls succeed in browser Network tab.
3. Confirm backend health endpoint returns database connected.

Quick tests:

- Frontend loads without CORS errors.
- `GET /api/health` returns `status: healthy`.
- Core endpoint test: `GET /api/capability/mapping?page=1&per_page=10`.

---

## 6) Recommended for stable production

If you need persistent data, switch from SQLite to managed Postgres later:

- Set `DATABASE_PROVIDER=postgresql`
- Set `DATABASE_URL=postgresql+psycopg2://...`

Your backend config already supports both providers.
