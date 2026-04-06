"""
Helper script to create an initial admin user in the new MongoDB database.
DEVTOOLS - DO NOT import in production code.
"""

import asyncio
from datetime import datetime
from app.models.database import init_db, close_db
from app.models.user import User
from app.utils.security import hash_password

async def create_admin():
    print("Connecting to MongoDB...")
    await init_db()
    
    email = "admin@example.com"
    password = "changeThisInProd123!"
    display_name = "System Admin"
    
    # Check if user exists
    existing = await User.find_one(User.email == email)
    if existing:
        print(f"User {email} already exists.")
    else:
        print(f"Creating user {email}...")
        user = User(
            email=email,
            hashed_password=hash_password(password),
            display_name=display_name,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await user.insert()
        print(f"Successfully created admin user!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(create_admin())
