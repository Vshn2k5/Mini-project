import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import FoodItem, Inventory
from datetime import datetime

def sync_foods():
    db = SessionLocal()
    
    # Target foods from dataset_generator.py
    foods_to_add = [
        # Vegan Foods
        {
            "name": "Oats Upma", "category": "Breakfast", "dietary_type": "Vegan",
            "price": 80.0, "calories": 220.0, "protein": 8.0, "carbs": 40.0, "fat": 6.0, "sugar": 2.0, "sodium": 450.0,
            "image_emoji": "🥣"
        },
        {
            "name": "Vegetable Idli", "category": "Breakfast", "dietary_type": "Vegan",
            "price": 60.0, "calories": 180.0, "protein": 6.0, "carbs": 35.0, "fat": 2.0, "sugar": 1.0, "sodium": 400.0,
            "image_emoji": "⚪"
        },
        {
            "name": "Ragi Dosa", "category": "Breakfast", "dietary_type": "Vegan",
            "price": 85.0, "calories": 240.0, "protein": 7.0, "carbs": 45.0, "fat": 6.0, "sugar": 1.0, "sodium": 500.0,
            "image_emoji": "🥞"
        },
        {
            "name": "Vegetable Salad", "category": "Snacks", "dietary_type": "Vegan",
            "price": 120.0, "calories": 120.0, "protein": 4.0, "carbs": 20.0, "fat": 3.0, "sugar": 4.0, "sodium": 200.0,
            "image_emoji": "🥗"
        },
        {
            "name": "Brown Rice Veg Meal", "category": "Lunch", "dietary_type": "Vegan",
            "price": 180.0, "calories": 450.0, "protein": 15.0, "carbs": 80.0, "fat": 10.0, "sugar": 3.0, "sodium": 600.0,
            "image_emoji": "🍱"
        },
        {
            "name": "Sprouts Salad", "category": "Snacks", "dietary_type": "Vegan",
            "price": 110.0, "calories": 200.0, "protein": 14.0, "carbs": 30.0, "fat": 4.0, "sugar": 3.0, "sodium": 300.0,
            "image_emoji": "🌱"
        },
        {
            "name": "Fruit Bowl", "category": "Snacks", "dietary_type": "Vegan",
            "price": 130.0, "calories": 150.0, "protein": 2.0, "carbs": 35.0, "fat": 1.0, "sugar": 25.0, "sodium": 10.0,
            "image_emoji": "🍎"
        },
        {
            "name": "Sambar Idli", "category": "Breakfast", "dietary_type": "Vegan",
            "price": 90.0, "calories": 210.0, "protein": 8.0, "carbs": 42.0, "fat": 3.0, "sugar": 2.0, "sodium": 550.0,
            "image_emoji": "🍲"
        },
        {
            "name": "Vegetable Upma", "category": "Breakfast", "dietary_type": "Vegan",
            "price": 75.0, "calories": 230.0, "protein": 7.0, "carbs": 48.0, "fat": 5.0, "sugar": 2.0, "sodium": 480.0,
            "image_emoji": "🥣"
        },
        {
            "name": "Kerala Avial", "category": "Lunch", "dietary_type": "Vegan",
            "price": 140.0, "calories": 180.0, "protein": 5.0, "carbs": 15.0, "fat": 12.0, "sugar": 2.0, "sodium": 420.0,
            "image_emoji": "🥥"
        },
        {
            "name": "Red Rice Meal", "category": "Lunch", "dietary_type": "Vegan",
            "price": 170.0, "calories": 420.0, "protein": 12.0, "carbs": 75.0, "fat": 8.0, "sugar": 2.0, "sodium": 580.0,
            "image_emoji": "🍚"
        },
        {
            "name": "Chickpea Curry", "category": "Lunch", "dietary_type": "Vegan",
            "price": 150.0, "calories": 320.0, "protein": 15.0, "carbs": 45.0, "fat": 12.0, "sugar": 4.0, "sodium": 650.0,
            "image_emoji": "🥘"
        },
        {
            "name": "Lentil Soup", "category": "Snacks", "dietary_type": "Vegan",
            "price": 100.0, "calories": 190.0, "protein": 14.0, "carbs": 30.0, "fat": 2.0, "sugar": 2.0, "sodium": 480.0,
            "image_emoji": "🥣"
        },
        # Veg Foods
        {
            "name": "Paneer Protein Bowl", "category": "Lunch", "dietary_type": "Veg",
            "price": 220.0, "calories": 380.0, "protein": 25.0, "carbs": 20.0, "fat": 22.0, "sugar": 4.0, "sodium": 700.0,
            "image_emoji": "🧀"
        },
        {
            "name": "Grilled Paneer Wrap", "category": "Snacks", "dietary_type": "Veg",
            "price": 190.0, "calories": 420.0, "protein": 22.0, "carbs": 45.0, "fat": 18.0, "sugar": 5.0, "sodium": 750.0,
            "image_emoji": "🌯"
        },
        {
            "name": "Greek Yogurt Bowl", "category": "Breakfast", "dietary_type": "Veg",
            "price": 160.0, "calories": 280.0, "protein": 18.0, "carbs": 25.0, "fat": 12.0, "sugar": 15.0, "sodium": 150.0,
            "image_emoji": "🍦"
        }
    ]

    added_count = 0
    for food_data in foods_to_add:
        # Check if already exists
        existing = db.query(FoodItem).filter(FoodItem.name == food_data["name"]).first()
        if not existing:
            new_food = FoodItem(
                name=food_data["name"],
                category=food_data["category"],
                dietary_type=food_data["dietary_type"],
                price=food_data["price"],
                calories=food_data["calories"],
                protein=food_data["protein"],
                carbs=food_data["carbs"],
                fat=food_data["fat"],
                sugar=food_data["sugar"],
                sodium=food_data["sodium"],
                image_emoji=food_data["image_emoji"],
                is_available=True
            )
            db.add(new_food)
            db.flush() # Get the ID
            
            # Add inventory
            new_inv = Inventory(food_id=new_food.id, current_stock=100)
            db.add(new_inv)
            
            added_count += 1
            print(f"Added: {food_data['name']}")
        else:
            print(f"Skipped (exists): {food_data['name']}")
    
    db.commit()
    print(f"\nSuccessfully added {added_count} new food items to DB and Inventory.")
    db.close()

if __name__ == "__main__":
    sync_foods()
