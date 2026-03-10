import requests
import json

def test_performance_api():
    base_url = "http://localhost:8080"
    login_url = f"{base_url}/api/auth/login"
    performance_url = f"{base_url}/api/analytics/performance?period=Weekly"
    
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
        headers = {"Authorization": f"Bearer {token}"}
        
        print("Fetching performance analytics...")
        res = requests.get(performance_url, headers=headers)
        
        if res.status_code == 200:
            print("Performance API response:")
            print(json.dumps(res.json(), indent=4))
        else:
            print(f"Performance API failed: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_performance_api()
