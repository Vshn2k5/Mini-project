import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import FoodItem

db = SessionLocal()
foods = db.query(FoodItem).all()

non_veg = ["chicken", "egg", "shrimp", "fish", "tuna", "pepperoni", "hot dog", "prawn", "meat", "beef", "mutton"]
dairy = ["paneer", "cheese", "milk", "yoghurt", "yogurt", "butter", "lassi", "crepe", "ice cream", "chocolate", "caramel", "sundae", "donut", "brownie"]

counts = {"Vegan": 0, "Veg": 0, "Non-Veg": 0}

for f in foods:
    n = f.name.lower()
    if any(nv in n for nv in non_veg):
        f.dietary_type = "Non-Veg"
    elif any(d in n for d in dairy):
        f.dietary_type = "Veg"
    else:
        f.dietary_type = "Vegan"
    
    counts[f.dietary_type] += 1

db.commit()
print("Updated database dietary_type flags:", counts)
