"""
Voice Profile Routes — Creator voice learning API.

Endpoints:
  POST   /voice/analyze  — analyze scripts and save voice profile
  GET    /voice/profile   — get current voice profile
  DELETE /voice/profile   — reset voice profile
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.voice_profile import VoiceProfileService

router = APIRouter()


class VoiceAnalyzeRequest(BaseModel):
    """Request body for voice analysis."""
    scripts: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="2-3 sample scripts from the creator (plain text)",
    )


class VoiceProfileResponse(BaseModel):
    """Voice profile data."""
    tone: str = ""
    avg_sentence_length: int = 0
    hook_style: str = ""
    vocabulary_level: str = ""
    signature_phrases: List[str] = []
    pacing: str = ""
    formality: str = ""
    engagement_style: str = ""
    emotional_range: str = ""
    analyzed_at: str = ""
    sample_count: int = 0


@router.post(
    "/analyze",
    response_model=VoiceProfileResponse,
    summary="Analyze scripts to learn creator voice",
)
async def analyze_voice(
    body: VoiceAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """Upload 2-3 old scripts and the AI will learn your unique voice/style.

    The extracted profile will be automatically applied to all future
    script generations.
    """
    service = VoiceProfileService()
    try:
        profile = await service.analyze_and_save(
            str(current_user.id), body.scripts
        )
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice analysis failed: {str(e)}")


@router.get(
    "/profile",
    summary="Get current voice profile",
)
async def get_voice_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the creator's current voice profile, or null if not set."""
    service = VoiceProfileService()
    profile = await service.get_voice_profile(str(current_user.id))
    if not profile:
        return {"profile": None, "message": "No voice profile set. Upload scripts to analyze."}
    return {"profile": profile}


@router.delete(
    "/profile",
    summary="Reset voice profile",
)
async def reset_voice_profile(
    current_user: User = Depends(get_current_user),
):
    """Reset the voice profile. Future scripts will use default AI voice."""
    service = VoiceProfileService()
    success = await service.reset_voice_profile(str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="User profile not found")
    return {"message": "Voice profile reset successfully"}
