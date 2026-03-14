import os
from functools import wraps
from urllib.parse import urlencode, quote

import requests
from flask import Blueprint, jsonify, redirect, request, g

from app.models.auth import APP_RATIONALIZATION, CODE_ANALYSIS, SUPPORTED_APPS, User
from app.services.auth_service import AUTH_APP_NAME_MAP, AuthService


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _normalize_apps(apps):
    normalized = []
    for app in apps or []:
        if not app or not isinstance(app, str):
            continue
        value = app.strip()
        if value in SUPPORTED_APPS:
            normalized.append(value)
            continue

        mapped = AUTH_APP_NAME_MAP.get(value.lower())
        if mapped:
            normalized.append(mapped)

    if not normalized:
        return []

    return sorted(set(normalized))


def _frontend_login_url():
    return os.getenv("AUTH_SUCCESS_REDIRECT_URL", "http://localhost:3000/login")


def _oauth_callback_url(provider):
    explicit = os.getenv(f"{provider.upper()}_REDIRECT_URI", "").strip()
    if explicit:
        return explicit

    base = request.host_url.rstrip("/")
    return f"{base}/api/auth/{provider}/callback"


def _oauth_redirect(token=None, error=None):
    target = _frontend_login_url().rstrip("/")
    if token:
        return redirect(f"{target}#token={quote(token)}")
    if error:
        return redirect(f"{target}#error={quote(error)}")
    return redirect(target)


def _current_identity():
    token = AuthService.extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        return None, (jsonify({"error": "Authentication required"}), 401)

    auth = AuthService.validate_access_token(token, check_session=True)
    if not auth["ok"]:
        return None, (jsonify({"error": auth["error"]}), auth["status"])

    g.current_user = auth["user"]
    g.current_apps = auth["apps"]
    g.current_token_payload = auth["payload"]
    return auth, None


def requires_auth(admin_only=False):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            auth, error = _current_identity()
            if error:
                return error
            if admin_only and auth["user"].role != "admin":
                return jsonify({"error": "Admin access required"}), 403
            return func(*args, **kwargs)

        return wrapped

    return decorator


@auth_bp.get("/apps")
def get_apps():
    return jsonify(
        {
            "applications": [
                {
                    "key": APP_RATIONALIZATION,
                    "name": "App Rationalization",
                    "slug": "app-rationalization",
                },
                {
                    "key": CODE_ANALYSIS,
                    "name": "Code Analysis",
                    "slug": "code-analysis",
                },
            ]
        }
    )


@auth_bp.get("/oauth/providers")
def oauth_provider_status():
    google_ready = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
    github_ready = bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"))

    return jsonify(
        {
            "google": {
                "enabled": google_ready,
                "start_url": "/api/auth/google/start",
            },
            "github": {
                "enabled": github_ready,
                "start_url": "/api/auth/github/start",
            },
        }
    )


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    result, error = AuthService.authenticate_local_user(
        username=username,
        password=password,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", ""),
    )
    if error:
        return jsonify({"error": error}), 401

    return jsonify(result), 200


@auth_bp.get("/google/start")
def google_start():
    client_id = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        return jsonify({"error": "Google OAuth is not configured"}), 501

    redirect_uri = _oauth_callback_url("google")
    state = AuthService.create_state_token("google")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(auth_url)


@auth_bp.get("/google/callback")
def google_callback():
    if request.args.get("error"):
        return _oauth_redirect(error=f"google_{request.args.get('error')}")

    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return _oauth_redirect(error="google_missing_code_or_state")

    try:
        AuthService.verify_state_token(state, "google")
    except Exception as exc:  # noqa: BLE001
        return _oauth_redirect(error=f"google_state_invalid_{str(exc)}")

    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uri": _oauth_callback_url("google"),
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return _oauth_redirect(error="google_access_token_missing")

        user_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        user_resp.raise_for_status()
        user_data = user_resp.json()

        oauth_subject = str(user_data.get("sub") or "")
        email = user_data.get("email")
        preferred = user_data.get("name") or (email.split("@")[0] if email else None)
        if not oauth_subject:
            return _oauth_redirect(error="google_user_identity_missing")

        user = AuthService.upsert_oauth_user("google", oauth_subject, email=email, preferred_username=preferred)
        login_result, error = AuthService.login_oauth_user(
            user,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        if error:
            return _oauth_redirect(error=f"google_{error}")

        return _oauth_redirect(token=login_result["token"])
    except Exception as exc:  # noqa: BLE001
        return _oauth_redirect(error=f"google_callback_failed_{str(exc)}")


@auth_bp.get("/github/start")
def github_start():
    client_id = (os.getenv("GITHUB_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GITHUB_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        return jsonify({"error": "GitHub OAuth is not configured"}), 501

    state = AuthService.create_state_token("github")
    redirect_uri = _oauth_callback_url("github")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return redirect(auth_url)


@auth_bp.get("/github/callback")
def github_callback():
    if request.args.get("error"):
        return _oauth_redirect(error=f"github_{request.args.get('error')}")

    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return _oauth_redirect(error="github_missing_code_or_state")

    try:
        AuthService.verify_state_token(state, "github")
    except Exception as exc:  # noqa: BLE001
        return _oauth_redirect(error=f"github_state_invalid_{str(exc)}")

    try:
        token_resp = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "code": code,
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "redirect_uri": _oauth_callback_url("github"),
            },
            timeout=20,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return _oauth_redirect(error="github_access_token_missing")

        gh_user = requests.get(
            "https://api.github.com/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=20,
        )
        gh_user.raise_for_status()
        user_data = gh_user.json()

        gh_emails = requests.get(
            "https://api.github.com/user/emails",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=20,
        )
        email = None
        if gh_emails.ok:
            emails = gh_emails.json()
            primary = next((x for x in emails if x.get("primary") and x.get("verified")), None)
            if primary:
                email = primary.get("email")
            elif emails:
                email = emails[0].get("email")

        oauth_subject = str(user_data.get("id") or "")
        preferred = user_data.get("login")
        if not oauth_subject:
            return _oauth_redirect(error="github_user_identity_missing")

        user = AuthService.upsert_oauth_user("github", oauth_subject, email=email, preferred_username=preferred)
        login_result, error = AuthService.login_oauth_user(
            user,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        if error:
            return _oauth_redirect(error=f"github_{error}")

        return _oauth_redirect(token=login_result["token"])
    except Exception as exc:  # noqa: BLE001
        return _oauth_redirect(error=f"github_callback_failed_{str(exc)}")


@auth_bp.get("/me")
@requires_auth(admin_only=False)
def me():
    return jsonify(
        {
            "user": AuthService.serialize_user(g.current_user),
            "expires_at": g.current_token_payload.get("exp"),
        }
    )


@auth_bp.post("/logout")
@requires_auth(admin_only=False)
def logout():
    sid = g.current_token_payload.get("sid")
    AuthService.revoke_session(sid)
    return jsonify({"success": True}), 200


@auth_bp.get("/users")
@requires_auth(admin_only=True)
def list_users():
    users = User.query.order_by(User.username.asc()).all()
    return jsonify({"users": [AuthService.serialize_user(user) for user in users]})


@auth_bp.post("/users")
@requires_auth(admin_only=True)
def create_user():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role", "user")
    apps = _normalize_apps(payload.get("apps", []))

    try:
        user = AuthService.create_user(
            username=username,
            password=password,
            role=role,
            apps=apps,
        )
        return jsonify({"user": AuthService.serialize_user(user)}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@auth_bp.put("/users/<int:user_id>")
@requires_auth(admin_only=True)
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payload = request.get_json(silent=True) or {}
    role = payload.get("role")
    is_active = payload.get("is_active")
    password = payload.get("password")
    apps = _normalize_apps(payload.get("apps")) if "apps" in payload else None

    try:
        user = AuthService.update_user(
            user=user,
            role=role,
            is_active=is_active,
            apps=apps,
            password=password,
        )
        return jsonify({"user": AuthService.serialize_user(user)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
