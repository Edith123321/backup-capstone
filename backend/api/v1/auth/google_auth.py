from flask import Blueprint, redirect, request, jsonify
import os
import requests
import urllib.parse
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = "https://capstone-be-yxzd.onrender.com/api/v1/auth/google/callback"
FRONTEND_URL = "https://backup-capstone-mbq6.onrender.com"
JWT_SECRET = os.getenv("JWT_SECRET", "dev")

# =========================
# LOGIN
# =========================
@auth_bp.route("/google/login")  # Removed /api/v1/auth prefix
def login():
    if not GOOGLE_CLIENT_ID:
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
@auth_bp.route("/google/callback")  # Removed /api/v1/auth prefix
def callback():
    code = request.args.get("code")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400

    try:
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
            return jsonify({"error": token.get("error_description", "Token exchange failed")}), 400

        access_token = token.get("access_token")
        
        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_response.json()
        
        if "error" in user:
            return jsonify({"error": "Failed to get user info"}), 400

        jwt_token = jwt.encode(
            {
                "email": user["email"],
                "name": user.get("name", ""),
                "exp": datetime.utcnow() + timedelta(days=1),
            },
            JWT_SECRET,
            algorithm="HS256",
        )

        return redirect(
            f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user={urllib.parse.quote(str(user))}"
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# HEALTH CHECK FOR AUTH
# =========================
@auth_bp.route("/health")
def auth_health():
    return jsonify({"status": "auth healthy"})