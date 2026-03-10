import requests
import json

BASE_URL = "http://localhost:8080/api"

def test_orders():
    # 1. Login
    login_payload = {
        "email": "ryu@g.com",
        "password": "password123",
        "role": "USER"
    }
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    if res.status_code != 200:
        print("Login failed:", res.text)
        return
    
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get menu to find a food item
    print("Fetching menu...")
    res = requests.get(f"{BASE_URL}/menu/intelligent", headers=headers)
    menu = res.json()
    if not menu:
        print("Menu is empty")
        return
    
    food = menu[0]
    print(f"Selected food: {food['name']} (ID: {food['id']}, Stock: {food['stock']})")

    # 3. Place order
    order_payload = {
        "items": [{"food_id": food['id'], "quantity": 1}],
        "total_price": food['price'],
        "total_calories": food['calories'],
        "total_sugar": food['sugar'],
        "total_sodium": food['sodium'],
        "payment_method": "Cash"
    }
    print("Placing order...")
    res = requests.post(f"{BASE_URL}/menu/order", headers=headers, json=order_payload)
    if res.status_code != 200:
        print("Order placement failed:", res.text)
        return
    
    order = res.json()
    print(f"Order response: {order}")
    print(f"Order placed! ID: {order['id']}, Created At: {order['created_at']}")

    # 4. Check history
    print("Fetching order history...")
    res = requests.get(f"{BASE_URL}/menu/history", headers=headers)
    history = res.json()
    print(f"Found {len(history)} orders in history.")
    
    latest_order = history[0]
    print(f"Latest Order ID: {latest_order['id']}, Price: {latest_order['total_price']}")

    # 5. Verify inventory reduction
    print("Verifying inventory reduction...")
    res = requests.get(f"{BASE_URL}/menu/intelligent", headers=headers)
    new_menu = res.json()
    new_food = next(f for f in new_menu if f['id'] == food['id'])
    print(f"New Stock: {new_food['stock']} (Previous: {food['stock']})")
    
    if new_food['stock'] == food['stock'] - 1:
        print("SUCCESS: Inventory correctly decremented.")
    else:
        print("FAILURE: Inventory was not updated correctly.")

if __name__ == "__main__":
    test_orders()
