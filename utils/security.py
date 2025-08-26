from typing import Optional
import hashlib
import hmac
import secrets

# ---------------- Password Hashing ----------------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash a password with optional salt using SHA256.
    Returns a string in the format: salt$hash
    """
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hashed value (salt$hash format).
    """
    try:
        salt, pwd_hash = hashed.split("$")
        return hmac.compare_digest(hashlib.sha256((salt + password).encode()).hexdigest(), pwd_hash)
    except Exception:
        return False

# ---------------- Token Generation ----------------
def generate_token(length: int = 32) -> str:
    """
    Generate a secure random token of given byte length.
    """
    return secrets.token_hex(length)

def generate_client_secret(length: int = 40) -> str:
    """
    Generate secure client secret for OAuth apps.
    """
    return secrets.token_hex(length)
