import sys
import os

# Add backend to path
sys.path.append('h:/HEALTH-BITE_FINAL-main/HEALTH-BITE_FINAL-!@/HEALTH-BITE_FINAL-main/backend')

from database import SessionLocal
from models import User, HealthProfile, Order
from routes.admin_users import list_users
import json

db = SessionLocal()
try:
    # 1. Check if users exist in the session
    users = db.query(User).all()
    print(f"Total users in DB: {len(users)}")
    for u in users:
        print(f"User: {u.name}, Email: {u.email}, Role: {u.role}")

    # 2. Simulate the list_users route logic manually to see where it fails
    print("\nSimulating list_users route logic...")
    q = db.query(User)
    total = q.count()
    items = q.offset(0).limit(20).all()
    print(f"Total from count(): {total}")
    print(f"Items from query: {len(items)}")

    results = []
    for u in items:
        print(f" Processing user: {u.name} (ID: {u.id})")
        risk_level = "Unknown"
        risk_score = 0
        conditions = []
        dietary_preferences = []
        
        if u.health_profile:
            print(f"  Has health profile")
            risk_level = u.health_profile.risk_level or "Unknown"
            risk_score = u.health_profile.risk_score or 0
            try:
                disease_str = u.health_profile.disease or "[]"
                if "'" in disease_str and '"' not in disease_str:
                    disease_str = disease_str.replace("'", '"')
                conditions = json.loads(disease_str)
            except Exception as e:
                print(f"  Error parsing disease: {e}")
                conditions = [u.health_profile.disease] if u.health_profile.disease and u.health_profile.disease != "None" else []
            dietary_preferences = [u.health_profile.dietary_preference] if u.health_profile.dietary_preference else []

        total_orders = len(u.orders)
        total_spent = sum(o.total_price for o in u.orders) if u.orders else 0
        avg_value = round(total_spent / total_orders, 2) if total_orders > 0 else 0
        print(f"  Orders: {total_orders}, Spent: {total_spent}")

        compliance = 100 - (risk_score // 2) if risk_score < 100 else 10
        top_cat = "Salads & Proteins" if risk_level == "Low" else "Controlled Grains"
        
        results.append({ "id": u.id, "name": u.name, "role": u.role })

    print(f"\nFinal Results Length: {len(results)}")
    print("Successly completed logic simulation.")

finally:
    db.close()
