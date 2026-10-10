from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional
import httpx
from config import settings
from constants import SERPAPI_SEARCH_URL

logger = logging.getLogger(__name__)

# In-memory LRU-style cache for compressed queries
_COMPRESSION_CACHE: dict[str, str] = {}


def _clean_query_string(raw: str) -> str:
    """Strip quotes, leading/trailing punctuation, and excessive whitespace."""
    cleaned = re.sub(r'[\r\n]+', ' ', raw)
    cleaned = re.sub(r'["\'`“”]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def is_already_concise_query(text: str) -> bool:
    """Returns True if text is already concise enough to serve as a search query."""
    words = text.split()
    return len(words) <= 20 and len(text) <= 140 and "\n" not in text.strip()


async def compress_text_to_search_query(text: str) -> str:
    """
    Compresses raw news article text or synopsis into a concise Google News search query
    using SerpAPI Google AI Mode.
    1. If already short (headline/concise query), cleans and returns directly.
    2. Checks in-memory cache.
    3. Calls SerpAPI Google AI Mode to synthesize a single-line search query under 20 words.
    4. Falls back to heuristic noun/sentence extraction under 20 words.
    """
    raw = text.strip()
    if not raw:
        return ""

    if is_already_concise_query(raw):
        return _clean_query_string(raw)

    cache_key = f"summary:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"
    if cache_key in _COMPRESSION_CACHE:
        return _COMPRESSION_CACHE[cache_key]

    system_prompt = (
        "You compress a news article into a single short search query. "
        "Describe the exact incident (who, what, where, when) in 1 line, under 20 words, "
        "using concrete nouns and plain keywords someone would type into Google Search to find related articles. "
        "No quotes, no punctuation tricks, no explanation, no extra text. Output only the query."
    )

    if settings.SERP_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(
                    SERPAPI_SEARCH_URL,
                    params={
                        "engine": "google_ai_mode",
                        "q": f"{system_prompt}\n\nArticle:\n{raw[:1500]}",
                        "api_key": settings.SERP_API_KEY,
                        "gl": "us",
                        "hl": "en",
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    ai_text = data.get("ai_overview", {}).get("text", "") or data.get("text", "")
                    cleaned = _clean_query_string(ai_text.split("\n")[0])
                    words = cleaned.split()
                    if words:
                        cleaned = " ".join(words[:18])
                        logger.info(f"SerpAPI Google AI Mode compressed article to search query: '{cleaned}'")
                        _COMPRESSION_CACHE[cache_key] = cleaned
                        return cleaned
        except Exception as e:
            logger.warning(f"SerpAPI Google AI Mode query compression failed: {e}; using heuristic fallback.")

    # Heuristic fallback: take the first sentence or first 15 words
    first_sentence = re.split(r'[.!?\n]', raw)[0].strip()
    words = first_sentence.split()
    fallback_query = " ".join(words[:16]) if words else raw[:80]
    fallback_query = _clean_query_string(fallback_query)
    _COMPRESSION_CACHE[cache_key] = fallback_query
    return fallback_query
