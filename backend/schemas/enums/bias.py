from enum import Enum


class TopicDomain(str, Enum):
    """Broad domain classification of the news story."""
    POLITICAL = "Political"
    TECH_BUSINESS = "Technology & Business"
    GENERAL = "General / Non-Political"


class BiasCategory(str, Enum):
    """Fine-grained bias or stance category for news articles."""
    # Political Spectrum
    LEFT = "Left"
    CENTER_LEFT = "Center-Left"
    CENTER = "Center"
    CENTER_RIGHT = "Center-Right"
    RIGHT = "Right"

    # Tech / Business / Non-Political Stance
    CRITICAL = "Critical / Skeptical"
    NEUTRAL = "Neutral / Balanced"
    SUPPORTIVE = "Supportive / Optimistic"

    # Fallback
    UNANALYZED = "Unanalyzed"


class BiasGroupCategory(str, Enum):
    """Broad spectrum category for grouping articles."""
    # Political Spectrum
    LEFT = "Left"
    CENTER = "Center"
    RIGHT = "Right"
    
    # Tech / Business / Non-Political Stance
    CRITICAL = "Critical / Skeptical"
    NEUTRAL = "Neutral / Balanced"
    SUPPORTIVE = "Supportive / Optimistic"


class PoliticalLeaning(str, Enum):
    """Descriptive editorial leaning for political stories."""
    LEFT_LEANING = "Left-leaning"
    CENTER_LEFT_LEANING = "Center-Left-leaning"
    MODERATE = "Moderate / Centrist"
    CENTER_RIGHT_LEANING = "Center-Right-leaning"
    RIGHT_LEANING = "Right-leaning"

