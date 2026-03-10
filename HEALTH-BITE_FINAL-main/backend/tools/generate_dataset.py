import csv
import random
import os

from seed_foods import FOODS

# Generate a robust dataset of 500+ samples
num_samples = 600
output_csv = os.path.join(os.path.dirname(__file__), "ai_engine", "dataset.csv")

diet_types = ["veg", "vegan", "high_protein", "low_carb", "normal"]
health_conditions = ["diabetes", "hypertension", "normal"]

# Ensure output directory exists
os.makedirs(os.path.dirname(output_csv), exist_ok=True)

with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # Header matches REQUIRED features from the user prompt
    writer.writerow([
        "bmi", 
        "diet_type", 
        "health_condition", 
        "calorie_target", 
        "calories", 
        "protein", 
        "carbs", 
        "fat", 
        "category", 
        "recommended_food_label"
    ])
    
    for _ in range(num_samples):
        # 1. Generate User Profile
        bmi = round(random.uniform(16.0, 35.0), 1)
        diet_type = random.choice(diet_types)
        health_condition = random.choice(health_conditions)
        
        # Determine logical calorie target based on BMI and condition
        if bmi > 25.0:
            calorie_target = random.choice([1500, 1800, 2000])
        else:
            calorie_target = random.choice([2000, 2200, 2500])
            
        # 2. Select an appropriate Food Item logic
        valid_foods = list(FOODS)
        
        # Hard filters to make model learn realistic health patterns
        if health_condition == "diabetes":
            valid_foods = [f for f in valid_foods if f["sugar"] <= 20]
        if health_condition == "hypertension":
            valid_foods = [f for f in valid_foods if f["sodium"] <= 600]
            
        # Diet type approximations (for synthetic logic generation)
        if diet_type == "high_protein":
            valid_foods = [f for f in valid_foods if f["protein"] >= 15]
        if diet_type == "low_carb":
            valid_foods = [f for f in valid_foods if f["carbs"] <= 40]
            
        # Fallback if filters are too strict
        if not valid_foods:
            valid_foods = list(FOODS)
            
        # Pick the valid recommendation
        food = random.choice(valid_foods)
        
        # 3. Write row
        writer.writerow([
            bmi,
            diet_type,
            health_condition,
            calorie_target,
            food["calories"],
            food["protein"],
            food["carbs"],
            food["fat"],
            food["category"],
            food["name"]  # Target Label
        ])

print(f"Generated {num_samples} samples and saved to {output_csv}")
