"""
Cost Tracker — Universal cost calculation for Multi-LLM setup.
"""

import logging
from typing import Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CostCalculator:
    """
    Calculates cost based on model type and usage.
    """

    @staticmethod
    def calculate_cost_cents(model_id: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in cents for a given model and token usage.
        """
        # Normalize model_id to find prices in config
        model_id_lower = model_id.lower()
        
        # Simplified mapping logic for demo
        if "o1" in model_id_lower:
            in_rate = settings.cost_per_1k_input_premium
            out_rate = settings.cost_per_1k_output_premium
        elif "sonnet" in model_id_lower or "pro" in model_id_lower:
            in_rate = settings.cost_per_1k_input_standard
            out_rate = settings.cost_per_1k_output_standard
        else: # mini, flash, deepseek
            in_rate = settings.cost_per_1k_input_routing
            out_rate = settings.cost_per_1k_output_routing
            
        input_cost = (input_tokens / 1000.0) * in_rate
        output_cost = (output_tokens / 1000.0) * out_rate
        
        return input_cost + output_cost
