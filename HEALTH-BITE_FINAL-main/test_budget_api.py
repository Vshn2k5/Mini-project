import requests
import json

def test_budget_api():
    base_url = "http://localhost:8080"
    login_url = f"{base_url}/api/auth/login"
    budget_url = f"{base_url}/api/analytics/budget"
    
    login_data = {
        "email": "admin@canteen.local", 
        "password": "Admin@123", 
        "role": "ADMIN", 
        "admin_key": "HB-ADMIN-2026"
    }
    
    print("Logging in...")
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json().get("token")
        print(f"Login successful. Token: {token[:20]}...")
        
        headers = {"Authorization": f"Bearer {token}"}
        print("Fetching budget analytics...")
        res = requests.get(budget_url, headers=headers)
        
        if res.status_code == 200:
            print("Budget API response:")
            print(json.dumps(res.json(), indent=4))
        else:
            print(f"Budget API failed: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_budget_api()
