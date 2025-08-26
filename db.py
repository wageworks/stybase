import sqlite3
from datetime import datetime

DB_FILE = "stybase.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # ---------------- Users ----------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            app_password TEXT NOT NULL, -- permanent app password for OAuth apps
            phone TEXT,
            is_active INTEGER  DEFAULT 1,
            role TEXT NOT NULL DEFAULT 'user',  -- user, developer, admin
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    # --------------------------- app requests -------------------------------------
    c.execute('''CREATE TABLE IF NOT EXISTS app_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    app_name TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending', -- pending, approved, denied
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
''')
    

    # ---------------- Registered Apps ----------------
    c.execute('''
    CREATE TABLE IF NOT EXISTS apps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,  -- developer user ID
        name TEXT NOT NULL,
        client_id TEXT UNIQUE NOT NULL,
        client_secret TEXT NOT NULL,
        redirect_uri TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'active',
        FOREIGN KEY(owner_id) REFERENCES users(id)
    );
    ''')

    #
    # ---------------- OAuth Authorizations ----------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS oauth_authorizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            app_id INTEGER NOT NULL,
            authorized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(app_id) REFERENCES apps(id)
        );
    ''')
    # ---------------- OAuth Tokens ----------------
    c.execute('''
    CREATE TABLE IF NOT EXISTS oauth_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        app_id INTEGER NOT NULL,
        access_token TEXT UNIQUE NOT NULL,
        refresh_token TEXT UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(app_id) REFERENCES apps(id)
    );
''')


    # ---------------- OAuth Access Logs ----------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS oauth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            app_id INTEGER,
            action TEXT NOT NULL,  -- login, revoke, approve, deny
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(app_id) REFERENCES apps(id)
        );
    ''')

    # ---------------- Suggestions (Sociocon) ----------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')

    # ---------------- Admin Notes / Optional Future Features ----------------
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(admin_id) REFERENCES users(id)
        );
    ''')
    #------------------------oauth_codes___________________ 
    c.execute('''CREATE TABLE IF NOT EXISTS oauth_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT,
    expires_at DATETIME NOT NULL,
    used INTEGER DEFAULT 0
);''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_oauth_codes_code ON oauth_codes(code);')


    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# ---------------- Example Usage ----------------
if __name__ == "__main__":
    init_db()
