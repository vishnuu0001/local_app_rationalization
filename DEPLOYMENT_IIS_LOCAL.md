# Local IIS Deployment Guide (Backend + Frontend)

This guide deploys this project locally on Windows IIS.

- Backend (Flask) hosted by IIS via FastCGI (`wfastcgi`)
- Frontend (React build) hosted as static files on IIS

## 1) Prerequisites

Install/enable the following:

1. **Python 3.10+** (same version used for your project)
2. **Node.js + npm**
3. **IIS** with features:
   - Web Server
   - Application Development → **CGI**
   - Management Tools → IIS Management Console
4. **IIS URL Rewrite Module** (for SPA rewrite)
5. (Optional) **Application Request Routing (ARR)** if you want reverse proxy from one site

## 2) Prepare project folders

Use your current repo path (example):

- `E:\techmaapprationalization\local_app_rationalization\backend`
- `E:\techmaapprationalization\local_app_rationalization\frontend`

## 3) Backend setup (Flask on IIS)

Run in PowerShell from `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install wfastcgi
wfastcgi-enable
```

> Important: `wfastcgi-enable` must be run in an **Administrator PowerShell** (it updates IIS global `applicationHost.config`).

If you see `Cannot read configuration file due to insufficient permissions`, open an elevated PowerShell and run:

```powershell
Set-Location E:\techmaapprationalization\local_app_rationalization\backend
.\.venv\Scripts\Activate.ps1
wfastcgi-enable
```

### 3.1 Backend environment variables

Create/update `backend\.env`:

```env
FLASK_ENV=production
FLASK_DEBUG=false
DATABASE_PROVIDER=sqlite
DATABASE_PATH=E:/techmaapprationalization/local_app_rationalization/backend/instance/infra_assessment.db
SECRET_KEY=Zxcvbnm@0806@1973
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
```

Recommended for seamless local React dev (`3000`) and IIS frontend (`3001`):

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
```

Optional strict mode (disable automatic localhost CORS allowances in backend):

```env
INCLUDE_LOCALHOST_CORS_ORIGINS=false
```

> If frontend is served on a different IIS binding, add that origin as well.

### 3.2 Backend `web.config`

Use/update `backend/web.config` with correct absolute paths:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="Python FastCGI"
           path="*"
           verb="*"
           modules="FastCgiModule"
           scriptProcessor="E:\\techmaapprationalization\\local_app_rationalization\\backend\\.venv\\Scripts\\python.exe|E:\\techmaapprationalization\\local_app_rationalization\\backend\\.venv\\Lib\\site-packages\\wfastcgi.py"
           resourceType="Unspecified"
           requireAccess="Script" />
    </handlers>

    <fastCgi>
      <application fullPath="E:\\techmaapprationalization\\local_app_rationalization\\backend\\.venv\\Scripts\\python.exe"
                   arguments="E:\\techmaapprationalization\\local_app_rationalization\\backend\\.venv\\Lib\\site-packages\\wfastcgi.py"
                   instanceMaxRequests="10000">
        <environmentVariables>
          <environmentVariable name="WSGI_HANDLER" value="run.app" />
          <environmentVariable name="PYTHONPATH" value="E:\\techmaapprationalization\\local_app_rationalization\\backend" />
          <environmentVariable name="FLASK_ENV" value="production" />
        </environmentVariables>
      </application>
    </fastCgi>
  </system.webServer>
</configuration>
```

## 4) Frontend setup (React static on IIS)

Run in PowerShell from `frontend`:

```powershell
npm install
npm run build
```

This creates the static output in `frontend/build`.

### 4.1 Frontend API URL

Set `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:5000/api
```

If this value changes, rebuild:

```powershell
npm run build
```

### 4.2 Frontend `web.config` for SPA routing

Create `frontend/build/web.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="ApiProxy" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="http://localhost:5000/api/{R:1}" />
        </rule>
        <rule name="ReactRoutes" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
          </conditions>
          <action type="Rewrite" url="/index.html" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

> For API proxy rewrite to work, install and enable **Application Request Routing (ARR)** and enable proxy in IIS Manager (`Server` → `Application Request Routing Cache` → `Server Proxy Settings` → `Enable proxy`).

## 5) Create IIS sites

Open **IIS Manager**.

### 5.1 Backend site

1. Right-click **Sites** → **Add Website...**
2. Site name: `local-app-rationalization-backend`
3. Physical path: `E:\techmaapprationalization\local_app_rationalization\backend`
4. Binding:
   - Type: `http`
   - IP: `All Unassigned`
   - Port: `5000`
   - Host name: (empty)
5. Start the site.

### 5.2 Frontend site

1. Right-click **Sites** → **Add Website...**
2. Site name: `local-app-rationalization-frontend`
3. Physical path: `E:\techmaapprationalization\local_app_rationalization\frontend\build`
4. Binding:
   - Type: `http`
   - IP: `All Unassigned`
   - Port: `3001`
   - Host name: (empty)
5. Start the site.

## 6) App Pool settings (important)

For both app pools used by these sites:

1. Set **.NET CLR version** = `No Managed Code`
2. Set **Managed pipeline mode** = `Integrated`
3. Ensure identity has read/write access:
   - Backend needs write permissions to `backend/instance` and `uploads` folders

## 7) Verify deployment

1. Backend health:
   - `http://localhost:5000/health`
   - `http://localhost:5000/api/health`
2. Backend dashboard API:
   - `http://localhost:5000/api/dashboard`
3. Frontend:
   - `http://localhost:3001`

Expected: frontend loads and dashboard API calls succeed without CORS errors.

## 8) Troubleshooting

### 8.1 500 error on backend site

- Check IIS logs: `C:\inetpub\logs\LogFiles`
- Confirm `python.exe` and `wfastcgi.py` paths in `backend/web.config`
- Ensure `wfastcgi` is installed inside the same backend venv

### 8.2 CORS errors in browser

- Confirm backend is reachable at `http://localhost:5000/api/health`
- Confirm `frontend/.env` has `REACT_APP_API_URL=http://localhost:5000/api`
- Confirm `CORS_ORIGINS` includes `http://localhost:3001`
- Restart IIS site or run `iisreset`

### 8.3 React deep links return 404

- Ensure `frontend/build/web.config` exists with rewrite-to-`index.html`

### 8.4 Permission/database errors

- Grant modify permissions to IIS app pool identity for:
  - `backend/instance`
  - `backend/uploads`

## 9) Optional: single-origin setup

If you want to avoid CORS entirely, host frontend and backend under one IIS site and reverse-proxy `/api/*` to backend app. That requires ARR + URL Rewrite proxy rules.
