import logging
from typing import List, Dict, Any
import httpx
from config import settings
from constants import SERPAPI_SEARCH_URL, SERPAPI_ACCOUNT_URL
from schemas import SerpApiBalanceResponse

logger = logging.getLogger(__name__)



async def fetch_google_news(query: str, max_candidates: int = 15) -> List[Dict[str, Any]]:
    """
    Search string to SerpAPI Google News API.
    Fetches candidate news items (up to max_candidates) to allow retry/fallback if content parsing fails.
    """
    if not settings.SERP_API_KEY:
        logger.warning("SERP_API_KEY is not configured. Returning fallback mock news results.")
        return _get_mock_serp_results(query, max_candidates)

    params = {
        "engine": "google_news",
        "q": query,
        "api_key": settings.SERP_API_KEY,
        "gl": "us",
        "hl": "en"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(SERPAPI_SEARCH_URL, params=params)

            response.raise_for_status()
            data = response.json()

        news_results = data.get("news_results", [])
        candidates = []

        for item in news_results:
            if len(candidates) >= max_candidates:
                break

            source_raw = item.get("source", {})
            if isinstance(source_raw, dict):
                source_name = source_raw.get("name", "Unknown Source")
            else:
                source_name = str(source_raw) or "Unknown Source"

            article_info = {
                "title": item.get("title", "No Title"),
                "url": item.get("link", ""),
                "source": source_name,
                "snippet": item.get("snippet", ""),
                "date": item.get("date", "")
            }

            if article_info["url"]:
                candidates.append(article_info)

        if not candidates:
            logger.info("No news_results found in SerpAPI response. Using mock fallback.")
            return _get_mock_serp_results(query, max_candidates)

        return candidates

    except Exception as e:
        logger.error(f"Error fetching news from SerpAPI: {e}")
        return _get_mock_serp_results(query, max_candidates)


def _get_mock_serp_results(query: str, max_candidates: int = 15) -> List[Dict[str, Any]]:
    """Development fallback when SerpAPI key is missing or fails."""
    mock_sources = [
        ("Reuters", "https://www.reuters.com"),
        ("Associated Press", "https://apnews.com"),
        ("BBC News", "https://www.bbc.com/news"),
        ("The Guardian", "https://www.theguardian.com"),
        ("Wall Street Journal", "https://www.wsj.com"),
        ("Bloomberg", "https://www.bloomberg.com"),
        ("NPR", "https://www.npr.org"),
        ("CNBC", "https://www.cnbc.com"),
        ("Financial Times", "https://www.ft.com"),
        ("CBS News", "https://www.cbsnews.com")
    ]
    
    results = []
    for i in range(min(max_candidates, len(mock_sources))):
        name, base_url = mock_sources[i]
        results.append({
            "title": f"Coverage on '{query}' from {name}",
            "url": base_url,
            "source": name,
            "snippet": f"Detailed reporting and perspective regarding '{query}' from {name}.",
            "date": f"{i + 1} hour(s) ago"
        })
    return results


async def fetch_serpapi_balance() -> SerpApiBalanceResponse:
    """
    Queries SerpAPI Account API (https://serpapi.com/account.json).
    Free of charge, does not consume monthly search credits.
    """
    if not settings.SERP_API_KEY:
        raise ValueError("SERP_API_KEY is not configured in the environment.")

    params = {"api_key": settings.SERP_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(SERPAPI_ACCOUNT_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise ValueError(f"SerpAPI returned error: {data['error']}")

            return SerpApiBalanceResponse(
                account_email=data.get("account_email"),
                plan_name=data.get("plan_name"),
                total_searches_left=data.get("total_searches_left"),
                plan_searches_left=data.get("plan_searches_left"),
                searches_per_month=data.get("searches_per_month"),
                this_month_usage=data.get("this_month_usage"),
                this_hour_searches=data.get("this_hour_searches"),
                account_rate_limit_per_hour=data.get("account_rate_limit_per_hour"),
                plan_renewal_date=data.get("plan_renewal_date")
            )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching SerpAPI account balance: {e.response.status_code}")
        raise ValueError(f"SerpAPI account check failed with HTTP {e.response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching SerpAPI account balance: {e}")
        raise

