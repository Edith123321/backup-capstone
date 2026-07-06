from flask import Blueprint, redirect, request, jsonify
import os
import requests
import urllib.parse
import jwt
import json
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = "https://capstone-be-yxzd.onrender.com/api/v1/auth/google/callback"
FRONTEND_URL = "https://backup-capstone-mbq6.onrender.com"
JWT_SECRET = os.getenv("JWT_SECRET", "dev")

# =========================
# LOGIN
# =========================
@auth_bp.route("/google/login")
def login():
    logger.info(f"Login endpoint called")
    
    if not GOOGLE_CLIENT_ID:
        logger.error("Google Client ID not configured")
        return jsonify({"error": "Google Client ID not configured"}), 500
    
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
    )
    return redirect(url)

# =========================
# CALLBACK
# =========================
@auth_bp.route("/google/callback")
def callback():
    code = request.args.get("code")
    logger.info(f"Callback called with code: {code[:10] if code else 'None'}...")
    
    if not code:
        logger.error("No code provided in callback")
        return jsonify({"error": "No code provided"}), 400

    try:
        # Exchange code for token
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token = token_response.json()
        
        if "error" in token:
            logger.error(f"Token error: {token}")
            return jsonify({"error": token.get("error_description", "Token exchange failed")}), 400

        access_token = token.get("access_token")
        
        # Get user info
        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_response.json()
        
        if "error" in user:
            logger.error(f"User info error: {user}")
            return jsonify({"error": "Failed to get user info"}), 400

        # Generate JWT token
        jwt_token = jwt.encode(
            {
                "email": user["email"],
                "name": user.get("name", ""),
                "picture": user.get("picture", ""),
                "exp": datetime.utcnow() + timedelta(days=1),
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        
        # IMPORTANT: Use json.dumps() instead of str()
        # This ensures valid JSON format that JavaScript can parse
        user_json = json.dumps(user)
        encoded_user = urllib.parse.quote(user_json)
        
        # Redirect to frontend with token and user data
        redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user={encoded_user}"
        logger.info(f"Redirecting to frontend with user: {user['email']}")
        
        return redirect(redirect_url)
        
    except Exception as e:
        logger.error(f"Exception in callback: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# =========================
# DEBUG ENDPOINT
# =========================
@auth_bp.route("/debug")
def debug():
    return jsonify({
        "google_client_id_set": bool(GOOGLE_CLIENT_ID),
        "google_client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "redirect_uri": REDIRECT_URI,
        "frontend_url": FRONTEND_URL,
        "jwt_secret_set": bool(JWT_SECRET),
    })