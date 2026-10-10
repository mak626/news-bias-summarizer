"""
Application-wide constants and default configurations.
No hardcoded outlet ratings, company names, or political keyword dictionaries.
"""

# Third-party Service Endpoints
SERPAPI_SEARCH_URL: str = "https://serpapi.com/search.json"
SERPAPI_ACCOUNT_URL: str = "https://serpapi.com/account.json"


# Default Spectrum Weights for Visualizations (-1.0 to 1.0)
DEFAULT_POLITICAL_SPECTRUM = [
    {"category": "Left", "score": -0.5},
    {"category": "Center", "score": 0.0},
    {"category": "Right", "score": 0.5},
]

DEFAULT_PERSPECTIVE_SPECTRUM = [
    {"category": "Critical / Skeptical", "score": -0.5},
    {"category": "Neutral / Balanced", "score": 0.0},
    {"category": "Supportive / Optimistic", "score": 0.5},
]
