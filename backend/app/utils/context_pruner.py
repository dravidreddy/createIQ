"""
ContextPruner — Token budget enforcement for LLM requests.

Ensures that the total message payload (system + history + new input) 
stays within the target model's context limits.
"""

import logging
from typing import List, Dict, Any
from app.llm.base import LLMMessage

logger = logging.getLogger(__name__)

class ContextPruner:
    """
    Intelligent context pruning based on token budgets.
    """

    def __init__(self, char_per_token: float = 3.5):
        self.char_per_token = char_per_token

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens based on character count (conservative heuristic)."""
        if not text:
            return 0
        return int(len(text) / self.char_per_token)

    def prune_messages(
        self, 
        messages: List[LLMMessage], 
        max_tokens: int,
        reserve_output_tokens: int = 2048
    ) -> List[LLMMessage]:
        """
        Prune message history to stay within budget. 
        Always preserves the system prompt (first message) and the latest user message.
        """
        if not messages:
            return []

        # Target budget
        budget = max_tokens - reserve_output_tokens
        
        system_msg = None
        if messages[0].role == "system":
            system_msg = messages[0]
            history = messages[1:]
        else:
            history = messages

        if not history:
            return [system_msg] if system_msg else []

        # Always keep the latest message
        latest_msg = history[-1]
        mid_history = history[:-1]

        current_tokens = self.estimate_tokens(latest_msg.content)
        if system_msg:
            current_tokens += self.estimate_tokens(system_msg.content)

        if current_tokens > budget:
            logger.warning(f"Single message + system prompt exceeds budget ({current_tokens} > {budget}). Truncating latest message.")
            excess = current_tokens - budget
            chars_to_remove = int(excess * self.char_per_token)
            latest_msg.content = latest_msg.content[:-chars_to_remove]
            return [system_msg, latest_msg] if system_msg else [latest_msg]

        # Add history from most recent to oldest until budget is reached
        final_history = [latest_msg]
        for msg in reversed(mid_history):
            msg_tokens = self.estimate_tokens(msg.content)
            if current_tokens + msg_tokens <= budget:
                final_history.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        result = [system_msg] + final_history if system_msg else final_history
        logger.debug(f"ContextPruner: Original {len(messages)} msgs -> Pruned {len(result)} msgs (Est. tokens: {current_tokens})")
        return result

    def prune_context_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """Prune vector search results to stay within a specific token sub-budget."""
        total_tokens = 0
        preserved = []
        
        for chunk in chunks:
            content = chunk.get("content", "")
            tokens = self.estimate_tokens(content)
            if total_tokens + tokens <= max_tokens:
                preserved.append(chunk)
                total_tokens += tokens
            else:
                break
                
        return preserved
