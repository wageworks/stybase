from flask import Blueprint, request, session, redirect, url_for, jsonify
from utils.auth import get_user_by_id, is_admin
from utils.security import generate_token
from db import get_db_connection
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
oauth_bp = Blueprint("oauth", __name__, url_prefix="/oauth")

def _add_qs(url: str, extra: dict) -> str:
    """Merge querystring params into a URL."""
    parts = list(urlparse(url))
    q = dict(parse_qsl(parts[4], keep_blank_values=True))
    for k, v in list(extra.items()):
        if v is None or v == "":
            extra.pop(k, None)
    q.update(extra)
    parts[4] = urlencode(q)
    return urlunparse(parts)

@oauth_bp.route("/authorize", methods=["GET", "POST"])
def authorize():
    """
    Step 1: User authorization (consent) screen.
    Accepts: client_id, redirect_uri, scope, response_type=code, state (optional)
    """
    # Require login (preserve return-to)
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login", next=request.url))

    # Read params from GET (first load) or POST (form submit)
    client_id = request.values.get("client_id", "").strip()
    redirect_uri = request.values.get("redirect_uri", "").strip()
    scope = request.values.get("scope", "").strip()
    state = request.values.get("state", "").strip()
    response_type = request.values.get("response_type", "code").strip()

    # Basic validation
    if not client_id or not redirect_uri:
        return "Missing required parameters: client_id, redirect_uri", 400
    if response_type and response_type.lower() != "code":
        return jsonify({"error": "unsupported_response_type"}), 400

    # Lookup app
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, redirect_uri FROM apps WHERE client_id=?", (client_id,))
    app = cur.fetchone()
    if not app:
        conn.close()
        return "Invalid client_id", 400

    # Validate redirect_uri against registered URIs (space/newline separated list allowed)
    registered_uris = (app["redirect_uri"] or "").split()
    if redirect_uri not in registered_uris:
        conn.close()
        return "Invalid redirect_uri for this client_id", 400

    if request.method == "POST":
        action = request.form.get("action")

        if action == "deny":
            conn.close()
            # Pass through error and optional state
            return redirect(_add_qs(redirect_uri, {"error": "access_denied", "state": state}))

        # Approve: record authorization (idempotent-ish)
        cur.execute("""
            INSERT INTO oauth_authorizations (user_id, app_id, authorized_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (user_id, app["id"]))

        # Issue short-lived auth code and store it for the token exchange
        code = generate_token(32)
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds")

        # Requires oauth_codes table (DDL provided below)
        cur.execute("""
            INSERT INTO oauth_codes (code, user_id, app_id, redirect_uri, scope, expires_at, used)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (code, user_id, app["id"], redirect_uri, scope, expires_at))

        conn.commit()
        conn.close()

        # Redirect back to client with code (+ state if provided)
        return redirect(_add_qs(redirect_uri, {"code": code, "state": state}))

    # GET → render consent screen
    conn.close()
    return render_template(
        "authorize.html",
        client_name=app["name"],
        client_id=client_id,
        redirect_uri=redirect_uri,
        permissions=scope.split() if scope else [],
        scope=scope,
        state=state
    )
# ---------------- Token endpoint ----------------
# ---------------- Token endpoint ----------------
@oauth_bp.route("/token", methods=["POST"])
def token():
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    code = request.form.get("code")
    grant_type = request.form.get("grant_type", "authorization_code")

    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400

    # Validate app
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM apps WHERE client_id=? AND client_secret=?", (client_id, client_secret))
    app = cur.fetchone()
    if not app:
        conn.close()
        return jsonify({"error": "invalid_client"}), 400

    # Validate code
    cur.execute("SELECT * FROM oauth_codes WHERE code=? AND used=0", (code,))
    code_row = cur.fetchone()
    if not code_row:
        conn.close()
        return jsonify({"error": "invalid_code"}), 400

    user_id = code_row["user_id"]

    # Mark code as used
    cur.execute("UPDATE oauth_codes SET used=1 WHERE code=?", (code,))

    # Generate tokens
    access_token = generate_token(32)
    refresh_token = generate_token(32)
    expires_at = (datetime.utcnow() + timedelta(seconds=3600)).isoformat(timespec="seconds")

    # Insert into oauth_tokens
    cur.execute("""
        INSERT INTO oauth_tokens (user_id, app_id, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, app["id"], access_token, refresh_token, expires_at))

    # Log action
    cur.execute(
        "INSERT INTO oauth_logs (user_id, app_id, action, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, app["id"], "token_issued", datetime.utcnow())
    )

    conn.commit()
    conn.close()

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token
    })

# ---------------- Revoke endpoint ----------------
@oauth_bp.route("/revoke", methods=["POST"])
def revoke():
    """
    Revoke an authorization
    POST params: client_id, user_id (optional)
    """
    if not is_admin():
        return "Unauthorized", 403

    client_id = request.form.get("client_id")
    user_id = request.form.get("user_id")  # optional

    conn = get_db_connection()
    cur = conn.cursor()

    # Get app
    cur.execute("SELECT * FROM apps WHERE client_id=?", (client_id,))
    app = cur.fetchone()
    if not app:
        conn.close()
        return "Invalid client_id", 400

    # Revoke
    if user_id:
        cur.execute("UPDATE oauth_authorizations SET revoked=1 WHERE app_id=? AND user_id=?", (app["id"], user_id))
    else:
        cur.execute("UPDATE oauth_authorizations SET revoked=1 WHERE app_id=?", (app["id"],))
    conn.commit()
    conn.close()

    return jsonify({"status": "revoked"})
from flask import Blueprint, render_template, session



# Existing routes ...

@oauth_bp.route("/logs")
def oauth_logs():
    if not is_admin():
        return "Unauthorized", 403

    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oauth_logs ORDER BY timestamp DESC")


    logs = cur.fetchall()
    conn.close()

    return render_template("oauth_logs.html", user=user, logs=logs)
