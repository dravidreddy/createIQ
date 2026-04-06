"""
Output Guard — JSON validation and response repair.
"""

import json
import logging
from typing import Any, Dict, Optional, Type, List
from pydantic import BaseModel, ValidationError

from app.llm.base import LLMMessage, LLMResponse
from app.utils.json_parser import extract_json

logger = logging.getLogger(__name__)

class OutputGuard:
    """
    Validates and repairs LLM outputs, especially for non-deterministic OSS models.
    """

    def __init__(self, router: Any):
        self.router = router
        self.max_retries = 2

    async def validate_and_repair(
        self,
        response: LLMResponse,
        schema: Type[BaseModel],
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        Tiered validation and repair:
        Stage 1: Soft Fix (Regex/JSON cleanup)
        Stage 2: Self Repair (Same model retry)
        Stage 3: Formatting Repair (External model - Groq)
        """
        content = response.content
        trace_id = kwargs.get("trace_id", "unknown")
        
        # 1. Stage 1: Soft Fix (Direct Regex Extraction)
        try:
            raw_json = extract_json(content)
            validated = schema.model_validate(raw_json)
            response.content = validated.model_dump_json()
            return response
        except (ValueError, ValidationError) as e:
            logger.info(f"[{trace_id}] OutputGuard: Stage 1 (Soft Fix) failed. Moving to Stage 2.")

        # 2. Stage 2: Self Repair (Retry with same model)
        # Limit recursion for self-repair
        for attempt in range(self.max_retries):
            try:
                repair_messages = messages + [
                    LLMMessage(role="assistant", content=content),
                    LLMMessage(
                        role="user", 
                        content=f"Your previous response was not valid JSON or did not match the required schema. Error: {str(e)}. Please provide the corrected JSON only, with no preamble."
                    )
                ]
                
                # Use same model for semantic-preserving self-correction
                repair_response = await self.router.generate(
                    messages=repair_messages,
                    task_type="repair",
                    priority="HIGH",
                    model_override=response.model,
                    trace_id=trace_id
                )
                
                content = repair_response.content
                raw_json = extract_json(content)
                validated = schema.model_validate(raw_json)
                response.content = validated.model_dump_json()
                logger.info(f"[{trace_id}] OutputGuard: Stage 2 (Self Repair) succeeded on attempt {attempt+1}")
                return response
            except Exception as e2:
                logger.warning(f"[{trace_id}] OutputGuard: Stage 2 (Self Repair) attempt {attempt+1} failed: {e2}")
                e = e2 

        # 3. Stage 3: Formatting Repair (External - Groq)
        # Used as last resort for formatting issues only
        try:
            logger.info(f"[{trace_id}] OutputGuard: Moving to Stage 3 (External Repair via Groq)")
            repair_messages = [
                LLMMessage(role="system", content="You are a JSON formatting expert. Your task is to fix the JSON structure of the provided text WITHOUT changing any of its semantic meaning or content. Return ONLY valid JSON."),
                LLMMessage(role="user", content=f"Fix this JSON structure to match the schema but KEEP all original data content.\nSchema: {schema.model_json_schema()}\n\nText: {content}")
            ]
            
            repair_response = await self.router.generate(
                messages=repair_messages,
                task_type="repair",
                priority="HIGH",
                model_override="llama-3.3-70b-versatile", # High reliability for JSON structure
                trace_id=trace_id
            )
            
            raw_json = extract_json(repair_response.content)
            validated = schema.model_validate(raw_json)
            response.content = validated.model_dump_json()
            logger.info(f"[{trace_id}] OutputGuard: Stage 3 (External Repair) succeeded.")
            return response
        except Exception as e3:
            logger.error(f"[{trace_id}] OutputGuard: All repair stages failed. Original: {e} | Stage 3 Error: {e3}")
            raise e # Raise original error if repair fails completely

    @staticmethod
    def is_valid_json(text: str) -> bool:
        """Check if string is valid JSON."""
        try:
            json.loads(text)
            return True
        except ValueError:
            return False
