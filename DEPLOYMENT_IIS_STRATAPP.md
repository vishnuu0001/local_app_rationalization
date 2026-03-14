# StratApp — IIS + Cloudflare Deployment Guide

**Target environment:** Windows Server running IIS, fronted by Cloudflare, using the stratapp.org domain.

**Repo root on server:** `E:\techmaapprationalization\local_app_rationalization`

**Public URLs after deployment:**

| URL | What it serves |
|-----|----------------|
| `https://stratapp.org` | App Rationalization portal (React frontend) |
| `https://www.stratapp.org` | Same portal (alias) |
| `https://api.stratapp.org` | App Rationalization API (Flask via IIS FastCGI) |
| `https://code.stratapp.org` | Code Analysis UI (Vite frontend + FastAPI proxy) |

---

## PART 1 — PRE-FLIGHT: INSTALL SERVER REQUIREMENTS

### Step 1.1 — Install Python

1. Open a browser and download Python 3.11 (or 3.10 / 3.12) from `https://python.org/downloads`
2. Run the installer
3. On the first screen **check both boxes**:
   - `Add python.exe to PATH`
   - `Install launcher for all users`
4. Click **Install Now**
5. When the installer finishes, open a new PowerShell window and verify:
   ```powershell
   python --version
   ```
   You should see `Python 3.11.x` (or similar). If you see an error, reopen PowerShell and try again — the PATH update requires a new shell session.

---

### Step 1.2 — Install Node.js

1. Download Node.js 20 LTS from `https://nodejs.org`
2. Run the installer with all defaults
3. After install, open a new PowerShell window and verify:
   ```powershell
   node --version
   npm --version
   ```
   Both commands must return version numbers without errors.

---

### Step 1.3 — Enable IIS and Required Windows Features

1. Press **Win + R**, type `optionalfeatures`, press **Enter**
2. In the **Windows Features** dialog, expand **Internet Information Services** and enable the following:

   Under **Web Management Tools**:
   - IIS Management Console

   Under **World Wide Web Services → Application Development Features**:
   - CGI

   Under **World Wide Web Services → Common HTTP Features**:
   - Default Document
   - HTTP Errors
   - Static Content

   Under **World Wide Web Services → Security**:
   - Request Filtering

3. Click **OK** and wait for Windows to apply the changes
4. Click **Close** when done

---

### Step 1.4 — Install IIS URL Rewrite Module

1. Open a browser and search for **IIS URL Rewrite 2.1** or go to:
   `https://www.iis.net/downloads/microsoft/url-rewrite`
2. Click **Install this extension** — this opens the Web Platform Installer or a direct MSI download
3. If you get the MSI directly, run it as Administrator and accept all defaults
4. When the installer finishes, do **not** close IIS Manager yet — continue to the next step

---

### Step 1.5 — Install Application Request Routing (ARR)

ARR is required so IIS can proxy `/api` requests from `code.stratapp.org` to the local FastAPI process on port 8000.

1. Go to `https://www.iis.net/downloads/microsoft/application-request-routing`
2. Download and run the ARR 3.0 installer as Administrator
3. Accept all defaults and finish the installation

---

### Step 1.6 — Verify Both Modules Are Installed

1. Press **Win + R**, type `inetmgr`, press **Enter** — IIS Manager opens
2. In the left **Connections** panel, click your **server name** (the top node)
3. In the center panel, look for these two icons:
   - **URL Rewrite**
   - **Application Request Routing Cache**
4. If either icon is missing, the installer did not complete — rerun it and check for errors before proceeding

---

### Step 1.7 — Enable ARR Server Proxy

This is a one-time global switch. Without it the Code Analysis `/api` reverse proxy silently returns 502.

1. In IIS Manager, click your **server name** in the Connections panel
2. Double-click **Application Request Routing Cache** in the center panel
3. In the right **Actions** panel, click **Server Proxy Settings**
4. Check the box labelled **Enable proxy**
5. Leave all other fields at their defaults
6. Click **Apply** in the right Actions panel
7. Confirm the green success banner appears, then press **Back** to return to the server view

---

## PART 2 — GET THE CODE

### Step 2.1 — Pull the Latest Repository

Open PowerShell as Administrator and run:

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization"
git pull origin main
```

If this is a first-time clone:

```powershell
git clone <your-repository-url> "E:\techmaapprationalization\local_app_rationalization"
Set-Location "E:\techmaapprationalization\local_app_rationalization"
```

---

### Step 2.2 — Verify Directory Structure

After pulling, confirm the following folders exist:

```
E:\techmaapprationalization\local_app_rationalization\
  AppRationalization\
    backend\          ← Flask API source
    frontend\         ← React source
      build\          ← built after Step 5
  CodeAnalysis\
    api\              ← FastAPI source
    frontend\         ← Vite source
      dist\           ← built after Step 7
```

Run this check:

```powershell
Test-Path "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\run.py"
Test-Path "E:\techmaapprationalization\local_app_rationalization\AppRationalization\frontend\package.json"
Test-Path "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\api\server.py"
Test-Path "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\frontend\package.json"
```

All four must return `True`. If any returns `False`, the pull was incomplete — re-run `git pull`.

---

## PART 3 — CONFIGURE APP RATIONALIZATION BACKEND

### Step 3.1 — Create the Python Virtual Environment

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install wfastcgi
```

To verify wfastcgi installed correctly:

```powershell
.\.venv\Scripts\python.exe -c "import wfastcgi; print(wfastcgi.__file__)"
```

This must print a file path ending in `wfastcgi.py`. If it errors, re-run `pip install wfastcgi`.

---

### Step 3.2 — Create the Backend .env File

Create the file `E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\.env`

Open Notepad as Administrator, paste the following, and save to that exact path:

```env
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=replace-with-a-long-random-string-at-least-32-characters
DATABASE_PROVIDER=sqlite
DATABASE_PATH=E:/techmaapprationalization/local_app_rationalization/AppRationalization/backend/instance/infra_assessment.db
AUTH_TOKEN_SECRET=replace-with-a-shared-secret-used-in-both-backends
AUTH_TOKEN_TTL_SECONDS=28800
SESSION_COOKIE_SECURE=true
AUTH_SUCCESS_REDIRECT_URL=https://stratapp.org/login
CORS_ORIGINS=https://stratapp.org,https://www.stratapp.org,https://code.stratapp.org
INCLUDE_LOCALHOST_CORS_ORIGINS=false
```

**Important notes on each value:**

| Key | Rule |
|-----|------|
| `SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` — keep private |
| `AUTH_TOKEN_SECRET` | Must be **exactly the same** value you put in `CodeAnalysis/.env` in Step 6.2 |
| `DATABASE_PATH` | Use forward slashes. IIS runs as a service account — make sure the path is absolute. |
| `SESSION_COOKIE_SECURE` | Must be `true` on HTTPS. Setting it `false` in production breaks secure cookie handling. |
| `CORS_ORIGINS` | Must include `https://code.stratapp.org` because Code Analysis calls the portal API for token validation. |

If you use Google or GitHub OAuth login, also add:

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://api.stratapp.org/api/auth/google/callback
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=https://api.stratapp.org/api/auth/github/callback
```

---

### Step 3.3 — Initialise the Database

The Flask app creates tables automatically on first startup, but you can run this manually to verify the connection:

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend"
.\.venv\Scripts\Activate.ps1
python init_db.py
```

If you see no errors, the SQLite database was created successfully at the `DATABASE_PATH` location.

---

### Step 3.4 — Register wfastcgi with IIS

This step patches the `web.config` placeholders with your actual Python paths and registers FastCGI with IIS.

**Run as Administrator:**

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization"
.\fix_iis_wfastcgi.ps1
```

The script performs these actions automatically:
1. Resolves the Python executable and wfastcgi.py paths inside the `.venv`
2. Replaces the `__BACKEND_PYTHON__` and `__BACKEND_WFASTCGI__` tokens in `backend\web.config`
3. Grants the IIS application pool identity `Modify` permission on the backend folder
4. Runs `iisreset`

After it completes, verify the tokens were replaced:

```powershell
Select-String -Path "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\web.config" -Pattern "__BACKEND_"
```

This command must return **no matches**. If it finds matches, the script failed — check for error output in the script's run.

---

## PART 4 — CONFIGURE IIS SITES

All steps in this part are performed inside **IIS Manager** (`inetmgr`).

---

### Step 4.1 — Open IIS Manager

1. Press **Win + R**, type `inetmgr`, press **Enter**
2. The left **Connections** panel shows:
   - Your server name at the top
   - **Application Pools** below it
   - **Sites** below that

Keep this window open for all of Part 4.

---

### Step 4.2 — Create Application Pools

Application pools run your site worker processes. Each site needs its own pool.

**Create AppRationalizationPool:**

1. In the Connections panel, click **Application Pools**
2. In the right **Actions** panel, click **Add Application Pool...**
3. Fill in:
   - Name: `AppRationalizationPool`
   - .NET CLR version: **No Managed Code**
   - Managed pipeline mode: **Integrated**
4. Click **OK**

**Create CodeAnalysisPool:**

1. Right-click **Application Pools** → **Add Application Pool...**
2. Fill in:
   - Name: `CodeAnalysisPool`
   - .NET CLR version: **No Managed Code**
   - Managed pipeline mode: **Integrated**
3. Click **OK**

You should now see both pools in the Application Pools list.

---

### Step 4.3 — Update the Portal Frontend Site (app_rationalizat)

This is your existing site that serves the React portal at `stratapp.org` and `www.stratapp.org`.

**Update the physical path:**

1. In the Connections panel, expand **Sites**, click **app_rationalizat**
2. In the right Actions panel, click **Basic Settings...**
3. Click the `...` button next to the **Physical path** field
4. Navigate to and select:
   `E:\techmaapprationalization\local_app_rationalization\AppRationalization\frontend\build`
5. Click **OK** to confirm the folder

**Assign the correct application pool:**

6. Still in Basic Settings, look at the **Application pool** field
7. Click **Select...**
8. Choose `AppRationalizationPool`
9. Click **OK**, then click **OK** again to close Basic Settings

**Update the site bindings:**

10. In the right Actions panel, click **Bindings...**
11. You will see the current binding list (port 3001, etc.)
12. Select the HTTP binding on **port 3001** → click **Edit**
    - Change Type to: **https**
    - Port: **443**
    - Host name: `stratapp.org`
    - SSL certificate: select your installed certificate (see Part 8 — Cloudflare for how to get this)
    - Click **OK**
13. Click **Add** to add a second binding:
    - Type: **https**
    - IP address: **All Unassigned**
    - Port: **443**
    - Host name: `www.stratapp.org`
    - SSL certificate: same certificate
    - Click **OK**
14. Select any remaining HTTP bindings on port 3001 → click **Remove** → confirm
15. Click **Close**

**Verify Default Document:**

16. With **app_rationalizat** selected in the Connections panel, double-click **Default Document** in the center panel
17. Confirm the list contains `index.html`
18. If it does not appear: right Actions panel → **Add...** → type `index.html` → click **OK**

---

### Step 4.4 — Update the API Backend Site (StratAppAPI)

This site runs the Flask API through IIS FastCGI.

**Update the physical path:**

1. Click **StratAppAPI** in the Connections panel
2. Right Actions panel → **Basic Settings...**
3. Click `...` → navigate to:
   `E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend`
4. Click **OK**

**Assign the application pool:**

5. In Basic Settings → **Application pool** → **Select...**
6. Choose `AppRationalizationPool` → **OK** → **OK**

**Update binding:**

7. Right Actions panel → **Bindings...**
8. Select the binding for `api.stratapp.org` → **Edit**
   - Type: **https**
   - Port: **443**
   - Host name: `api.stratapp.org`
   - SSL certificate: select your certificate
   - Click **OK**
9. Remove any HTTP bindings that remain → **Close**

---

### Step 4.5 — Stop and Remove the Legacy Duplicate Site

Your IIS currently has `techm_app_rati...` (port 5050) which is a duplicate backend that will cause routing conflicts. Remove it.

1. Click **techm_app_rati** (or its full name) in the Connections panel
2. Right Actions panel → click **Stop**
3. Wait for the status indicator to show **Stopped**
4. In the Actions panel, click **Remove**
5. When prompted "Are you sure you want to remove this website?" → click **Yes**

---

### Step 4.6 — Add the Code Analysis Frontend Site

This is a new site that serves the Vite-built frontend and proxies `/api` calls to FastAPI on port 8000.

1. Right-click **Sites** in the Connections panel → **Add Website...**
2. Fill in every field:
   - **Site name:** `CodeAnalysisUI`
   - **Application pool:** click **Select...** → choose `CodeAnalysisPool` → **OK**
   - **Physical path:** `E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\frontend\dist`
   - **Binding** section:
     - Type: **https**
     - IP address: **All Unassigned**
     - Port: **443**
     - Host name: `code.stratapp.org`
     - SSL certificate: select your certificate
3. Click **OK**

**Verify the URL Rewrite rules loaded:**

4. Click **CodeAnalysisUI** in the Connections panel
5. Double-click **URL Rewrite** in the center panel
6. You should see exactly two rules:
   - `CodeAnalysisApiProxy` — matches `^api/(.*)` and rewrites to `http://127.0.0.1:8000/api/{R:1}`
   - `CodeAnalysisSpaRoutes` — rewrites all other non-file paths to `/index.html`
7. If no rules appear, the `dist` folder is empty — run the frontend build (Step 7.2) first, then return to this check.

---

### Step 4.7 — Grant File System Permissions

The IIS application pool identity needs write access to specific folders.

Run the following as Administrator in PowerShell:

**App Rationalization — allow database writes and file uploads:**

```powershell
$acl = Get-Acl "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\instance"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("IIS AppPool\AppRationalizationPool","Modify","ContainerInherit,ObjectInherit","None","Allow")
$acl.SetAccessRule($rule)
Set-Acl "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\instance" $acl

$acl = Get-Acl "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\uploads"
$acl.SetAccessRule($rule)
Set-Acl "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend\uploads" $acl
```

**Code Analysis — allow cloned repos and report output:**

```powershell
$rule2 = New-Object System.Security.AccessControl.FileSystemAccessRule("IIS AppPool\CodeAnalysisPool","Modify","ContainerInherit,ObjectInherit","None","Allow")

foreach ($folder in @(
    "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\cloned_repos",
    "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\output_reports"
)) {
    if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder | Out-Null }
    $acl = Get-Acl $folder
    $acl.SetAccessRule($rule2)
    Set-Acl $folder $acl
}
```

---

### Step 4.8 — Apply All IIS Changes

```powershell
iisreset
```

IIS Manager will show all sites in the Sites list. Confirm the status column shows **Started** for:
- `app_rationalizat`
- `StratAppAPI`
- `CodeAnalysisUI`

If any site shows **Stopped**, click it and press **Start** in the right Actions panel. Check the Windows Event Viewer under **Windows Logs → Application** for error details if a site refuses to start.

---

## PART 5 — BUILD THE APP RATIONALIZATION FRONTEND

### Step 5.1 — Create the Production Environment File

Create the file:
`E:\techmaapprationalization\local_app_rationalization\AppRationalization\frontend\.env.production`

Contents:

```env
REACT_APP_API_URL=https://api.stratapp.org/api
REACT_APP_CODE_ANALYSIS_URL=https://code.stratapp.org
REACT_APP_ENVIRONMENT=production
```

**Why `REACT_APP_CODE_ANALYSIS_URL` is critical:**
The portal has a "Launch Modules" page that opens Code Analysis in a new window. If this variable is missing at build time, the button falls back to `http://localhost:5173` and the link will not work in production.

---

### Step 5.2 — Run the Build

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization\frontend"
npm install
npm run build
```

`npm run build` reads `.env.production` automatically and bakes the environment variables into the output files. The build output goes to `AppRationalization\frontend\build\`.

To verify the correct URL was baked in:

```powershell
Select-String -Path "E:\techmaapprationalization\local_app_rationalization\AppRationalization\frontend\build\static\js\*.js" -Pattern "code\.stratapp\.org" | Select-Object -First 1
```

This must return at least one match. If it returns nothing, the `.env.production` file was not found — check the file path and re-run the build.

---

## PART 6 — CONFIGURE CODE ANALYSIS BACKEND

Code Analysis uses FastAPI and runs as a standalone process on `127.0.0.1:8000`. It cannot use IIS FastCGI. IIS forwards `/api` requests to it via the ARR reverse proxy configured in Step 4.6.

---

### Step 6.1 — Create the Python Virtual Environment

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis"
python -m venv .venv
$py = "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install --no-cache-dir -r requirements.txt
& $py -m pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.41.0 pydantic==2.12.5 pydantic-core==2.41.5
```

Important:

- Always install packages with `& $py -m pip ...` as shown above.
- Do not use a bare `pip install ...` command here, because another active virtual environment can silently install the wrong wheel set.

Verify the FastAPI server can start without errors:

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis"
$py = "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\.venv\Scripts\python.exe"
& $py -c "from api.server import app; print('FastAPI app loaded OK')"
```

Expected output: `FastAPI app loaded OK`

If you get either of these errors:

- `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`
- `ModuleNotFoundError: No module named '_cffi_backend'`

run this repair block:

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis"
$py = "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\.venv\Scripts\python.exe"

& $py -m pip uninstall -y pydantic-core pydantic fastapi cffi pynacl pygithub
& $py -m pip install --no-cache-dir pydantic-core==2.41.5 pydantic==2.12.5 fastapi==0.135.1 cffi==2.0.0 pynacl==1.6.2 pygithub==2.8.1

Get-ChildItem ".\.venv\Lib\site-packages\pydantic_core" | Where-Object { $_.Name -like "_pydantic_core*.pyd" }
Get-ChildItem ".\.venv\Lib\site-packages" -Filter "_cffi_backend*.pyd"

& $py -c "from api.server import app; print('FastAPI app loaded OK')"
```

For Python 3.13, the native files should show `cp313` in the filename.

---

### Step 6.2 — Create the Backend .env File

Create the file:
`E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\.env`

Contents:

```env
GITHUB_TOKEN=replace-with-your-github-personal-access-token
AUTH_TOKEN_SECRET=replace-with-the-same-shared-secret-used-in-AppRationalization
AUTH_REQUIRED=true
```

**Important:**
- `AUTH_TOKEN_SECRET` must be **byte-for-byte identical** to the value in `AppRationalization\backend\.env`
- `GITHUB_TOKEN` is required for private repositories. For public repos, GitHub's rate limit is the only constraint — a token still helps.
- `AUTH_REQUIRED=true` enforces portal authentication on every Code Analysis API call.

---

### Step 6.3 — Register the Watchdog as a Startup Task

The backend must be running before IIS can proxy `/api` calls. The watchdog script keeps it alive and restarts it if it crashes.

Run the following **as Administrator** to create a Windows Scheduled Task:

```powershell
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\watchdog_backend.ps1"' `
    -WorkingDirectory "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis"

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName "StratApp-CodeAnalysis-Watchdog" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Keeps CodeAnalysis uvicorn backend running on port 8000" `
    -RunLevel Highest `
    -User "SYSTEM"
```

**Start the watchdog immediately** (without rebooting):

```powershell
Start-ScheduledTask -TaskName "StratApp-CodeAnalysis-Watchdog"
Start-Sleep -Seconds 5
```

**Verify port 8000 is now listening:**

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 8000
```

The output must show `TcpTestSucceeded : True`. If it shows `False`, the watchdog did not start — view the log:

```powershell
Get-Content "E:\codeanalysis_stderr.log" -Tail 30
```

---

## PART 7 — BUILD THE CODE ANALYSIS FRONTEND

### Step 7.1 — Create the Production Environment File

Create the file:
`E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\frontend\.env.production`

Contents:

```env
VITE_PORTAL_API_URL=https://api.stratapp.org/api
VITE_PORTAL_LOGIN_URL=https://stratapp.org/login
VITE_PORTAL_HOME_URL=https://stratapp.org/launch-modules
```

**Do not** set `VITE_CODE_ANALYSIS_API_URL`. If it is left unset, the frontend uses same-origin `/api` which IIS proxies to `localhost:8000` — that is the correct and intended behaviour.

---

### Step 7.2 — Run the Build

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\frontend"
npm install
npm run build
```

The build outputs to `CodeAnalysis\frontend\dist\`.

The `web.config` from `CodeAnalysis\frontend\public\web.config` is automatically copied to `dist\web.config` during the build. This file contains the ARR reverse proxy rule and SPA routing rewrite rule that IIS requires.

Verify the web.config was copied:

```powershell
Test-Path "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\frontend\dist\web.config"
```

Must return `True`. If it returns `False`, check that `CodeAnalysis\frontend\public\web.config` exists and re-run the build.

---

### Step 7.3 — Reload IIS to Pick Up the New dist Folder

```powershell
iisreset
```

---

## PART 8 — CONFIGURE CLOUDFLARE

### Step 8.1 — Sign In to the Cloudflare Dashboard

1. Open a browser and go to `https://dash.cloudflare.com`
2. Sign in with your Cloudflare account credentials
3. In the account home screen, click the **stratapp.org** domain tile — this opens the zone settings for that domain

Keep this page open throughout Part 8.

---

### Step 8.2 — Set SSL/TLS Encryption Mode to Full (Strict)

1. In the left sidebar, click **SSL/TLS** → **Overview**
2. Under **Your SSL/TLS encryption mode**, select **Full (strict)**
3. The setting saves automatically. A green confirmation message appears.

Mode reference:

| Mode | When to use |
|------|-------------|
| **Full (strict)** | Use this. IIS has a valid CA-signed or Cloudflare Origin Certificate. |
| Full | IIS has a self-signed cert. Less secure. Only use if you cannot get a real cert. |
| Flexible | Never. Sends unencrypted traffic to IIS and causes login redirect loops. |
| Off | Never in production. |

---

### Step 8.3 — Issue a Cloudflare Origin Certificate

Cloudflare Origin Certificates are free, issued by Cloudflare, trusted by Cloudflare's proxy, and valid for up to 15 years. They are the recommended option for IIS HTTPS bindings when behind Cloudflare.

**Create the certificate:**

1. Left sidebar → **SSL/TLS** → **Origin Server**
2. Click **Create Certificate**
3. Leave the default settings:
   - Generate private key and CSR with Cloudflare: **selected**
   - Key type: **RSA (2048)**
4. Under **Hostnames**, confirm both of these are listed (they should be added by default):
   - `stratapp.org`
   - `*.stratapp.org`
5. Certificate validity: **15 years** (or whatever suits your policy)
6. Click **Create**

**Save the certificate files:**

7. The page now shows two text blocks:
   - **Origin Certificate** — this is the public certificate
   - **Private Key** — this is the private key (shown only once — copy it now)
8. On your IIS server, open Notepad as Administrator
9. Paste the **Origin Certificate** text and save as:
   `C:\Certs\stratapp_origin.crt`
10. Paste the **Private Key** text and save as:
    `C:\Certs\stratapp_origin.key`
11. Back in the browser, click **OK** to close the certificate creation dialog

**Import the certificate into Windows:**

12. Open PowerShell **as Administrator** on the IIS server
13. Convert the PEM files to a PFX (requires OpenSSL — download from `https://slproweb.com/products/Win32OpenSSL.html` if not installed):
    ```powershell
    & "C:\Program Files\OpenSSL-Win64\bin\openssl.exe" pkcs12 -export `
        -out "C:\Certs\stratapp_origin.pfx" `
        -inkey "C:\Certs\stratapp_origin.key" `
        -in "C:\Certs\stratapp_origin.crt" `
        -passout pass:
    ```
14. Import the PFX into the Windows certificate store:
    ```powershell
    Import-PfxCertificate `
        -FilePath "C:\Certs\stratapp_origin.pfx" `
        -CertStoreLocation "Cert:\LocalMachine\My" `
        -Password (New-Object System.Security.SecureString)
    ```
15. Verify the certificate is now in the store:
    ```powershell
    Get-ChildItem "Cert:\LocalMachine\My" | Where-Object { $_.Subject -like "*stratapp*" }
    ```
    You should see a line with the certificate subject and thumbprint.

**Assign the certificate to IIS bindings:**

16. Open IIS Manager
17. For each of the three HTTPS sites (`app_rationalizat`, `StratAppAPI`, `CodeAnalysisUI`):
    - Click the site in the Connections panel
    - Right Actions panel → **Bindings...**
    - Click the HTTPS binding → **Edit**
    - In the **SSL certificate** dropdown, select the Cloudflare Origin certificate
    - Click **OK** → **Close**

---

### Step 8.4 — Open Zero Trust to Access the Tunnel

The Cloudflare tunnel connects your IIS server to Cloudflare's edge without opening inbound firewall ports.

1. In the left sidebar of the Cloudflare dashboard, scroll to the bottom and click **Zero Trust**
   (This opens a separate tab at `https://one.dash.cloudflare.com`)
2. In the left navigation, click **Networks** → **Tunnels**
3. You should see your existing tunnel with a **green Healthy** status

**If the tunnel shows Degraded or Disconnected**, check the `cloudflared` service on the IIS server:

```powershell
Get-Service -Name 'Cloudflared' | Select-Object Name, Status, StartType
```

Start it if it is stopped:

```powershell
Start-Service -Name 'Cloudflared'
Set-Service -Name 'Cloudflared' -StartupType Automatic
```

If `cloudflared` is not installed as a service, reinstall it:

```powershell
# Navigate to where cloudflared.exe is located, then:
.\cloudflared.exe service install
Start-Service -Name 'Cloudflared'
```

---

### Step 8.5 — Add the code.stratapp.org Public Hostname

Your tunnel already serves `stratapp.org`, `www.stratapp.org`, and `api.stratapp.org`. You need to add the Code Analysis hostname.

1. In Zero Trust → **Networks** → **Tunnels**, click your tunnel name
2. Click **Edit** (top right of the tunnel detail page)
3. Click the **Public Hostname** tab
4. Click **Add a public hostname**
5. Fill in:
   - **Subdomain:** `code`
   - **Domain:** `stratapp.org`
   - **Path:** *(leave blank)*
   - **Service Type:** `HTTP`
   - **URL:** `localhost:80`
6. Click **Save hostname**

> **Note on HTTP vs HTTPS:** If your IIS sites have HTTPS-only bindings (port 443 with no port 80 binding), change **Service Type** to `HTTPS` and **URL** to `localhost:443`. Then expand **Additional application settings** → check **No TLS Verify** → this lets cloudflared accept the self-signed or Cloudflare Origin certificate on `localhost`.

**Verify all four hostnames are present and correct:**

| Public hostname | Service Type | URL |
|-----------------|--------------|-----|
| `stratapp.org` | HTTP | `localhost:80` |
| `www.stratapp.org` | HTTP | `localhost:80` |
| `api.stratapp.org` | HTTP | `localhost:80` |
| `code.stratapp.org` | HTTP | `localhost:80` |

If any hostname points to the wrong URL, click its **Edit** button, correct the URL, and click **Save hostname**.

---

### Step 8.6 — Verify DNS Records

Cloudflare automatically creates DNS records when you save public hostnames in the tunnel, but it is worth confirming.

1. Go back to the stratapp.org zone settings (close the Zero Trust tab or open the zone in a new tab)
2. Left sidebar → **DNS** → **Records**
3. Confirm you see a CNAME record for each hostname:

   | Type | Name | Target | Proxy |
   |------|------|--------|-------|
   | CNAME | `@` (root) | `<tunnel-uuid>.cfargotunnel.com` | Proxied (orange cloud) |
   | CNAME | `www` | `<tunnel-uuid>.cfargotunnel.com` | Proxied (orange cloud) |
   | CNAME | `api` | `<tunnel-uuid>.cfargotunnel.com` | Proxied (orange cloud) |
   | CNAME | `code` | `<tunnel-uuid>.cfargotunnel.com` | Proxied (orange cloud) |

4. If the `code` record is missing, add it manually:
   - Click **Add record**
   - Type: `CNAME`
   - Name: `code`
   - Target: `<your-tunnel-uuid>.cfargotunnel.com`
   - Proxy status: **Proxied** (click the cloud icon to make it orange)
   - Click **Save**

To find your tunnel UUID: Zero Trust → Networks → Tunnels → click the tunnel name. The UUID appears in the tunnel detail page and in all CNAME targets.

**All four records must show the orange cloud (Proxied ON).** Grey cloud (DNS only) means traffic bypasses Cloudflare entirely and your IIS server is exposed directly to the internet.

---

### Step 8.7 — Create Cache Bypass Rules for the APIs

API responses must not be cached at the Cloudflare edge. Create two bypass rules.

**Rule 1 — Bypass cache for App Rationalization API:**

1. Left sidebar → **Caching** → **Cache Rules**
2. Click **Create rule**
3. Rule name: `Bypass cache for StratApp API`
4. Under **When incoming requests match...**:
   - Field: **Hostname** | Operator: **equals** | Value: `api.stratapp.org`
5. Under **Then...**:
   - Cache eligibility: **Bypass cache**
6. Click **Deploy**

**Rule 2 — Bypass cache for Code Analysis API paths:**

1. Click **Create rule** again
2. Rule name: `Bypass cache for Code Analysis API`
3. Under **When incoming requests match...**, add two conditions with **AND**:
   - Condition 1: Field **Hostname** | equals | `code.stratapp.org`
   - Condition 2: Field **URI Path** | starts with | `/api`
4. Under **Then...**:
   - Cache eligibility: **Bypass cache**
5. Click **Deploy**

---

### Step 8.8 — (Optional) Enable Automatic HTTPS Redirect

This ensures anyone who visits `http://stratapp.org` is automatically redirected to HTTPS.

1. Left sidebar → **SSL/TLS** → **Edge Certificates**
2. Scroll to **Always Use HTTPS** → toggle to **On**

---

### Step 8.9 — (Optional) Enable HSTS

Do this only **after** you have confirmed all four URLs work correctly over HTTPS. HSTS cannot easily be undone once browsers have cached it.

1. Left sidebar → **SSL/TLS** → **Edge Certificates**
2. Scroll to **HTTP Strict Transport Security (HSTS)**
3. Click **Enable HSTS**
4. Set:
   - **Max Age:** `6 months` (increase to 1 year after the site is proven stable)
   - **Include subdomains:** On
   - **Preload:** Off (only enable after long-term stability is confirmed)
5. Click **Save**

---

## PART 9 — SMOKE TEST

Run each check **in order**. If an earlier check fails, do not proceed to the next — fix it first.

### Step 9.1 — Test the App Rationalization API

From any browser or from PowerShell on the server:

```powershell
Invoke-RestMethod -Uri "https://api.stratapp.org/api/health"
```

Expected response: `{ "status": "ok" }` (or similar JSON health payload)

If this fails:
- Check IIS is running: `iisreset /status`
- Check app pool: in IIS Manager → Application Pools → `AppRationalizationPool` must show **Started**
- Check Flask logs: `Get-Content "C:\Windows\Temp\wfastcgi_runner.log" -Tail 50`
- Check the `web.config` tokens were replaced (Step 3.4 verification)

---

### Step 9.2 — Test the Portal Frontend

Open in a browser:
`https://stratapp.org`

Expected: The App Rationalization login page renders, no 404 or 500 errors in the browser console (F12 → Console tab).

If this fails:
- Check that `npm run build` completed (Step 5.2)
- Check that the IIS physical path points to the `build` folder (Step 4.3)
- Check that `index.html` is listed as the Default Document (Step 4.3, item 17)

---

### Step 9.3 — Test Portal Login

1. Go to `https://stratapp.org/login`
2. Log in with an admin account (the default admin is created automatically by the Flask startup code)
3. Confirm you land on the portal homepage without errors

If login redirects to `localhost` or shows a CORS error:
- Check `AUTH_SUCCESS_REDIRECT_URL=https://stratapp.org/login` in `AppRationalization\backend\.env`
- Check `CORS_ORIGINS` includes `https://stratapp.org` in `AppRationalization\backend\.env`
- Rebuild the Flask site: re-run `iisreset`

---

### Step 9.4 — Test the Code Analysis API

```powershell
Invoke-RestMethod -Uri "https://code.stratapp.org/api/health"
```

Expected: A JSON response. If you get a 502 Bad Gateway:
- Check FastAPI is running: `Test-NetConnection -ComputerName 127.0.0.1 -Port 8000`
- If port 8000 is not listening: `Start-ScheduledTask -TaskName "StratApp-CodeAnalysis-Watchdog"; Start-Sleep -Seconds 5`
- Re-test the port, then retry the URL

If you get a 404 (not a 502):
- Check the URL Rewrite rules loaded in the `CodeAnalysisUI` IIS site (Step 4.6, items 4-7)
- Check `dist\web.config` exists (Step 7.2 verification)

---

### Step 9.5 — Test the Code Analysis Frontend

Open in a browser: `https://code.stratapp.org`

Expected: The Code Analysis interface loads.

---

### Step 9.6 — Test the Launch from Portal

1. Log into `https://stratapp.org`
2. Go to the Launch Modules page
3. Click the button to open Code Analysis
4. Confirm it opens `https://code.stratapp.org` (not `localhost:5173`)

If it opens `localhost:5173`:
- The App Rationalization frontend was built without `REACT_APP_CODE_ANALYSIS_URL`
- Fix: add it to `.env.production` (Step 5.1), then re-run `npm run build` (Step 5.2)

---

## PART 10 — UPDATE WORKFLOW (FUTURE DEPLOYMENTS)

Use this checklist every time you deploy a new version.

### Step 10.1 — Pull the Latest Code

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization"
git pull origin main
```

---

### Step 10.2 — Update Python Dependencies (if requirements changed)

```powershell
# App Rationalization backend
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization\backend"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Code Analysis backend
Set-Location "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

### Step 10.3 — Re-run wfastcgi Patch (if backend path or Python version changed)

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization"
.\fix_iis_wfastcgi.ps1
```

---

### Step 10.4 — Rebuild Both Frontends

```powershell
Set-Location "E:\techmaapprationalization\local_app_rationalization\AppRationalization\frontend"
npm install
npm run build

Set-Location "E:\techmaapprationalization\local_app_rationalization\CodeAnalysis\frontend"
npm install
npm run build
```

---

### Step 10.5 — Recycle IIS and Restart Code Analysis Backend

```powershell
iisreset
Restart-ScheduledTask -TaskName "StratApp-CodeAnalysis-Watchdog"
```

---

### Step 10.6 — Re-run Smoke Tests

Repeat Steps 9.1 through 9.6 to confirm the new version works correctly.

---

## TROUBLESHOOTING REFERENCE

| Symptom | Where to look | What to check |
|---------|--------------|---------------|
| `api.stratapp.org` returns 500 | `C:\Windows\Temp\wfastcgi_runner.log` | Python path correct? `.env` file present? |
| `api.stratapp.org` returns 404 | IIS Bindings for StratAppAPI | Host name exactly `api.stratapp.org`? |
| Portal loads but API calls fail with CORS | `AppRationalization\backend\.env` | `CORS_ORIGINS` includes `https://stratapp.org`? |
| Portal login redirects to localhost | `AppRationalization\backend\.env` | `AUTH_SUCCESS_REDIRECT_URL=https://stratapp.org/login`? |
| Launch button opens `localhost:5173` | `AppRationalization\frontend\.env.production` | `REACT_APP_CODE_ANALYSIS_URL` present? Rebuild frontend? |
| `code.stratapp.org` returns 502 | Port 8000 listening? | Run `Test-NetConnection -ComputerName 127.0.0.1 -Port 8000` |
| `code.stratapp.org/api` returns 502 | ARR proxy enabled? | Step 1.7 — Enable ARR Server Proxy |
| `code.stratapp.org/api` returns 404 | `dist\web.config` present? | Rebuild Code Analysis frontend (Step 7.2) |
| JWT auth fails between portal and Code Analysis | `AUTH_TOKEN_SECRET` mismatch | Must be identical in both `.env` files |
| Cloudflare shows 521 | IIS not listening | `iisreset /status` — confirm site is Started |
| Cloudflare shows 522 | Tunnel disconnected | `Get-Service Cloudflared` — must be Running |
| Cloudflare shows 524 | Backend timeout | Check FastAPI/Flask process health |
| Cloudflare shows 526 | Invalid SSL cert | Check cert in IIS binding; enable No TLS Verify in tunnel if needed |
