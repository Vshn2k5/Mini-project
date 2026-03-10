import requests
import json

BASE_URL = "http://localhost:8080/api/auth"

def test_admin_login():
    payload = {
        "email": "admin1@example.com",
         # Wait, seed_users.py says Admin@1234!
        "password": "Admin@123!",
        "role": "ADMIN",
        "admin_key": "HB-ADMIN-2026"
    }
    
    print(f"Testing login for {payload['email']}...")
    try:
        response = requests.post(f"{BASE_URL}/login", json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Login successful!")
            print(f"Token: {data['token'][:20]}...")
            print(f"Role: {data['role']}")

            # Additional sanity check: compare dashboard low-stock count against
            # inventory listing (should exclude out-of-stock items).
            headers = {"Authorization": f"Bearer {data['token']}"}
            try:
                inv_resp = requests.get("http://localhost:8000/api/admin/inventory/", headers=headers)
                ov_resp = requests.get("http://localhost:8000/api/admin/overview", headers=headers)
                if inv_resp.status_code == 200 and ov_resp.status_code == 200:
                    inv_data = inv_resp.json()
                    ov_data = ov_resp.json()
                    # count low-stock items ignoring out-of-stock
                    low_count = sum(1 for item in inv_data.get('items', [])
                                     if item['current_stock'] > 0 and item['current_stock'] < item['reorder_level'])
                    dash_count = ov_data.get('lowStock', {}).get('value')
                    print(f"Dashboard low-stock={dash_count}, inventory computed={low_count}")
                    if low_count != dash_count:
                        print("WARNING: Mismatch between dashboard and inventory low-stock counts")
                else:
                    print("Failed to fetch inventory/overview for comparison")
            except Exception as e:
                print(f"Error during low-stock check: {e}")
        else:
            print(f"Login failed: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_admin_login()
