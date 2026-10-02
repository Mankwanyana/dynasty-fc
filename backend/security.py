# ============================================================
# DYNASTY FC — SECURITY LAYER
# Rate limiting, security headers, CSRF protection,
# session hardening, and audit logging helpers.
# ============================================================

import os
from datetime import timedelta
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman


# ============================================================
# 1. RATE LIMITER
#    Stops brute-force logins and API spam.
# ============================================================
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["600 per hour", "120 per minute"],   # global soft cap
    storage_uri="memory://",                              # in-memory (fine for school project)
    strategy="fixed-window",
)


# ============================================================
# 2. SECURITY HEADERS (Talisman)
#    Adds X-Frame-Options, CSP, HSTS, etc.
# ============================================================
def init_talisman(app):
    # Allow Google Fonts, FontAwesome, our own images, and inline styles/scripts
    # (we use inline <style> and <script> a lot, so unsafe-inline is needed)
    csp = {
        'default-src': ["'self'"],
        'img-src': [
            "'self'",
            "data:",
            "https:",
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            "https://cdnjs.cloudflare.com",
            "https://fonts.googleapis.com",
        ],
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            "https://cdnjs.cloudflare.com",
        ],
        'font-src': [
            "'self'",
            "data:",
            "https://cdnjs.cloudflare.com",
            "https://fonts.gstatic.com",
        ],
        'connect-src': ["'self'"],
        'frame-src': ["'self'", "https://www.google.com"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
    }

    Talisman(
        app,
        force_https=False,          # ← turn TRUE only after HTTPS is live (Render)
        strict_transport_security=False,   # ← turn TRUE only after HTTPS is live
        session_cookie_secure=False,       # ← turn TRUE only after HTTPS is live
        session_cookie_http_only=True,
        content_security_policy=csp,
        referrer_policy="strict-origin-when-cross-origin",
        feature_policy={
            'geolocation': "'none'",
            'camera': "'none'",
            'microphone': "'none'",
        },
    )


# ============================================================
# 3. SESSION HARDENING (call from app.py after creating app)
# ============================================================
def harden_session(app):
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,       # JS cannot read the cookie
        SESSION_COOKIE_SAMESITE="Lax",      # blocks most CSRF
        SESSION_COOKIE_SECURE=False,        # ← flip to True on Render (HTTPS)
        PERMANENT_SESSION_LIFETIME=timedelta(hours=4),
    )


# ============================================================
# 4. GLOBAL ERROR HANDLERS
#    Prevents stack traces leaking to users in production.
# ============================================================
def init_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Not found"}), 404
        return (
            "<h1 style='font-family:sans-serif;text-align:center;padding:60px;'>"
            "404 — Page Not Found</h1>"
            "<p style='text-align:center;font-family:sans-serif;'>"
            "<a href='/'>Return to Home</a></p>",
            404,
        )

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error"}), 500
        return (
            "<h1 style='font-family:sans-serif;text-align:center;padding:60px;'>"
            "500 — Something went wrong</h1>"
            "<p style='text-align:center;font-family:sans-serif;'>"
            "<a href='/'>Return to Home</a></p>",
            500,
        )

    @app.errorhandler(429)
    def rate_limited(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "Too many requests. Please slow down and try again shortly."
            }), 429
        return (
            "<h1 style='font-family:sans-serif;text-align:center;padding:60px;'>"
            "429 — Too Many Requests</h1>"
            "<p style='text-align:center;font-family:sans-serif;'>"
            "You've made too many requests. Please wait a moment and try again.</p>",
            429,
        )


# ============================================================
# 5. VALIDATION HELPERS (used by app.py routes)
# ============================================================
def clean_str(value, max_len=500):
    """Trim + cap length + remove control characters."""
    if value is None:
        return ""
    s = str(value).strip()
    # Strip non-printable control chars (except normal whitespace)
    s = "".join(ch for ch in s if ch == "\n" or ch == "\t" or ch >= " ")
    return s[:max_len]


def is_valid_email(email):
    """Simple email check — not perfect but stops obvious junk."""
    if not email or "@" not in email:
        return False
    email = email.strip()
    if len(email) > 254:
        return False
    local, _, domain = email.rpartition("@")
    if not local or not domain or "." not in domain:
        return False
    return True


def allowed_file(filename, allowed_ext=None):
    """Check file extension for uploads."""
    if allowed_ext is None:
        allowed_ext = {"png", "jpg", "jpeg", "gif", "webp"}
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_ext