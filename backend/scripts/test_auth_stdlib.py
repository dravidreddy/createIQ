import http.client
import json
import uuid

API_HOST = "127.0.0.1"
API_PORT = 8000
API_PREFIX = "/api/v1"

def test_flow():
    conn = http.client.HTTPConnection(API_HOST, API_PORT)
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    display_name = "Test User"
    
    print(f"--- 🚀 Testing for {email} ---")
    
    # 1. Signup
    signup_data = {
        "email": email,
        "password": password,
        "display_name": display_name
    }
    conn.request("POST", f"{API_PREFIX}/auth/signup", body=json.dumps(signup_data), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    print(f"Signup: {resp.status}")
    print(f"Signup Body: {resp.read().decode()}")
    
    if resp.status != 201:
        print("❌ Signup failed")
        return

    # 2. Login
    login_data = {"email": email, "password": password}
    conn.request("POST", f"{API_PREFIX}/auth/login", body=json.dumps(login_data), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    print(f"Login: {resp.status}")
    headers = resp.getheaders()
    cookies = [v for k, v in headers if k.lower() == 'set-cookie']
    print(f"Cookies: {cookies}")
    
    body = resp.read().decode()
    print(f"Login Body: {body}")
    
    if resp.status != 200:
        print("❌ Login failed")
        return

    # 3. getMe
    cookie_header = "; ".join([c.split(';')[0] for c in cookies])
    conn.request("GET", f"{API_PREFIX}/auth/me", headers={"Cookie": cookie_header})
    resp = conn.getresponse()
    print(f"getMe: {resp.status}")
    print(f"getMe Body: {resp.read().decode()}")
    
    if resp.status == 200:
        print("✅ SUCCESS!")
    else:
        print("❌ FAILED!")

if __name__ == "__main__":
    test_flow()
