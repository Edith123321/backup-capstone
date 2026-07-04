
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import blueprints
from api.v1.screening.heart_sound import heart_sound_bp
from api.v1.screening.database_routes import database_bp
from api.v1.screening.validation import validation_bp
from api.v1.auth.google_auth import auth_bp
from api.v1.auth.test_auth import test_auth_bp

# Initialize app
app = Flask(__name__)

# Session configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize session
Session(app)

# ============ CORS CONFIGURATION ============
# Get allowed origins from environment or use defaults
allowed_origins_env = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5001,http://localhost:5173')
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(',')]

# Add all possible frontend URLs
frontend_urls = [
    'https://saka-frontend.onrender.com',
    'https://backup-capstone-mbq6.onrender.com',  # Your current frontend
    'https://capstone-frontend.onrender.com',     # Alternative frontend
]

for url in frontend_urls:
    if url not in allowed_origins:
        allowed_origins.append(url)

# Also add your backend URL for self-requests
backend_url = 'https://capstone-be-yxzd.onrender.com'
if backend_url not in allowed_origins:
    allowed_origins.append(backend_url)

print("=" * 50)
print("CORS Allowed Origins:")
for origin in allowed_origins:
    print(f"  - {origin}")
print("=" * 50)

CORS(app, 
     origins=allowed_origins,
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization', 'Accept', 'X-Requested-With'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
     expose_headers=['Content-Type', 'Authorization'])

# Register blueprints
app.register_blueprint(heart_sound_bp)
app.register_blueprint(database_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(test_auth_bp)

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'name': 'Heart Sound Classifier API',
        'version': '1.0.0',
        'status': 'running',
        'allowed_origins': allowed_origins,
        'endpoints': {
            'health': '/api/v1/screening/health',
            'predict': '/api/v1/screening/predict',
            'validate': '/api/v1/screening/validate',
            'patients': '/api/v1/database/patients',
            'triage': '/api/v1/database/triage',
            'recordings': '/api/v1/database/recordings',
            'devices': '/api/v1/database/devices',
            'auth_login': '/api/v1/auth/google/login',
            'auth_callback': '/api/v1/auth/google/callback',
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'allowed_origins': allowed_origins
    })

@app.route('/mobile')
def serve_mobile():
    mobile_path = os.path.join(os.path.dirname(backend_dir), 'frontend_mobile')
    if os.path.exists(os.path.join(mobile_path, 'index.html')):
        return send_from_directory(mobile_path, 'index.html')
    return jsonify({'error': 'Mobile app not found'}), 404

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    
    print("=" * 50)
    print(" HEART SOUND CLASSIFIER API")
    print("=" * 50)
    print(f"\n Backend path: {backend_dir}")
    print(f" Authentication: Google OAuth")
    print(f" Session: Filesystem")
    print(f" Database: SQLite (doctors.db)")
    print(f"\n Allowed Origins: {allowed_origins}")
    print("\n Starting server at http://localhost:" + str(port))
    print(" Health check: http://localhost:" + str(port) + "/health")
    print(" Auth login: http://localhost:" + str(port) + "/api/v1/auth/google/login")
    print("=" * 50)
    
    app.run(debug=False, host='0.0.0.0', port=port)
