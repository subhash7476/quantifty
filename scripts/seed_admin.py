import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.database.manager import DatabaseManager, DatabaseDomain
from core.auth.password import hash_password

db = DatabaseManager(Path("data"))
pw = hash_password("admin123")

with db.write(DatabaseDomain.CONFIG) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            roles TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO users (username, password_hash, roles) VALUES (?, ?, ?)",
        ["admin", pw, "admin"],
    )

print("Admin user created: admin / admin123")
