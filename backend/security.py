import os
from datetime import timedelta
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["600 per hour", "120 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)


def init_talisman(app):
    force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"
    session_secure = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

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
            "https://cdn.jsdelivr.net",
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
        force_https=force_https,
        strict_transport_security=force_https,
        session_cookie_secure=session_secure,
        session_cookie_http_only=True,
        content_security_policy=csp,
        referrer_policy="strict-origin-when-cross-origin",
        feature_policy={
            'geolocation': "'none'",
            'camera': "'none'",
            'microphone': "'none'",
        },
    )


def harden_session(app):
    session_secure = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=session_secure,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=4),
    )


def init_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Not found"}), 404
        return (
            "<h1 style='font-family:sans-serif;text-align:center;padding:60px;'>"
            "404 - Page Not Found</h1>"
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
            "500 - Something went wrong</h1>"
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
            "429 - Too Many Requests</h1>"
            "<p style='text-align:center;font-family:sans-serif;'>"
            "You've made too many requests. Please wait a moment and try again.</p>",
            429,
        )


def clean_str(value, max_len=500):
    if value is None:
        return ""
    s = str(value).strip()
    s = "".join(ch for ch in s if ch == "\n" or ch == "\t" or ch >= " ")
    return s[:max_len]


def is_valid_email(email):
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
    if allowed_ext is None:
        allowed_ext = {"png", "jpg", "jpeg", "gif", "webp"}
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_ext