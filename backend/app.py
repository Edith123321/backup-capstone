from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import os
import sys

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# PATH SETUP
# =========================
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# =========================
# IMPORT BLUEPRINTS
# =========================
from api.v1.screening.heart_sound import heart_sound_bp
from api.v1.screening.database_routes import database_bp
from api.v1.screening.validation import validation_bp
from api.v1.auth.google_auth import auth_bp
from api.v1.auth.test_auth import test_auth_bp

# =========================
# INIT APP
# =========================
app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'dev-secret-key-change-in-production'
)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

Session(app)

# =========================
# CORS
# =========================
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5001",
    "https://saka-frontend.onrender.com",
    "https://backup-capstone-mbq6.onrender.com",
    "https://capstone-frontend.onrender.com",
    "https://capstone-be-yxzd.onrender.com",
]

CORS(
    app,
    resources={r"/*": {
        "origins": allowed_origins,
        "supports_credentials": True,
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "Accept",
            "X-Requested-With"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    }}
)
print("=" * 60)
print("CORS ENABLED FOR:")
for origin in allowed_origins:
    print(" -", origin)
print("=" * 60)

# =========================
# BLUEPRINT REGISTRATION
# IMPORTANT FIX: NO url_prefix="/api/v1" HERE
# =========================
app.register_blueprint(heart_sound_bp)
app.register_blueprint(database_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(test_auth_bp)

print("✅ All blueprints registered successfully")

# =========================
# ROOT ROUTE
# =========================
@app.route('/', methods=['GET', "OPTIONS"])
def index():
    return jsonify({
        "name": "SAKA Backend API",
        "status": "running",
        "endpoints": {
            "auth_login": "/api/v1/auth/google/login",
            "auth_callback": "/api/v1/auth/google/callback",
            "patients": "/api/v1/database/patients",
            "triage": "/api/v1/database/triage",
        }
    })

# =========================
# HEALTH CHECK
# =========================
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "env": os.environ.get("FLASK_ENV", "development")
    })

# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# =========================
# MAIN
# =========================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))

    print("\n" + "=" * 60)
    print("SAKA BACKEND RUNNING")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Auth login: http://localhost:{port}/api/v1/auth/google/login")
    print(f"Health: http://localhost:{port}/health")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )