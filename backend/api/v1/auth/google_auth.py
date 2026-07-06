from flask import Blueprint, redirect, request
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
@auth_bp.route("/api/v1/auth/google/login")
def login():
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
@auth_bp.route("/api/v1/auth/google/callback")
def callback():
    code = request.args.get("code")

    token = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    ).json()

    access_token = token.get("access_token")

    user = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    jwt_token = jwt.encode(
        {
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(days=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    return redirect(
        f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user={urllib.parse.quote(str(user))}"
    )