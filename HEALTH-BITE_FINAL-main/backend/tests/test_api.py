import requests

resp = requests.post('http://127.0.0.1:8000/api/auth/login', json={'email':'admin@canteen.local','password':'Admin@123','role':'ADMIN'})
with open('backend/api_test_result.txt','w') as out:
    out.write(f"login {resp.status_code} {resp.text}\n")
    if resp.ok:
        token = resp.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        u = requests.get('http://127.0.0.1:8000/api/admin/users', headers=headers)
        f = requests.get('http://127.0.0.1:8000/api/admin/foods', headers=headers)
        out.write(f"users {u.status_code} {u.text[:2000]}\n")
        out.write(f"foods {f.status_code} {f.text[:2000]}\n")
