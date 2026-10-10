import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from config import settings
from schemas import AnalysisRequest, AnalysisResponse
from services import process_news_search, analyze_and_group_news_bias

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])

# Path to cached static mock response
MOCK_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_response.json"


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_news_bias(request: AnalysisRequest):
    """
    1. If MOCK_MODE is enabled, return cached static mock JSON immediately.
    2. Otherwise, fetch top 5 news articles using SerpAPI and clean page content.
    3. Use SerpAPI Google AI Mode API to summarize articles and group them by political bias (Left, Center, Right).
    4. Cache the resulting response into data/mock_response.json for subsequent mock mode usage.
    """
    query = request.search_query.strip() if request.search_query else ""
    if not query and request.text:
        query = request.text[:50].strip()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid search_query must be provided."
        )

    # 1. Return cached mock response when MOCK_MODE=true
    if settings.MOCK_MODE:
        logger.info(f"MOCK_MODE is enabled. Returning cached response from {MOCK_DATA_PATH}")
        if MOCK_DATA_PATH.exists():
            with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
                mock_data = json.load(f)
            return AnalysisResponse(**mock_data)
        else:
            logger.warning(f"Mock file not found at {MOCK_DATA_PATH}. Falling back to live pipeline.")

    # 2. Live pipeline: fetch news articles with parsing failover to guarantee target_count (5)
    articles = await process_news_search(search_query=query, target_count=request.num_articles)

    # 3. AI Summarization & Bias Grouping via SerpAPI Google AI Mode
    summary, analyzed_articles, viz_data = await analyze_and_group_news_bias(
        query=query,
        articles=articles
    )

    response = AnalysisResponse(
        status="success",
        query_used=query,
        articles_fetched_count=len(analyzed_articles),
        articles=analyzed_articles,
        summary=summary,
        visualization_data=viz_data
    )

    # 4. Cache response to mock_response.json for mock mode usage
    _cache_mock_response(response)

    return response


def _cache_mock_response(response: AnalysisResponse) -> None:
    """Save the latest live response to data/mock_response.json for mock mode usage."""
    try:
        MOCK_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MOCK_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info(f"Cached latest live analysis response to {MOCK_DATA_PATH}")
    except Exception as e:
        logger.warning(f"Failed to cache response to {MOCK_DATA_PATH}: {e}")
