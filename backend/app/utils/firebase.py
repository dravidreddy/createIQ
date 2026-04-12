"""
Firebase Admin Initialization

Supports two modes:
  1. Local dev: Reads from a JSON file specified by FIREBASE_CREDENTIALS_PATH
  2. Production: Reads from a FIREBASE_CREDENTIALS_JSON env var (raw JSON string)
"""
import json
import os
import logging

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)


def init_firebase():
    """Initialize Firebase Admin app using the best available credentials."""
    # Already initialized — skip
    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    # --- Strategy 1: Raw JSON string from env var (production) ---
    cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if cred_json:
        try:
            service_info = json.loads(cred_json)
            cred = credentials.Certificate(service_info)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized from FIREBASE_CREDENTIALS_JSON env var")
            return
        except Exception as e:
            logger.error(f"Failed to init Firebase from JSON env var: {e}")

    # --- Strategy 2: File path (local dev) ---
    from app.config import get_settings
    settings = get_settings()
    cred_path = getattr(settings, "firebase_credentials_path", None)

    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized from file: {cred_path}")
            return
        except Exception as e:
            logger.error(f"Failed to init Firebase from file: {e}")

    # --- Fallback: GOOGLE_APPLICATION_CREDENTIALS or GCP metadata ---
    try:
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized via default credentials")
    except Exception as e:
        logger.warning(f"Could not initialize Firebase Admin SDK: {e}. Auth features will fail.")


# Auto-initialize on import
init_firebase()
