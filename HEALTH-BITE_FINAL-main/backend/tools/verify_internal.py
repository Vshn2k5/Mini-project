import os
import sys
from datetime import datetime

# Add the current directory to sys.path so we can import local modules
sys.path.append(os.getcwd())

from database import SessionLocal
from models import Order, FoodItem

def verify_internal():
    db = SessionLocal()
    try:
        # Check current system time
        now = datetime.now()
        print(f"Current System Time: {now}")
        
        # Create a test order for User ID 1
        # Use existing food item or just create a dummy one
        food = db.query(FoodItem).first()
        food_id = food.id if food else 1
        
        test_order = Order(
            user_id=1,
            items=f"[{food_id}]",
            total_price=0.0,
            total_calories=0.0,
            total_sugar=0.0,
            total_sodium=0.0,
            status="pending",
            payment_method="Test"
        )
        
        db.add(test_order)
        db.commit()
        db.refresh(test_order)
        
        created_at_str = test_order.created_at
        print(f"Order created at (ISO string): {created_at_str}")
        
        # Parse and compare
        order_time = datetime.fromisoformat(created_at_str)
        diff = abs((now - order_time).total_seconds())
        print(f"Time difference: {diff} seconds")
        
        if diff < 10:
            print("SUCCESS: Order timestamp matches local system time!")
        else:
            print("FAILURE: Order timestamp mismatch.")
            
        # Clean up
        db.delete(test_order)
        db.commit()
        print("Test order cleaned up.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_internal()
