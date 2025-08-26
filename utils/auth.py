from flask import session, redirect, url_for
from utils.security import hash_password, verify_password
from db import get_db_connection

# ---------------- User Registration ----------------
def register_user(username : str, email: str, app_password : str ,password: str, name=None, phone=None, role="user",):
    conn = get_db_connection()
    cur = conn.cursor()
    hashed_pwd = hash_password(password)
    try:
        cur.execute(
            "INSERT INTO users (username, email, password, name, phone, role, app_password) VALUES (?,?, ?, ?, ?, ?, ?)",
            (username, email, hashed_pwd, name, phone, role,app_password)
        )
        conn.commit()
        user_id = cur.lastrowid
    except Exception as e:
        conn.close()
        return None, str(e)
    conn.close()
    return user_id, None

# ---------------- User Login ----------------
def login_user(username_or_email, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? OR email=?", (username_or_email, username_or_email))
    user = cur.fetchone()
    conn.close()
    if user and verify_password(password, user["password"]):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True
        return True, user
    return False, None

# ---------------- Logout ----------------
def logout_user():
    session.clear()
    return redirect(url_for("index"))

# ---------------- Role Checking ----------------
def is_admin():
    if "user_id" not in session:
        return False
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE id = ?", (session["user_id"],))
    row = cur.fetchone()
    if row[0] == 'admin':
        return True
    conn.close()
    return row and row[0] == 1

def is_developer():
    return session.get("role") == "developer"

# ---------------- OAuth Helpers ----------------
def get_user_by_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    conn.close()
    return user
