"""
Niche Inference — Lightweight keyword-based niche classifier.

Infers content niche from topic text and user profile when not explicitly set.
Used by the pipeline to resolve niche before any agent runs.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Keyword → niche mappings (ordered by specificity)
_NICHE_KEYWORDS = {
    "fitness": [
        "gym", "workout", "exercise", "muscle", "hypertrophy", "weight loss",
        "fat loss", "bodybuilding", "strength", "cardio", "protein", "calories",
        "macros", "training", "squat", "deadlift", "bench press", "yoga",
        "running", "marathon", "crossfit", "HIIT", "abs", "gains",
        "bulking", "cutting", "supplement", "creatine", "whey",
    ],
    "tech": [
        "software", "hardware", "programming", "coding", "artificial intelligence",
        "machine learning", "startup", "iPhone", "Android", "laptop", "GPU",
        "processor", "algorithm", "API", "cloud computing", "SaaS", "cybersecurity",
        "blockchain", "web development", "gadget", "review tech",
        "developer", "computer", "chip", "silicon", "robotics",
    ],
    "finance": [
        "investing", "stock", "crypto", "bitcoin", "portfolio", "savings",
        "budgeting", "real estate", "mortgage", "taxes", "retirement",
        "401k", "index fund", "ETF", "dividend", "compound interest",
        "side hustle", "passive income", "credit score", "debt", "FIRE",
        "financial freedom", "money", "wealth", "trading", "forex",
    ],
    "education": [
        "learn", "study", "course", "tutorial", "explain", "how to",
        "university", "college", "school", "exam", "certification",
        "math", "science", "history", "language learning", "skill", "knowledge",
        "curriculum", "lecture", "professor", "research paper",
        "scholarship", "degree", "STEM", "educational",
    ],
    "entertainment": [
        "movie", "film", "TV show", "celebrity", "music", "album",
        "concert", "meme", "viral", "pop culture", "drama", "comedy",
        "Netflix", "streaming", "reaction", "review movie", "award",
        "Grammy", "Oscar", "Broadway", "animation", "K-pop", "idol",
    ],
    "gaming": [
        "game", "gaming", "esports", "PlayStation", "Xbox", "Nintendo",
        "Switch", "PC gaming", "Steam", "Twitch", "speedrun", "RPG",
        "FPS", "MOBA", "MMO", "Fortnite", "Minecraft", "Valorant",
        "League of Legends", "Elden Ring", "GTA", "walkthrough",
        "boss fight", "DLC", "patch notes", "controller",
    ],
    "lifestyle": [
        "routine", "morning routine", "productivity", "minimalism",
        "self care", "journal", "habit", "wellness", "mental health",
        "meditation", "mindfulness", "organization", "declutter",
        "aesthetic", "room tour", "apartment", "daily vlog",
        "day in the life", "work from home", "remote work",
    ],
    "travel": [
        "travel", "destination", "flight", "hotel", "hostel", "backpacking",
        "itinerary", "vacation", "trip", "airport", "passport", "visa",
        "beach", "mountain", "island", "Europe trip", "Southeast Asia",
        "road trip", "digital nomad", "hidden gem", "budget travel",
        "luxury travel", "cruise", "hiking", "adventure",
    ],
    "food": [
        "recipe", "cooking", "baking", "restaurant", "chef", "cuisine",
        "meal prep", "ingredients", "healthy eating", "vegan", "keto",
        "diet", "nutrition", "food review", "mukbang", "kitchen",
        "dinner", "breakfast", "lunch", "snack", "dessert",
        "grill", "BBQ", "seafood", "pasta", "spice",
    ],
    "beauty": [
        "skincare", "makeup", "beauty", "cosmetics", "foundation",
        "concealer", "mascara", "lipstick", "serum", "moisturizer",
        "SPF", "sunscreen", "acne", "anti-aging", "retinol",
        "routine skincare", "tutorial makeup", "swatch", "dupe",
        "haul beauty", "GRWM", "get ready with me", "nails",
        "hair", "hairstyle", "curly hair", "straight hair",
    ],
}

# Pre-compile regex patterns for word-boundary matching (avoids substring false positives)
_NICHE_PATTERNS = {}
for _niche, _keywords in _NICHE_KEYWORDS.items():
    _NICHE_PATTERNS[_niche] = [
        re.compile(r'\b' + re.escape(kw.lower()) + r'\b', re.IGNORECASE)
        for kw in _keywords
    ]


def infer_niche(
    topic: str,
    user_profile_niche: Optional[str] = None,
) -> str:
    """Infer content niche from topic text and optional user profile.

    Resolution order:
    1. If user profile has a valid content_niche → use it
    2. Word-boundary keyword matching against topic text → highest match wins
    3. Fallback to 'general'

    Args:
        topic: The content topic/description text
        user_profile_niche: Niche from user's profile (e.g. 'Fitness', 'Tech')

    Returns:
        Lowercase niche identifier (e.g. 'fitness', 'tech', 'general')
    """
    # 1. User profile niche (explicit, highest priority)
    if user_profile_niche:
        normalized = user_profile_niche.lower().strip()
        if normalized in _NICHE_KEYWORDS:
            return normalized
        # Handle enum values like "Fitness & Health" → "fitness"
        for niche_key in _NICHE_KEYWORDS:
            if niche_key in normalized:
                return niche_key

    # 2. Word-boundary keyword matching on topic
    if not topic:
        return "general"

    scores = {}

    for niche, patterns in _NICHE_PATTERNS.items():
        score = sum(1 for pat in patterns if pat.search(topic))
        if score > 0:
            scores[niche] = score

    if scores:
        best_niche = max(scores, key=scores.get)
        confidence = scores[best_niche]
        logger.info(
            "NAPOS: Inferred niche '%s' from topic (confidence: %d keyword matches)",
            best_niche, confidence
        )
        return best_niche

    # 3. Fallback
    logger.info("NAPOS: Could not infer niche from topic '%s', using 'general'", topic[:50])
    return "general"
