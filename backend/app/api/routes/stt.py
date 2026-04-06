"""
STT API Endpoints — Speech-to-Text transcription.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Optional
import io

from app.services.stt.router import get_stt_router
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    provider: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Transcribe uploaded audio file to text.
    Supports wav, mp3, m4a, and other standard formats.
    """
    if not file.content_type.startswith("audio/"):
        # Some browsers might send video/mp4 for m4a files
        if not (file.filename.endswith((".m4a", ".mp3", ".wav", ".ogg"))):
            raise HTTPException(status_code=400, detail="Uploaded file must be an audio file")

    try:
        # Read file into memory
        audio_content = await file.read()
        audio_file = io.BytesIO(audio_content)
        audio_file.name = file.filename # Required by some SDKs to detect format
        
        stt_router = get_stt_router()
        text = await stt_router.transcribe(
            audio_file=audio_file,
            provider_name=provider,
            language=language,
            prompt=prompt
        )
        
        return {
            "text": text,
            "filename": file.filename,
            "provider": provider or "groq"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()
