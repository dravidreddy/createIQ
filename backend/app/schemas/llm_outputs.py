"""Loose schemas for validating LLM JSON outputs before pipeline use."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrendResearchOutput(BaseModel):
    research_results: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class IdeaGenerationOutput(BaseModel):
    ideas: List[Dict[str, Any]] = Field(default_factory=list)
    selection_rationale: Optional[str] = None


class IdeaRankingOutput(BaseModel):
    ranked_ideas: List[Dict[str, Any]] = Field(default_factory=list)


class HookCreationOutput(BaseModel):
    hooks: List[Dict[str, Any]] = Field(default_factory=list)


class HookEvaluationOutput(BaseModel):
    evaluated_hooks: List[Dict[str, Any]] = Field(default_factory=list)


class DeepResearchOutput(BaseModel):
    research: List[Dict[str, Any]] = Field(default_factory=list)
    context_summary: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    research_summary: Optional[str] = None


class ScriptDraftOutput(BaseModel):
    title: Optional[str] = None
    hook_block: Dict[str, Any] = Field(default_factory=dict)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    full_script: str = ""
    retention_strategy: Optional[str] = None
    pacing_plan: Optional[str] = None


class FactCheckOutput(BaseModel):
    verified_claims: List[Any] = Field(default_factory=list)
    unverified_claims: List[Any] = Field(default_factory=list)
    corrections: List[Dict[str, Any]] = Field(default_factory=list)
    corrected_script: str = ""
    credibility_score: Optional[float] = None
    verification_summary: Optional[str] = None


class FinalReviewOutput(BaseModel):
    quality_score: float = 0.0
    final_script: str = ""
    improvement_summary: Optional[str] = None
    changes_made: List[Any] = Field(default_factory=list)


class SeriesPlanOutput(BaseModel):
    series_plan: List[Dict[str, Any]] = Field(default_factory=list)
    series_theme: Optional[str] = None
    series_narrative: Optional[str] = None
    release_cadence: Optional[str] = None


class GrowthAdviceOutput(BaseModel):
    posting_schedule: Dict[str, Any] = Field(default_factory=dict)
    growth_tips: List[Any] = Field(default_factory=list)
    cross_promotion_ideas: List[Any] = Field(default_factory=list)
    audience_growth_projections: Dict[str, Any] = Field(default_factory=dict)
