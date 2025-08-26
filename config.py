import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ---------------- General Flask Settings ----------------
class Config:
    DEBUG = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "stybase_session")
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_LIFETIME_DAYS", 7)))

    # ---------------- Database ----------------
    DB_FILE = os.getenv("stybase_DB", "stybase.db")
    DATABASE_URI = f"sqlite:///{DB_FILE}"

    # ---------------- OAuth Settings ----------------
    OAUTH_TOKEN_EXPIRY = int(os.getenv("OAUTH_TOKEN_EXPIRY", 3600))
    OAUTH_REFRESH_EXPIRY = int(os.getenv("OAUTH_REFRESH_EXPIRY", 86400))
    OAUTH_SCOPES = os.getenv("OAUTH_SCOPES", "profile,email,openid").split(",")

    # ---------------- Password / Security ----------------
    PASSWORD_HASH_ALGORITHM = os.getenv("PASSWORD_HASH_ALGORITHM", "sha256")
    PASSWORD_SALT_ROUNDS = int(os.getenv("PASSWORD_SALT_ROUNDS", 12))

    # ---------------- Email Settings ----------------
    EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "False").lower() in ["true", "1", "yes"]
    EMAIL_HOST = os.getenv("EMAIL_HOST", "")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ["true", "1", "yes"]

    # ---------------- App URLs ----------------
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
    LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "/dashboard")
    REGISTER_REDIRECT_URL = os.getenv("REGISTER_REDIRECT_URL", "/dashboard")

    # ---------------- Admin Defaults ----------------
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "super_secure_admin_password")


# ---------------- Dev / Prod configs ----------------
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in production
