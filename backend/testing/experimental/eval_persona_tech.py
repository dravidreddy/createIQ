import asyncio
import os
import json
import logging
from uuid import uuid4

# Import internal services to run evaluation without HTTP overhead
from app.config import get_settings
from app.pipeline.graph import get_graph
from app.models.user import User
from beanie import init_beanie, PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_tech_reviewer_eval():
    settings = get_settings()
    
    # 1. Initialize DB (needed for checkpointer and models)
    logger.info("Initializing database for evaluation...")
    client = AsyncIOMotorClient(settings.mongodb_url)
    from app.models.user import User
    from app.models.pipeline_checkpoint import PipelineCheckpoint
    from app.models.content_version import ContentVersion
    from app.models.job_metrics import JobMetrics
    from app.models.user_preferences import UserPreferencesModel
    from app.models.project import Project
    from app.models.memory_entry import MemoryEntry
    
    await init_beanie(
        database=client[settings.mongodb_db_name],
        document_models=[
            User, 
            PipelineCheckpoint, 
            ContentVersion, 
            JobMetrics,
            UserPreferencesModel,
            Project,
            MemoryEntry
        ],
    )

    # 2. Setup mock user
    user_id = str(PydanticObjectId())
    user = User(id=user_id, email="eval@creatoriq.ai", display_name="Eval User", hashed_password="...")
    
    # 3. Setup Graph
    graph = get_graph()
    thread_id = f"eval_tech:{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 4. Scenario: Tech Reviewer (YouTube Long-form)
    initial_state = {
        "user_id": user_id,
        "project_id": "tech_eval_001",
        "job_id": str(uuid4()),
        "user_preferences": {
            "writing_style": "high-energy",
            "tone": "enthusiastic",
            "vocabulary_level": "moderate"
        },
        "project_context": {
            "topic": "The $1,000 AI Mistake",
            "niche": "Technology / AI Tools",
            "platforms": ["YouTube"],
            "video_length": "10-15 minute",
            "target_audience": "Software Engineers and Tech Enthusiasts",
            "language": "English",
            "style_overrides": "Be brutal about common mistakes. No fluff."
        },
        "completed_stages": [],
        "current_stage": "",
        "errors": [],
        "total_cost_cents": 0.0,
        "total_tokens": {"input": 0, "output": 0},
        "_last_action": None,
        "should_terminate": False
    }

    logger.info("--- STARTING IDEA DISCOVERY ---")
    # We run the graph until the first interrupt (idea_selection)
    state_updates = []
    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        state_updates.append(event)
    
    final_state = await graph.aget_state(config)
    ideas = final_state.values.get("ideas", [])
    
    print("\n[GENERATE IDEAS]")
    print(json.dumps(ideas, indent=2))

    # 5. Simulate User selecting the best idea
    if not ideas:
        print("No ideas generated. Check API keys.")
        return

    selected_idea = ideas[0]
    logger.info(f"Selected Idea: {selected_idea['title']}")
    
    await graph.aupdate_state(config, {
        "user_action": "select",
        "selected_idea": selected_idea
    })

    logger.info("--- STARTING HOOK GENERATION ---")
    async for event in graph.astream(None, config, stream_mode="updates"):
        state_updates.append(event)
    
    final_state = await graph.aget_state(config)
    hooks = final_state.values.get("hooks", [])
    
    print("\n[GENERATE HOOKS]")
    print(json.dumps(hooks, indent=2))

    # 6. Simulate User selecting the best hook
    if not hooks:
        return

    selected_hook = hooks[0]
    await graph.aupdate_state(config, {
        "user_action": "select",
        "selected_hook": selected_hook
    })

    logger.info("--- STARTING SCRIPT WRITING ---")
    async for event in graph.astream(None, config, stream_mode="updates"):
        state_updates.append(event)
    
    final_state = await graph.aget_state(config)
    script = final_state.values.get("script", {})
    
    print("\n[GENERATE SCRIPT]")
    print(json.dumps(script, indent=2))

if __name__ == "__main__":
    asyncio.run(run_tech_reviewer_eval())
