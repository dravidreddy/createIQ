import requests
import uuid
import json

# Integration test to check signup -> login -> getMe flow via real API requests
API_URL = "http://127.0.0.1:8000/api/v1"

def test_full_auth_flow():
    session = requests.Session()
    
    # 1. Signup
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    display_name = "Test User"
    
    print(f"--- 🚀 Testing flow for {email} ---")
    
    signup_resp = session.post(f"{API_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "display_name": display_name
    })
    
    print(f"Signup: {signup_resp.status_code}")
    print(f"Signup Result: {signup_resp.json()}")
    
    if signup_resp.status_code != 201:
        print("❌ Signup failed")
        return

    # 2. Login
    login_resp = session.post(f"{API_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    
    print(f"Login: {login_resp.status_code}")
    print(f"Login Result: {login_resp.json()}")
    print(f"Cookies after login: {session.cookies.get_dict()}")
    
    if login_resp.status_code != 200:
        print("❌ Login failed")
        return

    # 3. getMe
    me_resp = session.get(f"{API_URL}/auth/me")
    print(f"getMe: {me_resp.status_code}")
    print(f"getMe Result: {me_resp.json()}")
    
    if me_resp.status_code == 200:
        print("✅ FULL AUTH FLOW SUCCESSFUL!")
    else:
        print("❌ getMe failed (Unauthorized)")

if __name__ == "__main__":
    test_full_auth_flow()
