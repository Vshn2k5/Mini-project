import requests
import json
import datetime
import os

API_ROOT = "http://127.0.0.1:8000/api"

def get_token():
    # Attempt to login as user to get token
    login_payload = {
        "email": "user@example.com",
        "password": "Password123!",
        "role": "USER"
    }
    try:
        res = requests.post(f"{API_ROOT}/auth/login", json=login_payload)
        data = res.json()
        print(f"Login Response: {data}")
        return data.get("token")
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def verify_order_time():
    token = get_token()
    if not token:
        print("Could not get token. Make sure a user exists.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # Place a dummy order
    order_payload = {
        "items": [{"food_id": 1, "quantity": 1}],
        "total_price": 100.0,
        "total_calories": 200.0,
        "total_sugar": 10.0,
        "total_sodium": 50.0,
        "payment_method": "Cash"
    }
    
    now = datetime.datetime.now()
    print(f"Current System Time: {now}")
    res = requests.post(f"{API_ROOT}/menu/order", json=order_payload, headers=headers)
    
    if res.status_code == 200:
        order = res.json()
        created_at = order.get('created_at')
        print(f"Order Placed. Created At: {created_at}")
        
        # Verify it's within 1 minute of 'now'
        # ISO format: 2026-03-02T10:31:45.123456
        order_time = datetime.datetime.fromisoformat(created_at)
        diff = abs((now - order_time).total_seconds())
        print(f"Difference: {diff} seconds")
        if diff < 60:
            print("SUCCESS: Order time matches local system time.")
        else:
            print("FAILURE: Order time mismatch detected.")
    else:
        print(f"Failed to place order: {res.text}")

if __name__ == "__main__":
    verify_order_time()
