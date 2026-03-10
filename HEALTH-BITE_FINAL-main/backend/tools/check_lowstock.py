import requests

BASE = "http://localhost:8080"
login = requests.post(f"{BASE}/api/auth/login", json={
    "email": "admin1@example.com",
    "password": "Admin@123!",
    "role": "ADMIN",
    "admin_key": "HB-ADMIN-2026"
})
print("login status", login.status_code, login.text)
if login.status_code != 200:
    exit(1)
token = login.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
inv = requests.get(f"{BASE}/api/admin/inventory/", headers=headers).json()
print("summary", inv.get("summary"))
for item in inv.get("items", []):
    if item["current_stock"] < item["reorder_level"]:
        print("low stock item", item)
