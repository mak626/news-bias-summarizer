from enum import Enum


class BiasCategory(str, Enum):
    """Fine-grained political bias category for news articles."""
    LEFT = "Left"
    CENTER_LEFT = "Center-Left"
    CENTER = "Center"
    CENTER_RIGHT = "Center-Right"
    RIGHT = "Right"
    UNANALYZED = "Unanalyzed"


class BiasGroupCategory(str, Enum):
    """Broad spectrum category for grouping articles."""
    LEFT = "Left"
    CENTER = "Center"
    RIGHT = "Right"


class PoliticalLeaning(str, Enum):
    """Descriptive editorial leaning."""
    LEFT_LEANING = "Left-leaning"
    CENTER_LEFT_LEANING = "Center-Left-leaning"
    MODERATE = "Moderate / Centrist"
    CENTER_RIGHT_LEANING = "Center-Right-leaning"
    RIGHT_LEANING = "Right-leaning"
