from flask import Flask, jsonify, render_template, send_from_directory, request, session, redirect, url_for, send_file
from flask_cors import CORS
import sys
import os
import hashlib
import uuid
import urllib.parse
import requests
import json
from functools import wraps
from datetime import datetime, date, time as dt_time, timedelta
from decimal import Decimal
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import secrets

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from database.db import get_db_connection, test_connection

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__,
            static_folder='../frontend',
            template_folder='../frontend/templates')
CORS(app)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dynasty-fc-secret-key-2026')

# ============================================================
# UPLOAD CONFIG
# ============================================================

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}

# ============================================================
# PAYFAST CONFIG
# ============================================================

PAYFAST_MERCHANT_ID  = os.getenv('PAYFAST_MERCHANT_ID')
PAYFAST_MERCHANT_KEY = os.getenv('PAYFAST_MERCHANT_KEY')
PAYFAST_PASSPHRASE   = os.getenv('PAYFAST_PASSPHRASE')
PAYFAST_SANDBOX      = os.getenv('PAYFAST_SANDBOX', 'True').lower() == 'true'
APP_BASE_URL         = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')

PAYFAST_URL = (
    'https://sandbox.payfast.co.za/eng/process'
    if PAYFAST_SANDBOX
    else 'https://www.payfast.co.za/eng/process'
)

# ============================================================
# GOOGLE OAUTH CONFIG
# ============================================================

GOOGLE_CLIENT_ID     = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# ============================================================
# SENDGRID CONFIG
# ============================================================

SENDGRID_API_KEY    = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL')
SENDGRID_FROM_NAME  = os.getenv('SENDGRID_FROM_NAME', 'Dynasty FC')
ADMIN_EMAIL         = os.getenv('ADMIN_EMAIL', SENDGRID_FROM_EMAIL)

# ============================================================
# HELPERS
# ============================================================

def _serialize_row(row):
    """Convert MySQL types (timedelta, date, datetime, Decimal) to JSON-friendly values."""
    clean = {}
    for k, v in row.items():
        if isinstance(v, timedelta):
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            clean[k] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        elif isinstance(v, datetime):
            clean[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(v, date):
            clean[k] = v.strftime('%Y-%m-%d')
        elif isinstance(v, Decimal):
            clean[k] = float(v)
        elif isinstance(v, bytes):
            clean[k] = v.decode('utf-8', errors='ignore')
        else:
            clean[k] = v
    return clean


def _serialize_rows(rows):
    return [_serialize_row(r) for r in rows]


def send_email(to_email, subject, html_content):
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        print("⚠️ SendGrid not configured")
        return False
    try:
        url = 'https://api.sendgrid.com/v3/mail/send'
        headers = {
            'Authorization': f'Bearer {SENDGRID_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": SENDGRID_FROM_EMAIL, "name": SENDGRID_FROM_NAME},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}]
        }
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 202):
            print(f"✅ Email sent to {to_email}")
            return True
        print(f"❌ SendGrid error {r.status_code}: {r.text}")
        return False
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def get_redirect_url(role):
    if role in ('System Administrator', 'Club Administrator'):
        return '/dashboard'
    return '/'


# ============================================================
# DECORATORS
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/staff-login')
        if session.get('role') not in ['System Administrator', 'Club Administrator']:
            return render_template('access_denied.html'), 403
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                return render_template('access_denied.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# PUBLIC PAGES
# ============================================================

@app.route('/')
def home(): return render_template('index.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/teams')
def teams(): return render_template('teams.html')

@app.route('/fixtures')
def fixtures(): return render_template('fixtures.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/login')
def login(): return render_template('login.html')

@app.route('/register')
def register_page(): return render_template('register.html')

@app.route('/get-involved')
def get_involved(): return render_template('get-involved.html')

@app.route('/donate')
def donate_page(): return render_template('donate.html')

@app.route('/payment-success')
def payment_success(): return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel(): return render_template('payment_cancel.html')


# ============================================================
# STAFF PAGES
# ============================================================

@app.route('/staff-login')
def staff_login_page():
    if 'user_id' in session and session.get('role') in ['System Administrator', 'Club Administrator']:
        return redirect('/dashboard')
    return render_template('staff_login.html')

@app.route('/dashboard')
@staff_required
def dashboard(): return render_template('dashboard.html')

@app.route('/players')
@staff_required
def players(): return render_template('players.html')

@app.route('/staff')
@staff_required
def staff(): return render_template('staff.html')

@app.route('/inventory')
@staff_required
def inventory(): return render_template('inventory.html')

@app.route('/finance')
@staff_required
def finance(): return render_template('finance.html')

@app.route('/donors')
@staff_required
def donors(): return render_template('donors.html')


# ============================================================
# GOOGLE OAUTH
# ============================================================

@app.route('/auth/google')
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return "Google login is not configured.", 500
    redirect_uri = f"{APP_BASE_URL}/auth/google/callback"
    scope = "openid email profile"
    state = secrets.token_urlsafe(24)
    session['oauth_state'] = state
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params))


@app.route('/auth/google/callback')
def google_callback():
    if request.args.get('error'):
        return redirect('/login?error=google_denied')
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or not state:
        return redirect('/login?error=google_missing_code')
    if state != session.get('oauth_state'):
        return redirect('/login?error=google_state_mismatch')
    session.pop('oauth_state', None)

    redirect_uri = f"{APP_BASE_URL}/auth/google/callback"
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    try:
        token_json = requests.post('https://oauth2.googleapis.com/token', data=token_data, timeout=10).json()
    except Exception as e:
        print(f"❌ Token exchange failed: {e}")
        return redirect('/login?error=google_token_failed')

    if 'id_token' not in token_json:
        return redirect('/login?error=google_no_id_token')

    try:
        idinfo = id_token.verify_oauth2_token(
            token_json['id_token'], google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        print(f"❌ ID token verify failed: {e}")
        return redirect('/login?error=google_verify_failed')

    google_email = idinfo.get('email', '').lower().strip()
    google_name  = idinfo.get('name') or idinfo.get('given_name') or google_email.split('@')[0]

    if not google_email or not idinfo.get('email_verified', False):
        return redirect('/login?error=google_email_unverified')

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (google_email,))
        user = cursor.fetchone()

        if user:
            if not user['is_active']:
                return redirect('/login?error=account_disabled')
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
        else:
            base_username = google_name.lower().replace(' ', '')[:20] or 'user'
            username = base_username
            counter = 1
            while True:
                cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
                if not cursor.fetchone():
                    break
                counter += 1
                username = f"{base_username}{counter}"

            random_hash = hash_password(secrets.token_urlsafe(32))
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role, is_active) VALUES (%s, %s, %s, 'Player', 1)",
                (username, random_hash, google_email)
            )
            conn.commit()
            session['user_id'] = cursor.lastrowid
            session['username'] = username
            session['role'] = 'Player'

            try:
                send_email(google_email, "Welcome to Dynasty FC!",
                    f"<h2>Welcome, {google_name}!</h2><p>Your account is active.</p>")
            except Exception as e:
                print(f"Email error: {e}")

        return redirect('/')
    except Exception as e:
        print(f"❌ Google DB error: {e}")
        return redirect('/login?error=google_db_error')
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# AUTH API
# ============================================================

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_active = 1", (email,))
        user = cursor.fetchone()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']

    return jsonify({
        'success': True,
        'user_id': user['user_id'],
        'username': user['username'],
        'role': user['role'],
        'redirect': get_redirect_url(user['role'])
    })


@app.route('/api/logout', methods=['POST'])
def logout_api():
    session.clear()
    return jsonify({'success': True, 'redirect': '/'})


@app.route('/api/register', methods=['POST'])
def register_api():
    data = request.json
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Username, email and password are required'}), 400
    if '@' not in email or '.' not in email:
        return jsonify({'success': False, 'message': 'Invalid email'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

    hashed_password = hash_password(password)

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Username taken'}), 400

        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role, is_active) VALUES (%s, %s, %s, 'Player', 1)",
            (username, hashed_password, email)
        )
        conn.commit()
        new_user_id = cursor.lastrowid

        try:
            send_email(email, "Welcome to Dynasty FC!", f"<h2>Welcome, {username}!</h2>")
        except Exception as e:
            print(f"Email error: {e}")

        return jsonify({'success': True, 'message': 'Account created!', 'user_id': new_user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/check-session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'role': session.get('role'), 'username': session.get('username')})
    return jsonify({'logged_in': False})


@app.route('/api/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role')
    })


@app.route('/api/check-staff-session', methods=['GET'])
def check_staff_session():
    if 'user_id' in session and session.get('role') in ['System Administrator', 'Club Administrator', 'Coach']:
        return jsonify({'logged_in': True, 'role': session.get('role')})
    return jsonify({'logged_in': False})


@app.route('/api/staff-login', methods=['POST'])
def staff_login_api():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM users 
            WHERE email = %s AND is_active = 1 
            AND role IN ('System Administrator', 'Club Administrator')
        """, (email,))
        user = cursor.fetchone()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'success': False, 'message': 'Invalid staff credentials'}), 401

    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']

    return jsonify({
        'success': True,
        'user_id': user['user_id'],
        'username': user['username'],
        'role': user['role'],
        'redirect': '/dashboard'
    })


# ============================================================
# NEWSLETTERS
# ============================================================

@app.route('/api/newsletters', methods=['GET'])
def get_newsletters():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM newsletters WHERE is_published = 1 ORDER BY created_at DESC LIMIT 10")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/newsletters', methods=['POST'])
@staff_required
def create_newsletter():
    data = request.json
    if not data.get('title') or not data.get('content'):
        return jsonify({'error': 'Title and content required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO newsletters (title, content, image_url, created_by, is_published) VALUES (%s, %s, %s, %s, 1)",
            (data['title'], data['content'], data.get('image_url'), session['user_id'])
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Newsletter created'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# MESSAGES
# ============================================================

@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.json
    if not all([data.get('name'), data.get('email'), data.get('subject'), data.get('message')]):
        return jsonify({'error': 'All fields required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (name, email, subject, message) VALUES (%s, %s, %s, %s)",
                       (data['name'], data['email'], data['subject'], data['message']))
        conn.commit()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    try:
        send_email(ADMIN_EMAIL, f"New Contact: {data['subject']}",
                   f"<p>{data['name']} ({data['email']}): {data['message']}</p>")
    except Exception as e:
        print(f"Email error: {e}")
    return jsonify({'success': True, 'message': 'Message sent'})


@app.route('/api/messages', methods=['GET'])
@staff_required
def get_messages():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM messages ORDER BY created_at DESC")
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/messages/<int:message_id>/read', methods=['PUT'])
@staff_required
def mark_message_read(message_id):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE messages SET is_read = 1 WHERE message_id = %s", (message_id,))
        conn.commit()
        return jsonify({'success': True})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# VOLUNTEER
# ============================================================

@app.route('/api/volunteer', methods=['POST'])
def apply_volunteer():
    data = request.json
    if not all([data.get('name'), data.get('email'), data.get('role')]):
        return jsonify({'error': 'Name, email and role required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO volunteer_applications (name, email, phone, role, availability, message) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['name'], data['email'], data.get('phone'), data['role'], data.get('availability'), data.get('message'))
        )
        conn.commit()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    try:
        send_email(ADMIN_EMAIL, f"New Volunteer: {data['name']}", f"<p>{data['email']}</p>")
    except Exception as e:
        print(f"Email error: {e}")
    return jsonify({'success': True, 'message': 'Application submitted'})


@app.route('/api/volunteer', methods=['GET'])
@staff_required
def get_volunteers():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM volunteer_applications ORDER BY created_at DESC")
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# DONORS PAGE
# ============================================================

@app.route('/api/donors-page', methods=['GET'])
def get_donors_page():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM donors_page ORDER BY amount DESC")
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/donors-page', methods=['POST'])
@staff_required
def create_donor_page():
    data = request.json
    if not all([data.get('name'), data.get('donor_type'), data.get('amount')]):
        return jsonify({'error': 'Missing fields'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO donors_page (name, donor_type, amount, logo_url, added_by) VALUES (%s, %s, %s, %s, %s)",
            (data['name'], data['donor_type'], data['amount'], data.get('logo_url'), session['user_id'])
        )
        conn.commit()
        return jsonify({'success': True})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# DOCUMENTS VAULT
# ============================================================

@app.route('/api/documents', methods=['GET'])
@staff_required
def get_documents():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM documents_vault ORDER BY uploaded_at DESC")
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/documents', methods=['POST'])
@staff_required
def upload_document():
    data = request.json
    if not all([data.get('title'), data.get('file_name'), data.get('file_path')]):
        return jsonify({'error': 'Missing fields'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents_vault (title, file_name, file_path, document_type, description, uploaded_by) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['title'], data['file_name'], data['file_path'], data.get('document_type'), data.get('description'), session['user_id'])
        )
        conn.commit()
        return jsonify({'success': True})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# TEAMS / PLAYERS
# ============================================================

@app.route('/api/players-teams', methods=['GET'])
def get_players_by_team():
    team_group = request.args.get('team_group')
    age_group = request.args.get('age_group')

    query = "SELECT * FROM players WHERE 1=1"
    params = []
    if team_group:
        query += " AND team_group = %s"
        params.append(team_group)
    if age_group:
        query += " AND age_group = %s"
        params.append(age_group)

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        print(f"❌ /api/players-teams ERROR: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# MATCHES
# ============================================================

@app.route('/api/team-matches', methods=['GET'])
def get_team_matches():
    team_group = request.args.get('team_group')
    age_group = request.args.get('age_group')
    is_completed = request.args.get('is_completed')

    query = "SELECT * FROM team_matches WHERE 1=1"
    params = []

    if team_group:
        query += " AND team_group = %s"
        params.append(team_group)
    if age_group:
        query += " AND age_group = %s"
        params.append(age_group)
    if is_completed is not None:
        query += " AND is_completed = %s"
        params.append(is_completed == 'true')

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query + " ORDER BY match_date ASC", params)
        raw_rows = cursor.fetchall()
        return jsonify(_serialize_rows(raw_rows))
    except Exception as e:
        print(f"❌ /api/team-matches ERROR: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/team-matches', methods=['POST'])
@staff_required
def create_team_match():
    data = request.json
    required = ['team_group', 'home_team', 'away_team', 'match_date', 'match_time']
    if not all(data.get(k) for k in required):
        return jsonify({'error': 'All fields required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_matches (team_group, age_group, home_team, away_team, match_date, match_time, venue, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (data['team_group'], data.get('age_group', 'U15'), data['home_team'], data['away_team'],
             data['match_date'], data['match_time'], data.get('venue'), session['user_id'])
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Match created'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/team-matches/<int:match_id>/result', methods=['PUT'])
@staff_required
def update_match_result(match_id):
    data = request.json
    if data.get('home_score') is None or data.get('away_score') is None:
        return jsonify({'error': 'Scores required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE team_matches SET home_score = %s, away_score = %s, is_completed = 1 WHERE match_id = %s",
            (data['home_score'], data['away_score'], match_id)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Result updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# PREDICTIONS
# ============================================================

@app.route('/api/match-predictions', methods=['POST'])
@login_required
def predict_match():
    data = request.json
    if not data.get('match_id') or data.get('home_score') is None or data.get('away_score') is None:
        return jsonify({'error': 'Match ID and scores required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO match_predictions (match_id, user_id, home_score, away_score) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE home_score = %s, away_score = %s",
            (data['match_id'], session['user_id'], data['home_score'], data['away_score'],
             data['home_score'], data['away_score'])
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Prediction saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/match-predictions', methods=['GET'])
@login_required
def get_predictions():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.username, mp.match_id, mp.home_score, mp.away_score,
                   tm.home_team, tm.away_team,
                   tm.home_score as actual_home, tm.away_score as actual_away,
                   mp.predicted_at
            FROM match_predictions mp
            JOIN users u ON mp.user_id = u.user_id
            JOIN team_matches tm ON mp.match_id = tm.match_id
            ORDER BY mp.predicted_at DESC
        """)
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/all-predictions', methods=['GET'])
@staff_required
def get_all_predictions():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                mp.prediction_id, mp.match_id,
                mp.home_score AS predicted_home,
                mp.away_score AS predicted_away,
                mp.predicted_at,
                u.username, u.email AS user_email,
                tm.home_team, tm.away_team,
                tm.team_group, tm.age_group, tm.match_date, tm.is_completed,
                tm.home_score AS actual_home, tm.away_score AS actual_away
            FROM match_predictions mp
            JOIN users u ON mp.user_id = u.user_id
            JOIN team_matches tm ON mp.match_id = tm.match_id
            ORDER BY tm.match_date DESC, mp.predicted_at DESC
        """)
        rows = cursor.fetchall()

        for r in rows:
            r['points'] = None
            r['result_status'] = 'pending'
            if r['is_completed'] and r['actual_home'] is not None and r['actual_away'] is not None:
                ph, pa = int(r['predicted_home']), int(r['predicted_away'])
                ah, aa = int(r['actual_home']), int(r['actual_away'])
                if ph == ah and pa == aa:
                    r['points'] = 3
                    r['result_status'] = 'exact'
                else:
                    def outcome(h, a): return 'H' if h > a else ('A' if a > h else 'D')
                    if outcome(ph, pa) == outcome(ah, aa):
                        r['points'] = 1
                        r['result_status'] = 'correct_winner'
                    else:
                        r['points'] = 0
                        r['result_status'] = 'wrong'

        return jsonify(_serialize_rows(rows))
    except Exception as e:
        print(f"❌ /api/all-predictions ERROR: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/match-votes', methods=['POST'])
@login_required
def vote_match():
    data = request.json
    if not data.get('match_id') or not data.get('vote'):
        return jsonify({'error': 'Match ID and vote required'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO match_votes (match_id, user_id, vote) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE vote = %s",
            (data['match_id'], session['user_id'], data['vote'], data['vote'])
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Vote recorded'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/match-votes/<int:match_id>/results', methods=['GET'])
def get_vote_results(match_id):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT vote, COUNT(*) as count FROM match_votes WHERE match_id = %s GROUP BY vote", (match_id,))
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# GENERIC DATA
# ============================================================

@app.route('/api/players', methods=['GET'])
def get_players():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vw_player_overview")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/staff', methods=['GET'])
def get_staff():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM staff")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/teams', methods=['GET'])
def get_teams():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vw_team_rosters")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/finance', methods=['GET'])
def get_finance():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vw_finance_dashboard")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/donors', methods=['GET'])
def get_donors():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vw_donor_summary")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventory_items")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vw_training_attendance")
        return jsonify(_serialize_rows(cursor.fetchall()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# CRUD APIs
# ============================================================

@app.route('/api/players', methods=['POST'])
@staff_required
def create_player():
    data = request.json
    if not all([data.get('mysafa_id'), data.get('first_name'), data.get('last_name'), data.get('date_of_birth')]):
        return jsonify({'error': 'Required fields missing'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO players (mysafa_id, first_name, last_name, date_of_birth, position, 
            contact_email, contact_phone, team_group, age_group, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (data['mysafa_id'], data['first_name'], data['last_name'], data['date_of_birth'],
              data.get('position'), data.get('contact_email'), data.get('contact_phone'),
              data.get('team_group', 'Dynamights'), data.get('age_group', 'U15'), data.get('is_active', 1)))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/staff', methods=['POST'])
@staff_required
def create_staff():
    data = request.json
    if not all([data.get('first_name'), data.get('last_name'), data.get('role'), data.get('date_joined')]):
        return jsonify({'error': 'Required fields missing'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO staff (first_name, last_name, role, employment_status, date_joined, contact_email, contact_phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (data['first_name'], data['last_name'], data['role'],
              data.get('employment_status'), data['date_joined'],
              data.get('contact_email'), data.get('contact_phone')))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/inventory', methods=['POST'])
@staff_required
def create_inventory():
    data = request.json
    if not all([data.get('item_name'), data.get('category')]):
        return jsonify({'error': 'Required fields missing'}), 400
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory_items (item_name, category, quantity, purchase_date, purchase_cost, item_condition, storage_location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (data['item_name'], data['category'], data.get('quantity'),
              data.get('purchase_date'), data.get('purchase_cost'),
              data.get('item_condition', 'New'), data.get('storage_location')))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/upload', methods=['POST'])
@staff_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    try:
        original = secure_filename(file.filename)
        ext = original.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)
        return jsonify({'success': True, 'filename': unique_name, 'url': f'/uploads/{unique_name}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================================
# PAYFAST PAYMENTS
# ============================================================

def _payfast_signature(data_dict):
    ordered = []
    for k, v in data_dict.items():
        if v is not None and str(v).strip() != '':
            ordered.append(f"{k}={urllib.parse.quote_plus(str(v).strip())}")
    param_string = '&'.join(ordered)
    if PAYFAST_PASSPHRASE:
        param_string += f"&passphrase={urllib.parse.quote_plus(PAYFAST_PASSPHRASE)}"
    return hashlib.md5(param_string.encode()).hexdigest()


@app.route('/api/donate/start', methods=['POST'])
def donate_start():
    data = request.json
    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    if amount < 10:
        return jsonify({'success': False, 'error': 'Minimum is R10'}), 400
    if not name or not email:
        return jsonify({'success': False, 'error': 'Name and email required'}), 400

    payment_ref = f"DYN-{uuid.uuid4().hex[:10].upper()}"
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO donations (donor_name, donor_email, donor_phone, amount, message, is_anonymous, payment_status, payment_ref)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
        """, (name, email, data.get('phone'), amount, data.get('message'), 1 if data.get('is_anonymous') else 0, payment_ref))
        conn.commit()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    name_parts = name.split()
    payfast_data = {
        'merchant_id': PAYFAST_MERCHANT_ID,
        'merchant_key': PAYFAST_MERCHANT_KEY,
        'return_url': f'{APP_BASE_URL}/payfast/return',
        'cancel_url': f'{APP_BASE_URL}/payfast/cancel',
        'notify_url': f'{APP_BASE_URL}/payfast/notify',
        'name_first': name_parts[0] if name_parts else '',
        'name_last': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
        'email_address': email,
        'm_payment_id': payment_ref,
        'amount': f'{amount:.2f}',
        'item_name': 'Donation to Dynasty FC',
        'item_description': 'Support our youth',
        'custom_str1': 'donation',
    }
    payfast_data['signature'] = _payfast_signature(payfast_data)

    return jsonify({
        'success': True,
        'payfast_url': PAYFAST_URL,
        'payfast_data': payfast_data,
        'payment_ref': payment_ref
    })


@app.route('/payfast/notify', methods=['POST'])
def payfast_notify():
    form = request.form.to_dict()
    received_sig = form.pop('signature', None)
    computed_sig = _payfast_signature(form)
    if received_sig != computed_sig:
        return 'Invalid signature', 400

    payment_ref = form.get('m_payment_id')
    pf_payment_id = form.get('pf_payment_id')
    payment_status = form.get('payment_status')

    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if payment_status == 'COMPLETE':
            cursor.execute("""
                UPDATE donations SET payment_status = 'paid', payfast_pf_id = %s,
                payfast_data = %s, paid_at = NOW() WHERE payment_ref = %s
            """, (pf_payment_id, json.dumps(form), payment_ref))
        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
        return 'DB error', 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return 'OK', 200


@app.route('/payfast/return', methods=['GET', 'POST'])
def payfast_return():
    ref = request.args.get('m_payment_id') or request.form.get('m_payment_id', 'N/A')
    return redirect(f'/payment-success?ref={ref}')


@app.route('/payfast/cancel', methods=['GET', 'POST'])
def payfast_cancel():
    return redirect('/payment-cancel')


@app.route('/api/donations', methods=['GET'])
@staff_required
def list_donations():
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM donations ORDER BY created_at DESC")
        return jsonify(_serialize_rows(cursor.fetchall()))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# STATIC FILES
# ============================================================

@app.route('/css/<path:filename>')
def serve_css(filename): return send_from_directory('../frontend/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename): return send_from_directory('../frontend/js', filename)

@app.route('/images/<path:filename>')
def serve_images(filename): return send_from_directory('../frontend/images', filename)


# ============================================================
# START SERVER
# ============================================================

if __name__ == '__main__':
    if test_connection():
        print("=" * 60)
        print("🚀 DYNASTY FC SERVER RUNNING")
        print("=" * 60)
        print("📱 On your phone (same WiFi):")
        print("   http://192.168.1.76:5000")
        print("")
        print("💻 On this Mac:")
        print("   http://127.0.0.1:5000")
        print("=" * 60)
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Database connection failed. Check your credentials.")