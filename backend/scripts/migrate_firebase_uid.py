"""
One-time script to migrate existing MongoDB users to Firebase authentication.
Finds all users without a `firebase_uid`, looks them up in Firebase,
and updates their MongoDB record.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.models.database import init_db, close_db
from app.models.user import User
from app.utils.firebase import init_firebase
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import NotFoundError

async def run_migration():
    print("Initializing Firebase & MongoDB...")
    init_firebase()
    await init_db()

    # Find users missing firebase_uid
    # Beanie representation for where field is null or missing
    users = await User.find(
        {"$or": [{"firebase_uid": {"$exists": False}}, {"firebase_uid": None}]}
    ).to_list()

    if not users:
        print("✅ All users have a firebase_uid. No migration needed.")
        await close_db()
        return

    print(f"Found {len(users)} users needing migration.")

    success_count = 0
    not_found_count = 0
    error_count = 0

    for user in users:
        print(f"\nProcessing user: {user.email} (ID: {user.id})")
        
        try:
            # 1. Lookup in Firebase by email
            fb_user = firebase_auth.get_user_by_email(user.email)
            print(f"  Found in Firebase (UID: {fb_user.uid})")
            
            # 2. Update MongoDB record
            user.firebase_uid = fb_user.uid
            await user.save()
            print("  ✅ Successfully linked firebase_uid in MongoDB.")
            success_count += 1
            
        except TypeError: # Some get_user_by_email failures raise TypeError from inner proto
            print("  ❌ User not found in Firebase. (TypeError)")
            not_found_count += 1
        except Exception as e:
            if "NOT_FOUND" in str(e) or "UserRecord" not in str(type(e)):
                # Handle generic exceptions indicating not found or other errors
                 if hasattr(e, 'code') and e.code == 'USER_NOT_FOUND':
                     print("  ❌ User not found in Firebase.")
                     not_found_count += 1
                 else:
                     print(f"  ❌ Error processing user: {e}")
                     error_count += 1
            else:
                 print(f"  ❌ Error processing user: {e}")
                 error_count += 1

    print("\n" + "="*40)
    print("Migration Summary")
    print("="*40)
    print(f"Total Users Processed: {len(users)}")
    print(f"Successfully Linked:   {success_count}")
    print(f"Not Found in Firebase: {not_found_count}")
    print(f"Errors Encountered:    {error_count}")

    if not_found_count > 0:
        print("\n⚠️ Note: Users 'Not Found' in Firebase cannot log in.")
        print("You may need to manually create them in the Firebase Console")
        print("or delete their MongoDB records if they are test accounts.")

    await close_db()

if __name__ == "__main__":
    asyncio.run(run_migration())
