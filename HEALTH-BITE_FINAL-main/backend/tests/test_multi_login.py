
import requests

BASE_URL = "http://localhost:8080/api/auth"

def test_login_response():
    email = "test99@example.com"
    password = "Password@123"

    print("Logging in...")
    login_data = {"email": email, "password": password, "role": "USER"}
    res = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")

if __name__ == "__main__":
    test_login_response()
