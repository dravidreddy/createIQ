"""
Models Package — CreatorIQ MongoDB Document Models

All Beanie document models are registered via database.init_db().
Import individual models from their respective modules.
"""

# Core
from app.models.user import User
from app.models.profile import ProfileEmbed, UserProfile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.project import Project, ProjectStatus, Collaborator, CollaboratorRole

# Content (block-based versioning)
from app.models.content_block import ContentBlock, BlockType
from app.models.content_version import ContentVersion

# AI
from app.models.ai_generation import AIGeneration, TokenUsage
from app.models.strategy import StrategyPlan
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.memory_entry import MemoryEntry

# V3.3 Engine
from app.models.project_agent_state import ProjectAgentState
from app.models.budget_allocation import BudgetAllocation
from app.models.job_metrics import JobMetrics
from app.models.ranking_profile import RankingProfile
from app.models.variant_log import VariantLog

# Other
from app.models.template import ContentTemplate

# Legacy (deprecated)
from app.models.artifact import ProjectArtifact
from app.models.session import AgentSession
from app.models.project_version import ProjectVersion

# Database lifecycle
from app.models.database import init_db, close_db
