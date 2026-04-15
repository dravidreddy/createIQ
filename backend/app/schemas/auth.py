"""
Authentication Schemas

Pydantic schemas for Firebase authentication requests.
"""

from pydantic import BaseModel


class FirebaseTokenRequest(BaseModel):
    """Schema for Firebase ID token login request."""
    token: str
