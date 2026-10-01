import mysql.connector
import os
from dotenv import load_dotenv
import sys

# Add the parent folder to the path so Python can find .env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


def get_db_connection():
    """Create and return a connection to the MySQL database (local or cloud)."""
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME", "dynasty_integrated_system")

    config = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "auth_plugin": "caching_sha2_password",  # Match MySQL 8 default
        "use_pure": True,
        "ssl_disabled": False,  # ✅ Enable SSL (works on local MySQL 8 too)
        "ssl_verify_cert": False,  # Don't fail on self-signed local certs
        "ssl_verify_identity": False,
    }

    return mysql.connector.connect(**config)


def test_connection():
    """Test the database connection."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchall()
        print("✅ Database connected successfully")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False