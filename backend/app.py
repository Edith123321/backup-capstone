import os
import sys
import logging
from dotenv import load_dotenv

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_session import Session

# =========================
# LOAD ENV VARIABLES FIRST
# =========================
load_dotenv()

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# PATH SETUP
# =========================
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# =========================
# FLASK APP INIT
# =========================
app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key-change-in-production"
)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

Session(app)

# =========================
# FRONTEND + CORS
# =========================
FRONTEND_URL = os.environ.get("FRONTEND_URL")

allowed_origins = [
  "https://backup-capstone-mbq6.onrender.com",
    "https://capstone-be-yxzd.onrender.com"
]

# add frontend from env if set
if FRONTEND_URL:
    allowed_origins.append(FRONTEND_URL)

CORS(app,
     origins=allowed_origins,
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

logger.info(f"🌍 Allowed origins: {allowed_origins}")

# =========================
# IMPORT BLUEPRINTS (AFTER ENV LOAD)
# =========================
from api.v1.screening.heart_sound import heart_sound_bp
from api.v1.screening.database_routes import database_bp
from api.v1.screening.validation import validation_bp
from api.v1.auth.google_auth import auth_bp
from api.v1.auth.test_auth import test_auth_bp

# =========================
# REGISTER BLUEPRINTS
# =========================
app.register_blueprint(heart_sound_bp)
app.register_blueprint(database_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(test_auth_bp)

logger.info("✅ All blueprints registered")

# =========================
# ROOT ROUTE
# =========================
@app.route("/", methods=["GET"])
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
@app.route("/api/v1/debug/env", methods=["GET"])
def debug_env():
    return jsonify({
        "GOOGLE_CLIENT_ID": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "GOOGLE_CLIENT_SECRET": bool(os.getenv("GOOGLE_CLIENT_SECRET")),
        "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL"),
        "JWT_SECRET": bool(os.getenv("JWT_SECRET"))
    })

# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# =========================
# MAIN (LOCAL ONLY)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))

    backend_url = os.environ.get(
        "RENDER_EXTERNAL_URL",
        f"http://localhost:{port}"
    )

    print("\n" + "=" * 60)
    print("SAKA BACKEND API")
    print("=" * 60)
    print(f"Backend URL: {backend_url}")
    print(f"Auth Login: {backend_url}/api/v1/auth/google/login")
    print(f"Callback: {backend_url}/api/v1/auth/google/callback")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )