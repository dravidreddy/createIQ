"""
Firebase Admin Initialization
"""
import firebase_admin
from firebase_admin import credentials
import logging
import os
from app.config import get_settings

logger = logging.getLogger(__name__)

def init_firebase():
    """Initialize Firebase Admin app using the service account credentials if available."""
    try:
        # Check if already initialized
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    settings = get_settings()
    cred_path = settings.firebase_credentials_path

    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized successfully using {cred_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase with specific path: {e}")
    else:
        # Fallback to default if environment variable GOOGLE_APPLICATION_CREDENTIALS is set
        try:
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized successfully using default credentials.")
        except Exception as e:
            logger.warning(f"Could not initialize Firebase Admin SDK: {e}. Google Auth features will fail.")

# Ensure it's initialized on import if we're not running early in lifecycles, 
# or we can just call it explicitly on startup. We'll call on import for ease.
init_firebase()
