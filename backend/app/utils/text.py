"""
Text utilities for safe truncation and sanitization.
"""

def truncate_text(text: str, max_chars: int = 2000) -> str:
    """
    Semantic-aware truncation:
    1. Preserves Head (start) and Tail (end).
    2. Cuts Head at the nearest sentence boundary for readability.
    3. Merges with a clear [TRUNCATED] marker.
    """
    if not text or len(text) <= max_chars:
        return text
        
    # Standard allocation: 75% head, 15% tail, remainder for marker
    head_len = int(max_chars * 0.75)
    tail_len = int(max_chars * 0.15)
    
    head = text[:head_len]
    tail = text[-tail_len:]
    
    # Try to find a sentence boundary in the last 30% of the head
    # to avoid cutting mid-sentence.
    search_start = int(head_len * 0.7)
    boundary_idx = -1
    for char in [". ", ".\n", "? ", "!\n", "\n"]:
        idx = head.rfind(char, search_start)
        if idx > boundary_idx:
            boundary_idx = idx + (len(char) - 1)
            
    if boundary_idx != -1:
        head = head[:boundary_idx + 1]
        
    return f"{head.strip()}\n\n... [SAFE TRUNCATED BY SENTINEL] ...\n\n{tail.strip()}"
