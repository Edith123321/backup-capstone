from flask import Blueprint, request, jsonify, redirect
import os
import requests
import jwt
from datetime import datetime, timedelta
import urllib.parse

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# MUST be EXACTLY backend callback
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    "https://capstone-be-yxzd.onrender.com/api/v1/auth/google/callback"
)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")


FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://backup-capstone-mbq6.onrender.com"
)

# =========================
# LOGIN REDIRECT
# =========================
@auth_bp.route("/google/login")
def google_login():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Missing GOOGLE_CLIENT_ID"}), 500

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(GOOGLE_REDIRECT_URI)}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=consent"
    )

    return redirect(auth_url)


# =========================
# CALLBACK
# =========================
@auth_bp.route("/google/callback")
def google_callback():
    code = request.args.get("code")

    if not code:
        return jsonify({"error": "No auth code provided"}), 400

    # Exchange code for token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )

    if token_response.status_code != 200:
        return jsonify({"error": "Token exchange failed"}), 400

    access_token = token_response.json().get("access_token")

    # Get user info
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    # Create JWT
    token = jwt.encode(
        {
            "email": user_info["email"],
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "exp": datetime.utcnow() + timedelta(days=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    # Redirect BACK to frontend callback page
    redirect_url = (
        f"{FRONTEND_URL}/auth/callback"
        f"?token={token}"
        f"&user={urllib.parse.quote(str(user_info))}"
    )

    return redirect(redirect_url)