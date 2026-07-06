from flask import Blueprint, request, jsonify, redirect
import os
import requests
import json
from datetime import datetime, timedelta
import jwt
import urllib.parse
import logging

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================
# ENV
# =====================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://backup-capstone-mbq6.onrender.com")


# =====================
# LOGIN (GO TO GOOGLE)
# =====================
@auth_bp.route("/google/login")
def google_login():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Missing GOOGLE_CLIENT_ID"}), 500

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "response_type=code&"
        "scope=openid email profile&"
        "access_type=offline&"
        "prompt=consent"
    )

    return redirect(google_auth_url)


# =====================
# CALLBACK (GOOGLE RETURNS HERE)
# =====================
@auth_bp.route("/google/callback")
def google_callback():
    code = request.args.get("code")

    if not code:
        return jsonify({"error": "Missing code"}), 400

    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    token_res = requests.post(token_url, data=data)

    if token_res.status_code != 200:
        return jsonify({"error": "Token exchange failed", "details": token_res.text}), 400

    tokens = token_res.json()
    access_token = tokens.get("access_token")

    # Get user info
    user_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if user_res.status_code != 200:
        return jsonify({"error": "Failed to fetch user"}), 400

    user = user_res.json()

    # Create JWT
    jwt_token = jwt.encode(
        {
            "email": user["email"],
            "name": user.get("name"),
            "exp": datetime.utcnow() + timedelta(hours=24),
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    # IMPORTANT: encode user safely
    user_encoded = urllib.parse.quote(json.dumps(user))

    # Redirect back to frontend
    return redirect(
        f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user={user_encoded}"
    )


# =====================
# DEBUG ROUTE
# =====================
@auth_bp.route("/debug")
def debug():
    return jsonify({
        "frontend": FRONTEND_URL,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "client_id_set": bool(GOOGLE_CLIENT_ID)
    })