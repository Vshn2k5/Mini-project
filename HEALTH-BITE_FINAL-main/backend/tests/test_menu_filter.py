import requests

base_url = "http://localhost:8080/api"

def get_token():
    # Login as test99
    resp = requests.post(f"{base_url}/auth/login", json={'email':'test99@example.com','password':'Password@123','role':'USER'})
    resp.raise_for_status()
    return resp.json()['token']

def set_profile_vegan(token):
    # Get current profile
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(f"{base_url}/health/profile", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    
    # Update to Vegan
    payload = {
        "age": data.get("age", 25),
        "weight_kg": data.get("weight_kg", 70),
        "height_cm": data.get("height_cm", 175),
        "gender": data.get("gender", "male"),
        "health_condition": data.get("health_condition", "normal"),
        "dietary_preference": "Vegan",
        "goal": data.get("goal", "maintain"),
        "activity_level": data.get("activity_level", "medium"),
        "disease": data.get("disease", []),
        "allergies": data.get("allergies", [])
    }
    resp = requests.post(f"{base_url}/health/profile", json=payload, headers=headers)
    resp.raise_for_status()
    print("Profile set to Vegan.")

def test_intelligent_menu(token, strict=False):
    mode = "Dashboard (Strict)" if strict else "Full Menu (Relaxed)"
    print(f"\n--- Testing Intelligent Menu [{mode}] ---")
    resp = requests.get(f"{base_url}/menu/intelligent?strict={'true' if strict else 'false'}", headers={'Authorization': f'Bearer {token}'})
    resp.raise_for_status()
    items = resp.json()
    
    # Check for Non-Veg items based on dietary_type
    non_veg_items = [i['name'] for i in items if "non-veg" in (i.get('dietary_type') or "").lower()]
    print(f"Total items returned: {len(items)}")
    print(f"Non-Veg items found: {len(non_veg_items)}")
    if non_veg_items and strict:
        print("FAIL: Non-Veg items found in strict Vegan menu!")
    elif not non_veg_items and not strict:
        print("FAIL: No Non-Veg items found in relaxed menu (they should be there with penalties)!")
    else:
        print("PASS: Filtering logic correct.")

try:
    token = get_token()
    set_profile_vegan(token)
    test_intelligent_menu(token, strict=True)
    test_intelligent_menu(token, strict=False)
except Exception as e:
    print(f"Test failed: {e}")
