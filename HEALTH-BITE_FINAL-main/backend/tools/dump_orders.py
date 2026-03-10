import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Order
import json

def dump_orders(user_id):
    db = SessionLocal()
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    for o in orders:
        print(f"ID: {o.id}, User: {o.user_id}, Date: {o.created_at}, Price: {o.total_price}")
        print(f"  Items (Raw): {o.items}")
        try:
            items = json.loads(o.items) if o.items else []
            print(f"  Items (Parsed): {items}")
        except Exception as e:
            print(f"  ERROR Parsing Items: {e}")
    db.close()

if __name__ == "__main__":
    dump_orders(11)
