import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from auth import pwd_context

def reset_password(email, new_password):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.hashed_password = pwd_context.hash(new_password)
        db.commit()
        print(f"Password reset for {email}")
    else:
        print(f"User {email} not found")
    db.close()

if __name__ == "__main__":
    reset_password("ryu@g.com", "password123")
