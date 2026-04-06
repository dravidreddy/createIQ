"""
PromptManager — Modular prompt assembly and lightweight versioning.

Handles the construction of complex prompts by combining base templates, 
task-specific instructions, and niche/persona modifiers.
"""

import logging
from typing import Dict, Any, List, Optional
from app.utils.prompt_loader import load_prompt, get_prompt_metadata

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Advanced prompt management with version tracking and modular assembly.
    """

    def __init__(self):
        self.active_versions: Dict[str, str] = {} # agent_name -> version

    def set_version(self, agent_name: str, version: str) -> None:
        """Set the active version for a specific agent/task."""
        self.active_versions[agent_name] = version

    def get_version(self, agent_name: str) -> Optional[str]:
        """Get the current active version for an agent."""
        return self.active_versions.get(agent_name)

    def assemble_prompt(
        self, 
        base_agent: str, 
        task_modifier: Optional[str] = None,
        niche_modifier: Optional[str] = None,
        version: Optional[str] = None,
        **context: Any
    ) -> str:
        """
        Assemble a modular prompt: [Base] + [Task Specifics] + [Niche Modifiers].
        """
        effective_version = version or self.get_version(base_agent)
        
        # 1. Load Base Prompt
        base_content = load_prompt(base_agent, "system_prompt", effective_version, **context)
        
        parts = [base_content]
        
        # 2. Add Task Modifier (if exists)
        if task_modifier:
            try:
                task_content = load_prompt(task_modifier, "instruction", version or "v1", **context)
                parts.append("\n### TASK SPECIFIC INSTRUCTIONS\n" + task_content)
            except Exception as e:
                logger.warning(f"Failed to load task modifier {task_modifier}: {e}")

        # 3. Add Niche Modifier (if exists)
        if niche_modifier:
            try:
                niche_content = load_prompt(niche_modifier, "tone", version or "v1", **context)
                parts.append("\n### NICHE & TONE ADJUSTMENTS\n" + niche_content)
            except Exception as e:
                logger.warning(f"Failed to load niche modifier {niche_modifier}: {e}")

        return "\n".join(parts)

    def track_prompt_metadata(self, agent_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Return metadata for inclusion in PipelineState/Logs."""
        meta = get_prompt_metadata(agent_name)
        return {
            "agent": agent_name,
            "version": version or self.get_version(agent_name) or "latest",
            "available_versions": meta.get("versions", [])
        }
