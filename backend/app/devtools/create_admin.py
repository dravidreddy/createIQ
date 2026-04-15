"""
Helper script to create an initial admin user via Firebase Admin SDK.
DEVTOOLS - DO NOT import in production code.
"""

import asyncio
from datetime import datetime
from app.models.database import init_db, close_db
from app.models.user import User
from app.utils.firebase import init_firebase
from firebase_admin import auth as firebase_auth

async def create_admin():
    print("Initializing Firebase & MongoDB...")
    init_firebase()
    await init_db()
    
    email = "admin@example.com"
    password = "changeThisInProd123!"
    display_name = "System Admin"
    
    # 1. Create in Firebase
    try:
        fb_user = firebase_auth.get_user_by_email(email)
        print(f"User {email} already exists in Firebase (UID: {fb_user.uid}).")
    except firebase_auth.UserNotFoundError:
        print(f"Creating user {email} in Firebase...")
        fb_user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=True
        )
        print(f"Successfully created Firebase user (UID: {fb_user.uid})")

    # 2. Upsert in MongoDB
    existing = await User.find_one(User.email == email)
    if existing:
        print(f"User {email} already exists in MongoDB.")
        if existing.firebase_uid != fb_user.uid:
            print("Updating MongoDB record with new Firebase UID...")
            existing.firebase_uid = fb_user.uid
            await existing.save()
    else:
        print(f"Creating user {email} in MongoDB...")
        user = User(
            email=email,
            display_name=display_name,
            firebase_uid=fb_user.uid,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await user.insert()
        print(f"Successfully created admin user in MongoDB!")

    print(f"\nEmail: {email}")
    print(f"Password: {password}")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(create_admin())
