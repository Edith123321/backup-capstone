from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import os
import sys

load_dotenv()

# =========================
# PATH
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
from api.v1.screening.encounter_routes import encounter_bp
from api.v1.auth.google_auth import auth_bp
from api.v1.auth.test_auth import test_auth_bp

# =========================
# APP INIT
# =========================
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

Session(app)

# =========================
# CORS CONFIGURATION
# =========================
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://backup-capstone-mbq6.onrender.com",
]

CORS(
    app,
    origins=allowed_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
    expose_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    max_age=3600
)

# =========================
# BLUEPRINT REGISTRATION
# =========================
# Screening endpoints
app.register_blueprint(heart_sound_bp, url_prefix="/api/v1/screening")
app.register_blueprint(validation_bp, url_prefix="/api/v1/screening")
app.register_blueprint(encounter_bp, url_prefix="/api/v1")

# Database endpoints
app.register_blueprint(database_bp, url_prefix="/api/v1/database")

# Authentication endpoints
app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
app.register_blueprint(test_auth_bp, url_prefix="/api/v1/auth/test")

print("✅ SAKA Blueprints registered successfully")

# =========================
# ROOT - API Information
# =========================
@app.route("/")
def index():
    return jsonify({
        "name": "SAKA Clinical Decision Support System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "auth": {
                "login": "/api/v1/auth/google/login",
                "callback": "/api/v1/auth/google/callback",
                "debug": "/api/v1/auth/debug"
            },
            "encounter": {
                "create": "/api/v1/encounter",
                "patients": "/api/v1/database/patients",
                "triage": "/api/v1/database/triage/doctor/<doctor_id>"
            },
            "screening": {
                "predict": "/api/v1/screening/predict",
                "validate": "/api/v1/screening/validate",
                "health": "/api/v1/screening/health"
            },
            "stats": {
                "rhd": "/api/v1/database/stats/rhd?doctor_id=<doctor_id>"
            },
            "system": {
                "health": "/health",
                "cors_test": "/api/test-cors"
            }
        }
    })

# =========================
# HEALTH CHECK
# =========================
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "SAKA CDSS",
        "version": "1.0.0"
    })

# =========================
# CORS TEST ENDPOINT
# =========================
@app.route("/api/test-cors")
def test_cors():
    """Test endpoint to verify CORS is working"""
    return jsonify({
        "success": True,
        "message": "CORS is working!",
        "origin": request.headers.get('Origin'),
        "method": request.method
    })

# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "hint": "Check the / endpoint for available routes"
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=False,
        threaded=True
    )