import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pydantic import ValidationError
from fastapi import status

# Ensure we're in the right path
sys.path.append(os.path.join(os.getcwd(), 'app'))

async def verify_auth_fixes():
    print("--- 🛡️ Starting Auth Fixes Verification ---")
    
    # 1. Verify main.py imports and status
    try:
        from app.main import status as main_status
        print("✅ [main.py] Successfully imported 'status' from FastAPI.")
    except ImportError:
        print("❌ [main.py] Failed to import 'status' from FastAPI.")
    except Exception as e:
        print(f"❌ [main.py] General error during import check: {e}")

    # 2. Verify UserCreate Schema Limit
    from app.schemas.user import UserCreate
    try:
        data = {
            "email": "test@example.com",
            "password": "a" * 100,  # Should fail now
            "display_name": "Test User"
        }
        UserCreate(**data)
        print("❌ [schemas/user.py] Password > 72 chars did NOT raise validation error.")
    except ValidationError as e:
        print("✅ [schemas/user.py] Password > 72 chars correctly raised validation error.")
    except Exception as e:
        print(f"❌ [schemas/user.py] Unexpected error: {e}")

    # 3. Verify AuthService Duplicate Handling
    from app.services.auth import AuthService
    from app.models.user import User
    from pymongo.errors import DuplicateKeyError
    
    auth_service = AuthService()
    
    # Mock User.insert to raise DuplicateKeyError
    mock_user = MagicMock(spec=User)
    mock_user.email = "duplicate@example.com"
    mock_user.insert = AsyncMock(side_effect=DuplicateKeyError("Duplicate email"))
    
    # We need to mock User() constructor inside catch or just bypass it
    # Let's test the catch block logic specifically
    try:
        # Patching inside register_user is hard, let's just inspect the code or use a smaller mock
        from unittest.mock import patch
        with patch('app.services.auth.User', return_value=mock_user):
            with patch.object(AuthService, 'get_user_by_email', return_value=None):
                user_create = UserCreate(email="duplicate@example.com", password="password123", display_name="Test")
                await auth_service.register_user(user_create)
        print("❌ [services/auth.py] DuplicateKeyError was NOT caught.")
    except ValueError as e:
        if str(e) == "Email already registered":
            print("✅ [services/auth.py] DuplicateKeyError correctly caught and raised ValueError.")
        else:
            print(f"❌ [services/auth.py] Caught wrong ValueError: {e}")
    except Exception as e:
        print(f"❌ [services/auth.py] Unexpected error: {type(e).__name__} - {e}")

    print("\n--- ✅ All Verification Checks Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_auth_fixes())
