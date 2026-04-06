"""
DEVTOOLS - Diagnostic Chat
DO NOT import in production code.
"""
import requests
import json
import os
from datetime import datetime
from jose import jwt

from app.config import get_settings
settings = get_settings()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
BASE_URL = f"http://localhost:{os.getenv('PORT', '8000')}"

def generate_test_token(user_id: str = "60f0f1f2f3f4f5f6f7f8f9fa") -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.utcnow().timestamp() + 3600,
        "iat": datetime.utcnow().timestamp()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def test_chat():
    token = generate_test_token()
    payload = {
        "project_id": "60f0f1f2f3f4f5f6f7f8f9fb",
        "topic": "Test quality of tech reviews",
        "blocking": True
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Load-Test-User": "60f0f1f2f3f4f5f6f7f8f9fa",
        "Content-Type": "application/json"
    }
    
    # 1. Check Health first
    print(f"--- Checking Health at {BASE_URL}/health ---")
    try:
        h_res = requests.get(f"{BASE_URL}/health")
        print(f"Health Status: {h_res.status_code}")
        print(f"Health Response: {h_res.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

    # 2. Test Chat
    print(f"\n--- Sending Chat request to {BASE_URL}/api/v1/chat ---")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/chat", json=payload, headers=headers)
        print(f"Status: {response.status_code}")
        print("Response (Formatted):")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
    except Exception as e:
        print(f"Chat request failed: {e}")

if __name__ == "__main__":
    test_chat()
