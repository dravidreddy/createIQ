import os
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from pydantic import BaseModel, Field

class EvaluationScore(BaseModel):
    quality: float = Field(..., ge=0, le=1)
    engagement: float = Field(..., ge=0, le=1)
    platform_fit: float = Field(..., ge=0, le=1)
    instruction_adherence: float = Field(..., ge=0, le=1)
    creativity: float = Field(..., ge=0, le=1)
    clarity: float = Field(..., ge=0, le=1)
    hallucination_detected: bool
    redundancy_detected: bool
    final_pass: bool
    reasoning: str

class ResponseEvaluator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

    async def evaluate(self, query: str, response: str, expected_behavior: str) -> EvaluationScore:
        prompt = f"""
        You are a Senior AI Quality Engineer at CreatorIQ. 
        Your task is to evaluate the following AI agent response based on specific CreatorIQ metrics.

        ## CONTEXT
        - User Query: {query}
        - Expected Behavior/Constraints: {expected_behavior}
        - AI Response: {response}

        ## METRICS (Score 0.0 to 1.0)
        1. Content Quality: Overall depth, value, and accuracy.
        2. Engagement Potential: How "viral" or catchy the content is (hooks, pacing).
        3. Platform Fit: Does it match the style of YouTube/TikTok/LinkedIn (based on query/context)?
        4. Instruction Adherence: Did it follow all constraints and expected behaviors?
        5. Creativity: Originality and unique angles.
        6. Clarity: Ease of understanding and flow.

        ## DETECT
        - Hallucination: Is it making up facts not present in common knowledge or the context?
        - Redundancy: Is it repeating itself or using generic AI tropes excessively?

        ## OUTPUT FORMAT
        You MUST return a valid JSON object with the following structure:
        {{
            "quality": float,
            "engagement": float,
            "platform_fit": float,
            "instruction_adherence": float,
            "creativity": float,
            "clarity": float,
            "hallucination_detected": bool,
            "redundancy_detected": bool,
            "final_pass": bool,
            "reasoning": "string explanation"
        }}

        A "final_pass" should only be true if instruction_adherence > 0.8 and quality > 0.7.
        """

        try:
            res = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(res.text)
            return EvaluationScore(**data)
        except Exception as e:
            logging.error(f"Evaluation failed: {e}")
            return EvaluationScore(
                quality=0.0,
                engagement=0.0,
                platform_fit=0.0,
                instruction_adherence=0.0,
                creativity=0.0,
                clarity=0.0,
                hallucination_detected=False,
                redundancy_detected=False,
                final_pass=False,
                reasoning=f"Evaluation Error: {str(e)}"
            )
