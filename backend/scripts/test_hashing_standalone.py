import sys
import os
from passlib.context import CryptContext

# Test standalone passlib logic on this environment
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_hashing():
    password = "password123"
    hashed = pwd_context.hash(password)
    print(f"Password: {password}")
    print(f"Hashed: {hashed}")
    
    verify_success = pwd_context.verify(password, hashed)
    print(f"Verify Success: {verify_success}")
    
    verify_fail = pwd_context.verify("wrongpassword", hashed)
    print(f"Verify Fail: {verify_fail}")

    if verify_success and not verify_fail:
        print("✅ passlib/bcrypt is working correctly on this system.")
    else:
        print("❌ passlib/bcrypt logic is broken.")

if __name__ == "__main__":
    test_hashing()
