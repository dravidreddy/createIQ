"""
AI Tools Routes — Standalone AI-powered tools.

Endpoints:
  POST /tools/hook-test           — Score a script's hook strength
  POST /tools/thumbnail-brief     — Generate thumbnail concept from script
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


# ── Hook Tester ─────────────────────────────────────────────────

class HookTestRequest(BaseModel):
    """Request body for hook testing."""
    script_text: str = Field(
        ...,
        min_length=10,
        description="Full script text (first ~150 words will be analyzed)",
    )
    niche: str = Field(default="", description="Content niche for context-aware scoring")
    platform: str = Field(default="", description="Target platform for context-aware scoring")


class HookBreakdown(BaseModel):
    curiosity_gap: int = 0
    emotional_trigger: int = 0
    specificity: int = 0
    pattern_interrupt: int = 0
    relevance: int = 0


class HookRewrite(BaseModel):
    text: str = ""
    predicted_score: float = 0
    improvement: str = ""


class HookTestResponse(BaseModel):
    overall_score: float = 0
    breakdown: HookBreakdown = Field(default_factory=HookBreakdown)
    hook_text: str = ""
    verdict: str = ""
    rewrites: list = []


@router.post(
    "/hook-test",
    response_model=HookTestResponse,
    summary="Test hook strength of a script",
)
async def test_hook(
    body: HookTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Score the first 30 seconds of a script for hook strength.

    Returns an overall score (1-10), breakdown across 4 dimensions,
    a verdict, and 2-3 rewrite suggestions.
    """
    from app.agents.sub_agents.hook_tester import HookTesterAgent

    agent = HookTesterAgent()
    try:
        result = await agent.execute({
            "script_text": body.script_text,
            "niche": body.niche,
            "platform": body.platform,
        })
        # Remove internal _meta from response
        result.pop("_meta", None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hook analysis failed: {str(e)}")


# ── Thumbnail Brief ─────────────────────────────────────────────

class ThumbnailBriefRequest(BaseModel):
    """Request body for thumbnail brief generation."""
    script_text: str = Field(..., min_length=10, description="The script content")
    hook_text: str = Field(default="", description="The hook text (optional)")
    topic: str = Field(default="", description="The video topic")


class ThumbnailBriefResponse(BaseModel):
    primary_text: str = ""
    secondary_text: str = ""
    expression: str = ""
    color_scheme: str = ""
    layout: str = ""
    elements: list = []
    style_reference: str = ""
    emotional_hook: str = ""
    contrast_tip: str = ""


@router.post(
    "/thumbnail-brief",
    response_model=ThumbnailBriefResponse,
    summary="Generate thumbnail concept from script",
)
async def generate_thumbnail_brief(
    body: ThumbnailBriefRequest,
    current_user: User = Depends(get_current_user),
):
    """Auto-generate a thumbnail concept brief from a finished script.

    Returns a structured brief with text overlay, expression, color scheme,
    layout guidance, and visual elements.
    """
    from app.agents.sub_agents.thumbnail_brief import ThumbnailBriefAgent

    agent = ThumbnailBriefAgent()
    try:
        result = await agent.execute({
            "script": body.script_text,
            "hook": body.hook_text,
            "topic": body.topic,
        })
        result.pop("_meta", None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail brief generation failed: {str(e)}")


# ── Competitor Analysis ─────────────────────────────────────────

class CompetitorAnalysisRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")


class CompetitorAnalysisResponse(BaseModel):
    hook_breakdown: dict = {}
    core_message: str = ""
    structure: list = []
    pattern_interrupts: list = []
    pacing_and_tone: str = ""
    call_to_action: dict = {}


@router.post(
    "/competitor-analysis",
    response_model=CompetitorAnalysisResponse,
    summary="Reverse-engineer competitor YouTube script",
)
async def analyze_competitor(
    body: CompetitorAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """Fetch transcript from a YouTube URL and extract script structure/tactics."""
    import re
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    from app.agents.sub_agents.competitor_analyzer import CompetitorAnalyzerAgent

    # Extract Video ID
    video_id = ""
    if "youtu.be/" in body.url:
        video_id = body.url.split("youtu.be/")[1].split("?")[0]
    else:
        match = re.search(r"v=([a-zA-Z0-9_-]{11})", body.url)
        if match:
            video_id = match.group(1)

    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Cannot find video ID.")

    # Fetch Transcript
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list])
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise HTTPException(status_code=400, detail="No English transcript found for this video.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")

    # Analyze with Agent
    agent = CompetitorAnalyzerAgent()
    try:
        result = await agent.execute({
            "transcript": transcript_text
        })
        result.pop("_meta", None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
