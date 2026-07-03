# backend/api/v1/auth/google_auth.py
from flask import Blueprint, request, jsonify, session, redirect
import os
import json
import requests
from datetime import datetime, timedelta
import jwt as pyjwt  # <-- FIX: Import as pyjwt to avoid conflict
from functools import wraps
import hashlib
import uuid
from dotenv import load_dotenv

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

# Google OAuth Configuration - Load from environment variables
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'https://capstone-be-yxzd.onrender.com/api/v1/auth/google/callback')
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key-change-this-in-production')

# Check if credentials are set
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("⚠️ WARNING: Google OAuth credentials not set in environment variables!")
    print("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
    print("For development, you can set them in a .env file or export them.")

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://backup-capstone-mbq6.onrender.com')
def token_required(f):
    """Decorator to verify JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            # FIX: Use pyjwt instead of jwt
            data = pyjwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = data
        except pyjwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """Redirect to Google OAuth"""
    # Generate state parameter for security
    state = hashlib.sha256(os.urandom(1024)).hexdigest()
    session['oauth_state'] = state
    
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
        f"&state={state}"
        f"&prompt=consent"
    )
    
    return jsonify({
        'auth_url': google_auth_url,
        'state': state
    })

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get the code from the URL
        code = request.args.get('code')
        state = request.args.get('state')
        
        print(f"Callback received - code: {code[:10]}..., state: {state}")
        
        if not code:
            error = request.args.get('error')
            print(f"Error from Google: {error}")
            return redirect(f"{FRONTEND_URL}/login?error={error or 'No authorization code provided'}")
        
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        print("Exchanging code for tokens...")
        token_response = requests.post(token_url, data=token_data)
        tokens = token_response.json()
        
        if 'error' in tokens:
            print(f"Token error: {tokens}")
            return redirect(f"{FRONTEND_URL}/login?error={tokens.get('error_description', 'Failed to get tokens')}")
        
        print("Tokens received successfully")
        
        # Get user info
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        user_response = requests.get(user_info_url, headers=headers)
        user_data = user_response.json()
        
        print(f"User data: {user_data.get('email')}")
        
        # FIX: Use pyjwt instead of jwt
        jwt_token = pyjwt.encode({
            'id': user_data.get('id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'picture': user_data.get('picture'),
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET, algorithm='HS256')
        
        # Redirect to frontend with token
        redirect_url = (
            f"{FRONTEND_URL}/auth/callback?"
            f"token={jwt_token}"
            f"&user={json.dumps(user_data)}"
        )
        
        print(f"Redirecting to frontend...")
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"Auth callback error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(f"{FRONTEND_URL}/login?error={str(e)}")

@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """Verify JWT token and return user info"""
    return jsonify({
        'authenticated': True,
        'user': current_user
    })

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout user"""
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/user', methods=['GET'])
@token_required
def get_user(current_user):
    """Get current user info"""
    return jsonify({
        'user': current_user
    })

@auth_bp.route('/refresh', methods=['POST'])
@token_required
def refresh_token(current_user):
    """Refresh JWT token"""
    # FIX: Use pyjwt instead of jwt
    new_token = pyjwt.encode({
        'id': current_user.get('id'),
        'email': current_user.get('email'),
        'name': current_user.get('name'),
        'picture': current_user.get('picture'),
        'exp': datetime.utcnow() + timedelta(days=7)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'token': new_token
    })