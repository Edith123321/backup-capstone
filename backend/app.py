from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import os
import sys

# =========================
# LOAD ENV
# =========================
load_dotenv()

backend_dir = os.path.dirname(os.path.abspath(__file__))
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
# APP INIT
# =========================
app = Flask(__name__)

# =========================
# SESSION
# =========================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False

Session(app)

# =========================
# CORS (IMPORTANT FIX)
# =========================
CORS(
    app,
    resources={r"/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://backup-capstone-mbq6.onrender.com",
            "https://capstone-be-yxzd.onrender.com"
        ],
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }}
)

# =========================
# BLUEPRINTS (IMPORTANT FIX HERE)
# =========================
app.register_blueprint(heart_sound_bp, url_prefix="/api/v1")
app.register_blueprint(database_bp, url_prefix="/api/v1")
app.register_blueprint(validation_bp, url_prefix="/api/v1")

# 🔥 AUTH MUST BE HERE EXACTLY
app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")

app.register_blueprint(test_auth_bp, url_prefix="/api/v1")

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "routes": {
            "login": "/api/v1/auth/google/login",
            "callback": "/api/v1/auth/google/callback",
            "patients": "/api/v1/database/patients",
            "triage": "/api/v1/database/triage/doctor/<id>"
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "hint": "Check blueprint registration or URL prefix"
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))

    print("🚀 Backend running on port", port)
    print("🔐 Login:", f"http://localhost:{port}/api/v1/auth/google/login")

    app.run(host="0.0.0.0", port=port, debug=False)