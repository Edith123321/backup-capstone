from flask import Blueprint, redirect, request, jsonify
import os
import requests
import urllib.parse
import jwt
import json
from datetime import datetime, timedelta
import logging
import sys

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

# Log environment variables (without exposing secrets fully)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

logger.info(f"GOOGLE_CLIENT_ID present: {bool(GOOGLE_CLIENT_ID)}")
logger.info(f"GOOGLE_CLIENT_SECRET present: {bool(GOOGLE_CLIENT_SECRET)}")

# Check if environment variables are set
if not GOOGLE_CLIENT_ID:
    logger.error("❌ GOOGLE_CLIENT_ID is not set in environment variables!")
if not GOOGLE_CLIENT_SECRET:
    logger.error("❌ GOOGLE_CLIENT_SECRET is not set in environment variables!")

REDIRECT_URI = "https://capstone-be-yxzd.onrender.com/api/v1/auth/google/callback"
FRONTEND_URL = "https://backup-capstone-mbq6.onrender.com"
JWT_SECRET = os.getenv("JWT_SECRET", "dev")

logger.info(f"REDIRECT_URI: {REDIRECT_URI}")
logger.info(f"FRONTEND_URL: {FRONTEND_URL}")

# =========================
# LOGIN
# =========================
@auth_bp.route("/google/login")
def login():
    try:
        logger.info("=" * 50)
        logger.info("🔐 LOGIN ENDPOINT CALLED")
        logger.info("=" * 50)
        
        # Check for missing credentials
        if not GOOGLE_CLIENT_ID:
            logger.error("❌ GOOGLE_CLIENT_ID is not configured!")
            return jsonify({
                "error": "Google Client ID not configured. Please check environment variables."
            }), 500
        
        # Build the Google OAuth URL
        url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
            "&response_type=code"
            "&scope=openid%20email%20profile"
        )
        
        logger.info(f"✅ Redirecting to Google OAuth")
        logger.info(f"Redirect URL: {url}")
        logger.info("=" * 50)
        
        return redirect(url)
        
    except Exception as e:
        logger.error(f"❌ Error in login endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"Login failed: {str(e)}"
        }), 500

# =========================
# CALLBACK
# =========================
@auth_bp.route("/google/callback")
def callback():
    try:
        logger.info("=" * 50)
        logger.info("🔐 CALLBACK ENDPOINT CALLED")
        logger.info("=" * 50)
        
        code = request.args.get("code")
        logger.info(f"Code received: {code[:20] if code else 'None'}...")
        
        if not code:
            logger.error("❌ No code provided in callback")
            return jsonify({"error": "No code provided"}), 400

        # Exchange code for token
        logger.info("🔄 Exchanging code for access token...")
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
        
        logger.info(f"Token response status: {token_response.status_code}")
        token = token_response.json()
        
        if "error" in token:
            logger.error(f"❌ Token error: {token}")
            return jsonify({
                "error": token.get("error_description", "Token exchange failed")
            }), 400

        access_token = token.get("access_token")
        logger.info("✅ Access token obtained successfully")
        
        # Get user info
        logger.info("🔄 Fetching user info from Google...")
        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        logger.info(f"User info response status: {user_response.status_code}")
        user = user_response.json()
        logger.info(f"User email: {user.get('email', 'No email')}")
        
        if "error" in user:
            logger.error(f"❌ User info error: {user}")
            return jsonify({"error": "Failed to get user info"}), 400

        # Generate JWT token
        logger.info("🔄 Generating JWT token...")
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
        logger.info("✅ JWT token generated successfully")
        
        # Prepare user data as JSON
        user_json = json.dumps(user)
        encoded_user = urllib.parse.quote(user_json)
        
        # Redirect to frontend
        redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}&user={encoded_user}"
        logger.info(f"✅ Redirecting to: {FRONTEND_URL}/auth/callback")
        logger.info("=" * 50)
        
        return redirect(redirect_url)
        
    except Exception as e:
        logger.error(f"❌ Error in callback: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# =========================
# DEBUG ENDPOINT
# =========================
@auth_bp.route("/debug")
def debug():
    """Debug endpoint to check configuration"""
    return jsonify({
        "google_client_id_set": bool(GOOGLE_CLIENT_ID),
        "google_client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "redirect_uri": REDIRECT_URI,
        "frontend_url": FRONTEND_URL,
        "jwt_secret_set": bool(JWT_SECRET),
        "environment": {
            "has_google_id": bool(os.getenv("GOOGLE_CLIENT_ID")),
            "has_google_secret": bool(os.getenv("GOOGLE_CLIENT_SECRET")),
        }
    })

# Add this to google_auth.py after the debug endpoint

@auth_bp.route("/test-env")
def test_env():
    """Test if environment variables are loaded"""
    return jsonify({
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID[:10] + "..." if GOOGLE_CLIENT_ID else "Not Set",
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET[:10] + "..." if GOOGLE_CLIENT_SECRET else "Not Set",
        "JWT_SECRET": JWT_SECRET[:10] + "..." if JWT_SECRET else "Not Set",
        "all_set": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
    })


# =========================
# SESSION ENDPOINTS (verify / user / refresh / logout)
# =========================
# The frontend (frontend_web/src/services/auth.js) calls these after login to
# validate the stored token, fetch the user, refresh on 401, and log out. They
# were previously only defined in the UNREGISTERED api/v1/auth/google.py, so all
# four 404'd in production. They are implemented here on the registered
# blueprint, using the same JWT scheme as /google/callback above. CORS/OPTIONS
# are handled globally by flask-cors in app.py.
def _decode_bearer():
    """Return (payload, error_tuple). error_tuple is (message, status) or None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, ("Missing or invalid Authorization header", 401)
    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, ("Token expired", 401)
    except jwt.InvalidTokenError:
        return None, ("Invalid token", 401)


@auth_bp.route("/verify", methods=["GET"])
def verify():
    """Verify the JWT and echo back the user claims."""
    payload, err = _decode_bearer()
    if err:
        return jsonify({"authenticated": False, "error": err[0]}), err[1]
    return jsonify({"authenticated": True, "user": payload})


@auth_bp.route("/user", methods=["GET"])
def get_user():
    """Return the current user's claims from a valid token."""
    payload, err = _decode_bearer()
    if err:
        return jsonify({"error": err[0]}), err[1]
    return jsonify({"user": payload})


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Issue a fresh token from a still-valid one (frontend calls this on 401)."""
    payload, err = _decode_bearer()
    if err:
        return jsonify({"error": err[0]}), err[1]
    new_token = jwt.encode(
        {
            "email": payload.get("email"),
            "name": payload.get("name", ""),
            "picture": payload.get("picture", ""),
            "exp": datetime.utcnow() + timedelta(days=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return jsonify({"token": new_token})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Stateless-JWT logout: the client drops the token; this just acknowledges."""
    return jsonify({"message": "Logged out successfully"})