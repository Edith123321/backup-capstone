from flask import Flask, jsonify, request  # Added 'request' here
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
    resources={
        r"/api/*": {
            "origins": allowed_origins,
            "supports_credentials": True,
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
            "expose_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "max_age": 3600
        }
    }
)

# Add CORS headers manually as a fallback
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS,PATCH')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Handle OPTIONS requests explicitly
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({})
    origin = request.headers.get('Origin')
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS,PATCH')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600')
    return response, 200

# =========================
# BLUEPRINT REGISTRATION
# =========================
app.register_blueprint(heart_sound_bp, url_prefix="/api/v1/screening")
app.register_blueprint(database_bp, url_prefix="/api/v1/database")
app.register_blueprint(validation_bp, url_prefix="/api/v1/screening")
app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
app.register_blueprint(test_auth_bp, url_prefix="/api/v1/auth/test")

print("✅ Blueprints registered successfully")

# =========================
# ROOT
# =========================
@app.route("/")
def index():
    return jsonify({
        "status": "running",
        "routes": {
            "login": "/api/v1/auth/google/login",
            "callback": "/api/v1/auth/google/callback",
            "patients": "/api/v1/database/patients",
            "triage": "/api/v1/database/triage/doctor/<id>"
        }
    })

# =========================
# HEALTH
# =========================
@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

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
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)