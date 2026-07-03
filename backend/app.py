
import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from flask import Flask, jsonify
from flask_cors import CORS

# Import the auth blueprint
from api.v1.auth.google_auth import auth_bp

logger.info("✅ auth_bp imported")

app = Flask(__name__)

# Configure CORS
CORS(app, 
     origins=['http://localhost:3000', 'http://localhost:5001', 'http://localhost:5173', 'http://localhost:5174'],
     supports_credentials=True)

# Register the blueprint
app.register_blueprint(auth_bp)
logger.info("✅ auth_bp registered")

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'running',
        'endpoints': {
            'auth_login': '/api/v1/auth/google/login',
            'auth_callback': '/api/v1/auth/google/callback',
            'auth_test': '/api/v1/auth/test'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("=" * 50)
    print(" SAKA BACKEND API")
    print("=" * 50)
    
    # List all routes
    print("\n=== Registered Routes ===")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule}")
    
    print("\n" + "=" * 50)
    print(f" Auth Login: http://localhost:{port}/api/v1/auth/google/login")
    print(f" Auth Callback: http://localhost:{port}/api/v1/auth/google/callback")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=port)
