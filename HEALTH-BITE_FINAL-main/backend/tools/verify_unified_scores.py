import requests
import json
import os

BASE_URL = "http://localhost:8080/api"

def test_unified_scoring():
    # 1. Login
    login_data = {"email": "test99@example.com", "password": "password123", "role": "USER"}
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        return
    token = resp.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Full Menu (strict=false)
    print("\n--- Verifying AI Scores (Full Menu) ---")
    resp = requests.get(f"{BASE_URL}/menu/intelligent?strict=false", headers=headers)
    if resp.status_code != 200:
        print(f"Menu fetch failed: {resp.status_code} {resp.text}")
        return
    menu = resp.json()

    # Check some Vegan/Non-Veg samples
    # test99@example.com is set to VEGAN
    samples = [
        "Oats Upma",         # Vegan
        "Boiled Egg Snack",  # Non-Veg
        "Paneer Protein Bowl"# Veg
    ]

    for item_name in samples:
        item = next((i for i in menu if i['name'] == item_name), None)
        if item:
            print(f"Food: {item_name}")
            print(f"  Match Score: {item.get('match_score')}%")
            print(f"  Insight: {item.get('insight')}")
        else:
            print(f"Food: {item_name} not found in menu")

    # 3. Get Dashboard Menu (strict=true)
    print("\n--- Verifying Dashboard (Strict) ---")
    resp = requests.get(f"{BASE_URL}/menu/intelligent?strict=true", headers=headers)
    dashboard_menu = resp.json()
    
    any_caution = any(i.get('match_score', 0) < 85 for i in dashboard_menu)
    print(f"Total Dashboard items: {len(dashboard_menu)}")
    print(f"Any items with score < 85? {'YES' if any_caution else 'NO'}")
    
    if any_caution:
        bad_item = next(i for i in dashboard_menu if i.get('match_score', 0) < 85)
        print(f"Found non-safe item in strict menu: {bad_item['name']} (Score: {bad_item['match_score']})")
    else:
        print("PASS: Dashboard only contains Safe/Recommended foods.")

if __name__ == "__main__":
    test_unified_scoring()
