import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Order

def inspect_order(order_id):
    db = SessionLocal()
    o = db.query(Order).filter(Order.id == order_id).first()
    if o:
        print(f"ID: {o.id}")
        print(f"User: {o.user_id}")
        print(f"Total Price: {o.total_price}")
        print(f"Total Calories: {o.total_calories}")
        print(f"Total Sugar: {o.total_sugar}")
        print(f"Total Sodium: {o.total_sodium}")
        print(f"Payment Method: {o.payment_method}")
        print(f"Items: {o.items}")
    else:
        print("Order not found")
    db.close()

if __name__ == "__main__":
    inspect_order(21)
