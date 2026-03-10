import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "..", "canteen.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if "created_at" not in columns:
            print("Adding 'created_at' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT '2024-01-01 00:00:00'")
        else:
            print("'created_at' column already exists.")

        if "last_active" not in columns:
            print("Adding 'last_active' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_active DATETIME DEFAULT '2024-01-01 00:00:00'")
        else:
            print("'last_active' column already exists.")

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
