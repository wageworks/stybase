from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
from db import init_db, get_db_connection
from utils.auth import register_user, login_user, logout_user, is_admin, is_developer, get_user_by_id, get_user_by_username
from api.handle_requests import handle_bp
from utils.security import generate_token
from api.oauth import oauth_bp

# ---------------- App Setup ----------------
app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(oauth_bp)
app.register_blueprint(handle_bp)

# Initialize DB
init_db()

# ---------------- Routes ----------------
@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/terms")
def terms():
    return render_template("terms.html")
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/")
def index():
    return render_template("index.html")

# ---------------- Registration ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        name = request.form.get("name")
        phone = request.form.get("phone")
        role = request.form.get("role", "user")  # user or developer
        app_password = request.form["app_password"]
        user_id, error = register_user(username, email,app_password, password, name, phone, role)
        
        if user_id:
            flash("✅ Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"❌ Registration failed: {error}", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")

# ---------------- Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form["username_or_email"].strip()
        password = request.form["password"]
        success, user = login_user(username_or_email, password)
        if success:
            flash(f"✅ Welcome {user['username']}!", "success") # type: ignore
            session["role"] = user["role"] # type: ignore
            if user["role"] == "revoked":  # type: ignore
                flash("❌ Your account has been revoked.", "danger")
                return redirect(url_for("login"))

            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid username/email or password", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    return logout_user()

# ---------------- Dashboard ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    conn = get_db_connection()
    cur = conn.cursor()

    # Developer-specific data
    owned_apps = []
    pending_app_requests = []

    if user["role"].lower() == "developer":
        # Fetch apps owned by this developer
        cur.execute("SELECT * FROM apps WHERE owner_id=?", (user["id"],))
        owned_apps = cur.fetchall()

        # Check if the developer has a pending app request
        cur.execute("""
            SELECT * FROM app_requests
            WHERE user_id=? AND status='pending'
            ORDER BY submitted_at DESC LIMIT 1
        """, (user["id"],))
        pending_request = cur.fetchone()
        has_pending_request = pending_request is not None
        pending_request_name = pending_request["app_name"] if has_pending_request else None
    else:
        has_pending_request = False
        pending_request_name = None

    # Fetch pending login/app requests (optional: only relevant for developers)
    cur.execute("""
        SELECT a.name, COUNT(o.id) as request_count
        FROM apps a
        LEFT JOIN oauth_authorizations o ON a.id = o.app_id
        WHERE a.owner_id=? 
        GROUP BY a.id
    """, (user["id"],))
    pending_app_requests = cur.fetchall()

    # Fetch apps the user has authorized
    cur.execute("""
        SELECT a.id, a.name, a.client_id, u.username AS developer, authorized_at AS authorized_at
        FROM apps a
        JOIN oauth_authorizations o ON a.id = o.app_id
        JOIN users u ON u.id = a.owner_id
        WHERE o.user_id=?
    """, (user["id"],))
    authorized_apps = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        owned_apps=owned_apps,
        pending_requests=pending_app_requests,
        authorized_apps=authorized_apps,
        has_pending_request=has_pending_request,
        pending_request_name=pending_request_name
    )
# --------------------edit app ----------------
@app.route("/app/<app_id>/edit", methods=["GET", "POST"])
def edit_app(app_id):
    if "user_id" not in session:
        flash("❌ Please log in first.", "danger")
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch app and check ownership
    cur.execute("SELECT * FROM apps WHERE id=? AND owner_id=?", (app_id, user["id"]))
    app_data = cur.fetchone()
    if not app_data:
        flash("❌ App not found or access denied.", "danger")
        conn.close()
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        new_name = request.form.get("app_name", "").strip()
        new_redirect = request.form.get("redirect_uri", "").strip()
        new_desc = request.form.get("description", "").strip()

        if new_name and new_redirect:
            cur.execute("""
                UPDATE apps SET name=?, redirect_uri=?, description=?
                WHERE id=?
            """, (new_name, new_redirect, new_desc, app_id))
            conn.commit()
            flash("✅ App updated successfully.", "success")
            conn.close()
            return redirect(url_for("dashboard"))

    conn.close()
    return render_template("edit_app.html", app=app_data, user=user)

# ---------------- Profile ----------------
@app.route("/profile/<username>")
def profile(username):
    user = get_user_by_username(username)
    if not user:
        return "User not found", 404
    return render_template("profile.html", user=user)

# ---------------- Admin ----------------
@app.route("/admin")
def admin():
    if not is_admin():
        return "Unauthorized", 404
    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    # Fetch pending developer requests or apps
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_requests WHERE status='pending'")
    dev_requests = cur.fetchall()
    cur.execute("SELECT * FROM apps")
    apps = cur.fetchall()
    conn.close()

    return render_template("admin.html", user=user,dev_requests=dev_requests, apps=apps)
# ---------------- Developer Tutorial ----------------
@app.route("/tutorial/<app_id>")
def tutorial(app_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM apps WHERE id=? AND owner_id=?", (app_id, user["id"]))
    app = cur.fetchone()
    conn.close()

    if not app:
        flash("❌ App not found or you don't have access.", "danger")
        return redirect(url_for("dashboard"))

    return render_template("developer_tutorial.html", app=app, user=user)

# ---------------- Error Handlers ----------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(403)
def forbidden(e):
    return "Forbidden", 403
@app.route("/app/new", methods=["GET", "POST"])
def request_app():
    if "user_id" not in session:
        flash("❌ Please log in first.", "danger")
        return redirect(url_for("login"))
    
    user_id = session["user_id"]

    if request.method == "POST":
        app_name = request.form.get("app_name", "").strip()
        redirect_uri = request.form.get("redirect_uri", "").strip()
        description = request.form.get("description", "").strip()

        if not app_name or not redirect_uri:
            flash("❌ Fill all required fields.", "danger")
            return redirect(url_for("request_app"))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO app_requests (user_id, app_name, redirect_uri, description)
            VALUES (?, ?, ?, ?)
        """, (user_id, app_name, redirect_uri, description))
        conn.commit()
        conn.close()

        flash("✅ App request submitted. Wait for admin approval.", "success")
        return redirect(url_for("dashboard"))

    return render_template("request_app.html")


# ---------------- Manage Developer Requests ----------------
@app.route("/admin/manage/app-requests")
def manage_app_requests():
    if not is_admin():
        return "Unauthorized", 403

    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_requests WHERE status='pending'")
    app_requests = cur.fetchall()
    conn.close()

    return render_template("manage_app_requests.html", user=user, app_requests=app_requests)


# ---------------- Manage Apps ----------------
@app.route("/admin/manage/apps")
def manage_apps():
    if not is_admin():
        return "Unauthorized", 403

    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM apps")
    apps = cur.fetchall()
    conn.close()

    return render_template(
        "manage_apps.html",
        user=user,
        apps=apps
    )
# ---------------- Revoke App Access ----------------
@app.route("/admin/manage/revoke-access", methods=["GET", "POST"])
def revoke_access():
    if not is_admin():
        return "Unauthorized", 403

    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        target_user_id = request.form.get("user_id")
        app_id = request.form.get("app_id")
        action = request.form.get("action")  # 'user' or 'app'

        if action == "user" and target_user_id:
            cur.execute("DELETE FROM oauth_authorizations WHERE user_id=?", (target_user_id,))
        elif action == "app" and app_id:
            cur.execute("DELETE FROM apps WHERE id=?", (app_id,))
            cur.execute("DELETE FROM oauth_authorizations WHERE app_id=?", (app_id,))

        conn.commit()
        flash("✅ Access revoked successfully", "success")

    # Fetch all users
    cur.execute("SELECT id, username, email, role FROM users")
    users = cur.fetchall()

    # Fetch apps with their owner’s username
    cur.execute("""
        SELECT apps.id, apps.name, apps.client_id, users.username as owner
        FROM apps
        LEFT JOIN users ON apps.owner_id = users.id
    """)
    apps = cur.fetchall()

    conn.close()

    return render_template("revoke_access.html", user=user, users=users, apps=apps)

# ---------------- Manage Users ----------------
@app.route("/admin/manage/users", methods=["GET", "POST"])
def manage_users():
    if not is_admin():
        return "Unauthorized", 403

    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        target_user_id = request.form.get("user_id")
        new_role = request.form.get("role")  # 'user', 'developer', 'admin'
        action = request.form.get("action")  # optional: 'disable' or 'enable'

        if new_role and target_user_id:
            cur.execute("UPDATE users SET role=? WHERE id=?", (new_role, target_user_id))

        if action == "disable" and target_user_id:
            cur.execute("UPDATE users SET is_active=0 WHERE id=?", (target_user_id,))
        elif action == "enable" and target_user_id:
            cur.execute("UPDATE users SET is_active=1 WHERE id=?", (target_user_id,))

        conn.commit()
        flash("✅ User updated successfully", "success")

    cur.execute("SELECT id, username, email, role, is_active FROM users")
    users = cur.fetchall()
    conn.close()

    return render_template("manage_users.html", user=user, users=users)
# ----------------store admin-----------------------
# ---------------- Approve App Request ----------------
@app.route("/admin/manage/app-requests/<request_id>/approve")
def approve_app_request(request_id):
    if not is_admin():
        return "Unauthorized", 403

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch the pending request
    cur.execute("SELECT * FROM app_requests WHERE id=? AND status='pending'", (request_id,))
    req = cur.fetchone()
    if not req:
        flash("❌ Request not found or already processed.", "danger")
        conn.close()
        return redirect(url_for("manage_app_requests"))

    # Generate unique client_id and client_secret
    client_id = generate_token(20)
    client_secret = generate_token(40)

    # Create the app
    cur.execute("""
        INSERT INTO apps (owner_id, name, client_id, client_secret, redirect_uri, description, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (
        req["user_id"],
        req["app_name"],
        client_id,
        client_secret,
        req["redirect_uri"],
        req["description"]
    ))

    # Mark the request as approved
    cur.execute("UPDATE app_requests SET status='approved' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()

    flash(f"✅ App '{req['app_name']}' approved and created successfully!", "success")
    return redirect(url_for("manage_app_requests"))
# ---------------- Set Admin Route ----------------
@app.route("/set-admin/<user_id>")
def set_admin(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Make sure the user exists
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return f"❌ User with ID {user_id} not found.", 404

    # Update role to admin
    cur.execute("UPDATE users SET role='admin' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return f"✅ User '{user['username']}' is now an admin!"


# ---------------- Deny App Request -----------------
@app.route("/admin/manage/app-requests/<request_id>/deny")
def deny_app_request(request_id):
    if not is_admin():
        return "Unauthorized", 403

    conn = get_db_connection()
    cur = conn.cursor()

    # Mark the request as denied
    cur.execute("UPDATE app_requests SET status='denied' WHERE id=? AND status='pending'", (request_id,))
    conn.commit()
    conn.close()

    flash("❌ App request denied.", "warning")
    return redirect(url_for("manage_app_requests"))

# ---------------- Revoke User ----------------
@app.route("/admin/revoke/user/<user_id>")
def revoke_user(user_id):
    if not is_admin():
        return "Unauthorized", 403

    conn = get_db_connection()
    cur = conn.cursor()

    # Prevent revoking yourself
    if session.get("user_id") == user_id:
        flash("❌ You cannot revoke your own account!", "danger")
        return redirect(url_for("revoke_access"))

    # Disable user account (or delete)
    cur.execute("UPDATE users SET role='revoked' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    flash("✅ User access revoked successfully", "success")
    return redirect(url_for("revoke_access"))


# ---------------- Revoke App ----------------
@app.route("/admin/revoke/app/<app_id>")
def revoke_app(app_id):
    if not is_admin():
        return "Unauthorized", 403

    conn = get_db_connection()
    cur = conn.cursor()

    # Option 1: Soft delete (mark app as revoked)
    #cur.execute("UPDATE apps SET status='pending' WHERE id=?", (app_id,))
    # Option 2: Hard delete
    cur.execute("DELETE FROM apps WHERE id=?", (app_id,))
    
    conn.commit()
    conn.close()

    flash("✅ App access revoked successfully", "success")
    return redirect(url_for("revoke_access"))

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=81)
