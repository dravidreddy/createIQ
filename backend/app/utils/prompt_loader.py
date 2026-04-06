"""
YAML Prompt Template Loader

Loads agent prompts from external YAML files and renders them
with Jinja2 templates for dynamic context injection.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

import yaml
from jinja2 import BaseLoader
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Jinja2 sandboxed environment — prevents user input from executing template expressions
_jinja_env = SandboxedEnvironment(loader=BaseLoader())


@lru_cache(maxsize=64)
def _load_yaml(agent_name: str) -> Dict[str, Any]:
    """Load and cache a YAML prompt file."""
    path = PROMPTS_DIR / f"{agent_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(
    agent_name: str,
    prompt_key: str = "system_prompt",
    version: Optional[str] = None,
    **context: Any,
) -> str:
    """
    Load and render a prompt template.

    Args:
        agent_name: Name of the agent (matches YAML filename without extension)
        prompt_key: Key within the version dict (e.g., 'system_prompt', 'user_prompt')
        version: Prompt version. If None, prefers 'v2_viral' then falls back to 'v1'.
        **context: Template variables to inject
    """
    data = _load_yaml(agent_name)
    versions = data.get("versions", {})

    # Version selection logic: preferred v2_viral -> v1 -> first available
    if version is None:
        if "v2_viral" in versions:
            version = "v2_viral"
        elif "v1" in versions:
            version = "v1"
        else:
            version = list(versions.keys())[0] if versions else None

    if not version or version not in versions:
        available = list(versions.keys())
        raise KeyError(f"Version '{version}' not found for {agent_name}. Available: {available}")

    template_str = versions[version].get(prompt_key, "")
    if not template_str:
        raise KeyError(f"Key '{prompt_key}' not found in {agent_name}/{version}")

    template = _jinja_env.from_string(template_str)
    return template.render(**context)


def load_system_prompt(agent_name: str, version: Optional[str] = None, **context: Any) -> str:
    """Shortcut to load the system prompt for an agent."""
    return load_prompt(agent_name, "system_prompt", version, **context)


def load_user_prompt(agent_name: str, version: Optional[str] = None, **context: Any) -> str:
    """Shortcut to load the user prompt for an agent."""
    return load_prompt(agent_name, "user_prompt", version, **context)


def get_prompt_metadata(agent_name: str) -> Dict[str, Any]:
    """Get metadata for a prompt file (name, description, available versions)."""
    data = _load_yaml(agent_name)
    return {
        "name": data.get("name", agent_name),
        "description": data.get("description", ""),
        "versions": list(data.get("versions", {}).keys()),
    }


def list_available_prompts() -> list:
    """List all available prompt files."""
    return [p.stem for p in PROMPTS_DIR.glob("*.yaml")]


def clear_cache() -> None:
    """Clear the YAML cache (e.g., after prompt files are updated)."""
    _load_yaml.cache_clear()
