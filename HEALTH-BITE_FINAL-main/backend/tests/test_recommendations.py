import requests
import json

base_url = "http://localhost:8080/api/recommend-food"

def test_diet(diet_type):
    payload = {
        "age": 25,
        "weight_kg": 70,
        "height_cm": 175,
        "gender": "male",
        "health_condition": "normal",
        "diet_type": diet_type,
        "goal": "maintain",
        "activity_level": "medium",
        "allergies": [],
        "calorie_target": 2000,
        "protein_requirement": 60,
        "carbs_limit": 250,
        "fat_limit": 60
    }
    
    print(f"\n--- Testing Diet: {diet_type} ---")
    try:
        response = requests.post(base_url, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Recommended Foods:")
        for rec in data.get("recommended_food", []):
            print(f" - {rec}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_diet("Vegan")
    test_diet("Veg")
    test_diet("Non-Veg")
