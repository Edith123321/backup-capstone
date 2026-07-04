
from flask import Blueprint, request, jsonify, redirect
import os
import logging
import requests
import json
from datetime import datetime, timedelta
import jwt as pyjwt
import traceback
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key-change-this-in-production')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

logger.info(f"✅ Auth blueprint created")
logger.info(f"FRONTEND_URL: {FRONTEND_URL}")
logger.info(f"GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")

@auth_bp.route('/test', methods=['GET'])
def test():
    return jsonify({
        'status': 'Auth blueprint is working!',
        'FRONTEND_URL': FRONTEND_URL,
        'GOOGLE_CLIENT_ID_SET': bool(GOOGLE_CLIENT_ID),
        'GOOGLE_CLIENT_SECRET_SET': bool(GOOGLE_CLIENT_SECRET),
        'GOOGLE_REDIRECT_URI': GOOGLE_REDIRECT_URI
    })

@auth_bp.route('/google/debug', methods=['GET'])
def debug():
    """Debug endpoint"""
    return jsonify({
        'FRONTEND_URL': FRONTEND_URL,
        'callback_path': f"{FRONTEND_URL}/auth/callback",
        'GOOGLE_REDIRECT_URI': GOOGLE_REDIRECT_URI
    })

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    logger.info("=== GOOGLE LOGIN CALLED ===")
    
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured!")
        return jsonify({'error': 'GOOGLE_CLIENT_ID not configured'}), 500

    auth_url = (
        'https://accounts.google.com/o/oauth2/v2/auth'
        '?response_type=code'
        f'&client_id={GOOGLE_CLIENT_ID}'
        f'&redirect_uri={GOOGLE_REDIRECT_URI}'
        '&scope=email profile'
        '&access_type=offline'
        '&prompt=consent'
    )
    
    logger.info(f"Redirecting to Google")
    return redirect(auth_url)

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        logger.info("=== GOOGLE CALLBACK CALLED ===")
        logger.info(f"Full URL: {request.url}")
        logger.info(f"Args: {dict(request.args)}")
        
        code = request.args.get('code')
        if not code:
            logger.error("No code provided")
            return jsonify({'error': 'No code provided'}), 400

        logger.info(f"✅ Received code: {code[:20]}...")

        # Exchange code for access token
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        logger.info("Exchanging code for token...")
        token_response = requests.post(token_url, data=token_data)
        
        logger.info(f"Token response status: {token_response.status_code}")

        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            return jsonify({'error': 'Failed to get access token'}), 400

        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            logger.error("No access token in response")
            return jsonify({'error': 'No access token received'}), 400

        logger.info("Access token received successfully")

        # Get user info
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(userinfo_url, headers=headers)

        if user_response.status_code != 200:
            logger.error(f"User info failed: {user_response.text}")
            return jsonify({'error': 'Failed to get user info'}), 400

        user_info = user_response.json()
        logger.info(f"✅ User authenticated: {user_info.get('email')}")

        # Create JWT token
        token_payload = {
            'user_id': user_info.get('id'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }

        jwt_token = pyjwt.encode(token_payload, JWT_SECRET, algorithm='HS256')
        logger.info("JWT token created")

        # Build redirect URL with proper encoding
        user_json = json.dumps(user_info)
        redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user={urllib.parse.quote(user_json)}"
        
        logger.info(f"Redirecting to: {redirect_url[:100]}...")
        return redirect(redirect_url)

    except Exception as e:
        logger.error(f"Callback error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
