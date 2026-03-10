import requests

BASE_URL = "http://localhost:8080/api"

def check_history():
    login_payload = {
        "email": "ryu@g.com",
        "password": "password123",
        "role": "USER"
    }
    res = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("Fetching history...")
    res = requests.get(f"{BASE_URL}/menu/history", headers=headers)
    print(f"Status Code: {res.status_code}")
    try:
        print(f"Response Body: {res.json()}")
    except:
        print(f"Response Body (Raw): {res.text}")

if __name__ == "__main__":
    check_history()
