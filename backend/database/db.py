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

    # Detect if this is a cloud DB (Aiven) or local
    is_cloud = "aivencloud.com" in host or os.getenv("DB_SSL", "").lower() == "true"

    config = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }

    # Cloud DBs need SSL
    if is_cloud:
        config["ssl_disabled"] = False
    else:
        # Local MySQL usually has no SSL
        config["ssl_disabled"] = True

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