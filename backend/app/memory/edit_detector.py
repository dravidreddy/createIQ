"""
EditDetectionEngine — Analyzes user edits to extract preference signals.

Uses difflib for structural diff analysis and an LLM (fast scoring model)
to classify the nature of changes. Outputs normalised preference signals
that feed into the UserMemoryStore's EMA-based learning.
"""

import difflib
import logging
from typing import Any, Dict, List

from app.llm.base import LLMMessage
from app.llm.router import get_llm_router
from app.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

_CLASSIFY_PROMPT = """You are an expert content analyst. Compare the original and edited versions below and classify the nature of changes.

ORIGINAL:
\"\"\"
{original}
\"\"\"

EDITED:
\"\"\"
{edited}
\"\"\"

DIFF SUMMARY:
{diff_summary}

Analyze the changes and return a JSON object:
{{
    "changes": [
        {{"type": "tone|structure|length|vocabulary|engagement", "detail": "brief description"}}
    ],
    "preference_signals": {{
        "tone_shift": 0.0,
        "length_preference": 0.0,
        "complexity_shift": 0.0,
        "engagement_shift": 0.0
    }}
}}

Signal ranges:
- tone_shift: -1 (more formal) to +1 (more casual)
- length_preference: -1 (shorter) to +1 (longer)
- complexity_shift: -1 (simpler) to +1 (more complex)
- engagement_shift: -1 (less interactive) to +1 (more interactive)

Return ONLY the JSON object."""


class EditDetectionEngine:
    """Analyzes user edits to extract preference signals."""

    def __init__(self):
        self._router = get_llm_router()

    def _compute_diff(self, original: str, edited: str) -> str:
        """Compute a human-readable diff summary using difflib."""
        original_lines = original.splitlines(keepends=True)
        edited_lines = edited.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            edited_lines,
            fromfile="original",
            tofile="edited",
            n=2,
        )
        diff_text = "".join(diff)

        if not diff_text:
            return "No differences detected."

        # Summarise stats
        additions = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))

        return f"Changes: +{additions} lines, -{deletions} lines\n\n{diff_text[:2000]}"

    def _compute_length_signal(self, original: str, edited: str) -> float:
        """Quick heuristic: length change → preference signal."""
        orig_len = len(original.split())
        edit_len = len(edited.split())
        if orig_len == 0:
            return 0.0
        ratio = (edit_len - orig_len) / orig_len
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, ratio * 2))

    async def analyze_edit(
        self,
        original: str,
        edited: str,
    ) -> Dict[str, Any]:
        """Analyze a user edit and extract preference signals.

        Returns:
            {
                "diff_summary": str,
                "changes": [{"type": "...", "detail": "..."}],
                "preference_signals": {
                    "tone_shift": float,
                    "length_preference": float,
                    "complexity_shift": float,
                    "engagement_shift": float,
                }
            }
        """
        # 1. Structural diff
        diff_summary = self._compute_diff(
            str(original)[:3000],
            str(edited)[:3000],
        )

        # 2. Quick heuristic signals
        length_signal = self._compute_length_signal(str(original), str(edited))

        # 3. LLM-based semantic classification
        try:
            prompt = _CLASSIFY_PROMPT.format(
                original=str(original)[:1500],
                edited=str(edited)[:1500],
                diff_summary=diff_summary[:1000],
            )
            messages = [LLMMessage(role="user", content=prompt)]
            response = await self._router.generate(
                messages,
                task_type="scoring",  # Use fast model (Groq)
                temperature=0.1,
                max_tokens=500,
            )

            result = parse_llm_json(response.content, fallback={
                "changes": [],
                "preference_signals": {},
            })

            # Merge heuristic signals
            signals = result.get("preference_signals", {})
            if "length_preference" not in signals or signals["length_preference"] == 0:
                signals["length_preference"] = length_signal

            return {
                "diff_summary": diff_summary,
                "changes": result.get("changes", []),
                "preference_signals": {
                    "tone_shift": float(signals.get("tone_shift", 0.0)),
                    "length_preference": float(signals.get("length_preference", length_signal)),
                    "complexity_shift": float(signals.get("complexity_shift", 0.0)),
                    "engagement_shift": float(signals.get("engagement_shift", 0.0)),
                },
            }

        except Exception as e:
            logger.warning("EditDetectionEngine: LLM classification failed — %s", e)
            return {
                "diff_summary": diff_summary,
                "changes": [],
                "preference_signals": {
                    "tone_shift": 0.0,
                    "length_preference": length_signal,
                    "complexity_shift": 0.0,
                    "engagement_shift": 0.0,
                },
            }
