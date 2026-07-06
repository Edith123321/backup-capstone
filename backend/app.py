from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
app.config["SESSION_TYPE"] = "filesystem"

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
            "https://backup-capstone-mbq6.onrender.com"
        ],
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }}
)

# =========================
# IMPORT BLUEPRINTS (CRITICAL)
# =========================
from api.v1.auth.google_auth import auth_bp
from api.v1.screening.database_routes import database_bp

# =========================
# REGISTER BLUEPRINTS (CRITICAL FIX)
# =========================
app.register_blueprint(auth_bp)
app.register_blueprint(database_bp)

# =========================
# TEST ROUTE
# =========================
@app.route("/")
def home():
    return jsonify({"status": "backend running"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})