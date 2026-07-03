# backend/api/v1/auth/test_auth.py
from flask import Blueprint, request, jsonify, redirect
import json
import jwt as pyjwt
from datetime import datetime, timedelta
import urllib.parse
import os

test_auth_bp = Blueprint('test_auth', __name__, url_prefix='/api/v1/auth/test')

# Use the SAME secret key as google_auth.py
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key-change-this-in-production')
FRONTEND_URL = 'http://localhost:5173'

@test_auth_bp.route('/login', methods=['GET'])
def test_login():
    """Simple test login - bypass Google OAuth"""
    user_data = {
        'id': 'test-user-123',
        'email': 'test@example.com',
        'name': 'Test Doctor',
        'picture': ''
    }
    
    # Use the same JWT_SECRET as google_auth.py
    jwt_token = pyjwt.encode({
        'id': user_data['id'],
        'email': user_data['email'],
        'name': user_data['name'],
        'picture': user_data['picture'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }, JWT_SECRET, algorithm='HS256')
    
    # Encode user data for URL
    encoded_user = urllib.parse.quote(json.dumps(user_data))
    
    redirect_url = (
        f"{FRONTEND_URL}/auth/callback?"
        f"token={jwt_token}"
        f"&user={encoded_user}"
    )
    
    print(f"🔗 Test redirect to: {redirect_url[:100]}...")
    print(f"🔑 Token: {jwt_token}")
    return redirect(redirect_url)

@test_auth_bp.route('/health', methods=['GET'])
def test_health():
    """Health check for test auth"""
    return jsonify({
        'status': 'ok',
        'frontend_url': FRONTEND_URL
    })

@test_auth_bp.route('/user', methods=['GET'])
def test_user():
    """Get test user info"""
    return jsonify({
        'id': 'test-user-123',
        'email': 'test@example.com',
        'name': 'Test Doctor',
        'picture': '',
        'type': 'test_user'
    })

@test_auth_bp.route('/generate', methods=['GET'])
def generate_token():
    """Generate a new test token for debugging"""
    user_data = {
        'id': 'test-user-456',
        'email': 'test@example.com',
        'name': 'Test Doctor',
        'picture': ''
    }
    
    jwt_token = pyjwt.encode({
        'id': user_data['id'],
        'email': user_data['email'],
        'name': user_data['name'],
        'picture': user_data['picture'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'token': jwt_token,
        'user': user_data,
        'expires_in': '7 days'
    })