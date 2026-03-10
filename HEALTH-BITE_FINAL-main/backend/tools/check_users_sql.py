import sys
import os
sys.path.append(os.getcwd())
try:
    from database import SessionLocal
    from models import User
    db = SessionLocal()
    count = db.query(User).count()
    users = db.query(User).all()
    print(f"SQLAlchemy User count: {count}")
    for u in users:
        print(f"ID: {u.id}, Name: {u.name}, Role: {u.role}")
    db.close()
except Exception as e:
    print(f"Error: {e}")
