from flask import Blueprint, request, jsonify
import sqlite3

handle_bp = Blueprint("handle_requests", __name__, url_prefix="/api")

DB_PATH = "stybase.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Mock token validation (replace with real validation in production)
def validate_access_token(token):
    # For demo, we just check it's not empty
    return token and len(token) > 10

@handle_bp.route("/userinfo", methods=["POST"])
def userinfo():
    """
    Client apps hit this route with access_token to fetch user info.
    Returns username + app_password.
    """
    data = request.get_json()
    access_token = data.get("access_token")

    if not access_token:
        return jsonify({"error": "missing_token"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Look up token
    cur.execute("""
        SELECT u.username, u.email, u.name, u.phone, u.app_password, t.expires_at, t.revoked
        FROM oauth_tokens t
        JOIN users u ON t.user_id = u.id
        WHERE t.access_token=?
    """, (access_token,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "invalid_token"}), 401

    # Expiry + revoke check
    from datetime import datetime
    expires_at = datetime.fromisoformat(row["expires_at"])
    if row["revoked"]:
        conn.close()
        return jsonify({"error": "revoked_token"}), 401
    if expires_at < datetime.utcnow():
        conn.close()
        return jsonify({"error": "expired_token"}), 401

    conn.close()
    return jsonify({
        "username": row["username"],
        "email": row["email"],
        "name": row["name"],
        "phone": row["phone"],
        "app_password": row["app_password"],
    })
