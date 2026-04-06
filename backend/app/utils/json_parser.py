"""
Shared JSON Parser Utility

Single place for parsing LLM JSON responses. Handles:
- Raw JSON strings
- JSON wrapped in ```json``` code blocks
- JSON wrapped in generic ``` code blocks
- Regex extraction as final fallback

Eliminates the duplicated parsing code across all agents.
"""

import json
import re
import logging
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract a JSON object from LLM response text.

    Tries these strategies in order:
    1. Direct JSON parse
    2. Extract from ```json``` code block
    3. Extract from generic ``` code block
    4. Regex extraction of first {...} block

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If no valid JSON can be extracted
    """
    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: ```json``` code block
    if "```json" in text:
        try:
            content = text.split("```json", 1)[1].split("```", 1)[0].strip()
            return json.loads(content)
        except (json.JSONDecodeError, IndexError):
            pass

    # Strategy 3: Generic ``` code block
    if "```" in text:
        try:
            content = text.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(content)
        except (json.JSONDecodeError, IndexError):
            pass

    # Strategy 4: Regex extraction of JSON object (outermost braces)
    # This is more robust for models that add preamble or postamble
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        json_str = match.group(0).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Final attempt: try to fix common issues like escaped single quotes
            try:
                # Basic cleaning for common LLM issues
                fixed = json_str.replace("\\'", "'")
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"No valid JSON found in response. Text sample: {text[:200]}...")


def parse_llm_json(
    text: str,
    fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Safely parse LLM JSON response with fallback.

    Args:
        text: Raw LLM response text
        fallback: Default value if parsing fails

    Returns:
        Parsed JSON dict or fallback
    """
    try:
        return extract_json(text)
    except ValueError as e:
        logger.warning("JSON parse failed: %s", e)
        return fallback if fallback is not None else {"_parse_error": str(e), "_raw": text[:2000]}


def validate_llm_output(
    text: str,
    schema: Type[BaseModel],
    fallback: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Parse LLM JSON and validate against a Pydantic schema.

    Args:
        text: Raw LLM response text
        schema: Pydantic BaseModel class to validate against
        fallback: Default if parsing/validation fails

    Returns:
        Tuple of (validated_model_or_None, raw_dict, error_or_None)
    """
    raw_dict = parse_llm_json(text, fallback)

    if "_parse_error" in raw_dict:
        return None, raw_dict, raw_dict["_parse_error"]

    try:
        validated = schema.model_validate(raw_dict)
        return validated, raw_dict, None
    except ValidationError as e:
        logger.warning("Schema validation failed: %s", e)
        return None, raw_dict, str(e)
