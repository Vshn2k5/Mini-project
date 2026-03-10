import requests

base_url = "http://localhost:8080/api"
diet_type = "Vegan"

def get_token():
    resp = requests.post(f"{base_url}/auth/login", json={'email':'test99@example.com','password':'Password@123','role':'USER'})
    resp.raise_for_status()
    return resp.json()['token']

def test_ml_recs(token):
    print(f"\n--- Testing ML Recommendations (Diet: {diet_type}) ---")
    payload = {
        "age": 25, "weight_kg": 70, "height_cm": 175, "gender": "male",
        "health_condition": "normal", "diet_type": diet_type, "goal": "maintain",
        "activity_level": "medium", "bmi": 22.5, "calorie_target": 2000,
        "protein_requirement": 60, "carbs_limit": 250, "fat_limit": 60
    }
    resp = requests.post(f"{base_url}/recommend-food", json=payload, headers={'Authorization': f'Bearer {token}'})
    try:
        resp.raise_for_status()
        for rec in resp.json().get("recommended_food", []):
            print(f" - {rec}")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print(f"Response Body: {resp.text}")

def test_intelligent_menu(token, strict=False):
    mode = "Dashboard (Strict)" if strict else "Full Menu (Relaxed)"
    print(f"\n--- Testing Intelligent Menu [{mode}] ---")
    resp = requests.get(f"{base_url}/menu/intelligent?strict={'true' if strict else 'false'}", headers={'Authorization': f'Bearer {token}'})
    resp.raise_for_status()
    items = resp.json()
    
    # Check for Non-Veg items if not strict
    non_veg_found = any("non-veg" in (i.get('dietary_type') or "").lower() for i in items)
    print(f"Total items: {len(items)}")
    print(f"Non-Veg items present: {non_veg_found}")
    
    for item in items[:5]: # Print first 5
        print(f" - {item['name']} (Score: {item['match_score']}, Insight: {item['insight']})")

try:
    token = get_token()
    test_ml_recs(token)
    test_intelligent_menu(token, strict=True)
    test_intelligent_menu(token, strict=False)
except Exception as e:
    print(f"Test failed: {e}")
