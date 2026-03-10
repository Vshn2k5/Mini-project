import sqlite3
import os

db_path = "canteen.db"

def check_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- USERS ---")
    cursor.execute("SELECT id, name, email, role FROM users LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- LATEST ORDERS ---")
    cursor.execute("SELECT id, user_id, created_at, total_price FROM orders ORDER BY id DESC LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_db()
