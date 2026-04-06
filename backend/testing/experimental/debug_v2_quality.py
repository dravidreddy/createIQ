"""
Persona Evaluation Debugger — Direct Agent Testing (Bypassing Graph)
Tests the V2 Viral prompts directly with live LLM calls.
"""
import asyncio
import os
import logging
from app.agents.sub_agents.trend_researcher import TrendResearcherAgent
from app.agents.sub_agents.idea_generator import IdeaGeneratorAgent
from app.agents.sub_agents.hook_creator import HookCreatorAgent
from app.agents.sub_agents.script_drafter import ScriptDrafterAgent
from app.config import get_settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Configure logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_persona_tech():
    settings = get_settings()
    
    # 1. Initialize Beanie (required for memory operations inside agents)
    logger.info("Initializing DB context...")
    client = AsyncIOMotorClient(settings.mongodb_url)
    from app.models.user import User
    from app.models.user_preferences import UserPreferencesModel
    from app.models.project import Project
    from app.models.memory_entry import MemoryEntry
    from app.models.pipeline_checkpoint import PipelineCheckpoint
    from app.models.content_version import ContentVersion
    from app.models.job_metrics import JobMetrics
    
    await init_beanie(
        database=client[settings.mongodb_db_name],
        document_models=[User, UserPreferencesModel, Project, MemoryEntry, PipelineCheckpoint, ContentVersion, JobMetrics],
    )

    context = {
        "user_id": "eval_user_001",
        "project_id": "tech_eval_debug",
        "topic": "The $1,000 AI Mistake",
        "niche": "Technology / AI Review",
        "platforms": ["YouTube"],
        "target_audience": "Tech enthusiasts and creators"
    }
    
    user_prefs = {
        "writing_style": "High Energy",
        "tone": "Enthusiastic and Bold",
        "engagement_style": "Aggressive Pattern Interrupts"
    }

    print("\n" + "="*50)
    print("STAGE 1: TREND RESEARCH (V2 VIRAL)")
    print("="*50)
    researcher = TrendResearcherAgent(user_context=context)
    research_results = await researcher.execute({
        **context,
        "user_preferences": user_prefs
    })
    
    res_list = research_results.get("research_results", [])
    print(f"Found {len(res_list)} trending narratives.")
    for r in res_list[:3]:
        print(f"- {r.get('topic')} (Score: {r.get('relevance_score')})")

    if not res_list:
        print("FAILED: Trend synthesis returned nothing. Check raw logs above.")
        return

    # Add aggressive cooldown for rate limits (Groq quota guard)
    print("\n...Aggressive Cooling (30s Guard for V2 Viral Upgrade)...")
    await asyncio.sleep(30)

    print("\n" + "="*50)
    print("STAGE 2: IDEA GENERATION (V2 VIRAL)")
    print("="*50)
    generator = IdeaGeneratorAgent(user_context=context)
    idea_results = await generator.execute({
        "research_results": res_list,
        "user_preferences": user_prefs,
        "project_context": context
    })
    
    ideas = idea_results.get("ideas", [])
    print(f"Generated {len(ideas)} viral concepts.")
    if not ideas:
        print("FAILED: Idea generation returned nothing.")
        return
        
    selected_idea = ideas[0]
    print(f"SELECTED IDEA: {selected_idea.get('title')}")
    print(f"THUMBNAIL: {selected_idea.get('thumbnail_concept')}")
    print(f"UNIQUE ANGLE: {selected_idea.get('unique_angle')}")

    # Add cooldown for rate limits
    print("\n...Cooling down for 10s...")
    await asyncio.sleep(10)

    print("\n" + "="*50)
    print("STAGE 3: HOOK CREATION (PHASE 4 AUDIT)")
    print("="*50)
    hook_creator = HookCreatorAgent(user_context=context)
    hook_results = await hook_creator.execute({
        "idea_title": selected_idea.get("title"),
        "idea_description": selected_idea.get("description"),
        "unique_angle": selected_idea.get("unique_angle"),
        "user_preferences": user_prefs
    })
    
    hooks = hook_results.get("hooks", [])
    for i, h in enumerate(hooks[:3]):
        print(f"HOOK {i+1} [{h.get('framework')}]:")
        print(f"TEXT: {h.get('text')}")
        print(f"VISUAL: {h.get('on_screen_text')}\n")

    # Add aggressive cooldown for Script Stage (Large token count)
    print("\n...Aggressive Cooling (30s Guard for Script Stage)...")
    await asyncio.sleep(30)

    print("\n" + "="*50)
    print("STAGE 4: SCRIPT DRAFTING (HIGH ENERGY VERSION)")
    print("="*50)
    drafter = ScriptDrafterAgent(user_context=context)
    script_results = await drafter.execute({
        "selected_idea": selected_idea,
        "selected_hook": hooks[0] if hooks else {},
        "research_context": str(res_list),
        "user_preferences": user_prefs,
        "platforms": context["platforms"]
    })
    
    print("\n[FINAL V2 SCRIPT SNIPPET]\n")
    print(script_results.get("full_script", "FAILED TO GENERATE")[:1500] + "...")

if __name__ == "__main__":
    asyncio.run(debug_persona_tech())
