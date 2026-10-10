from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from config import settings
import database
from schemas import (
    AnalysisRequest,
    AnalysisResponse,
    SerpApiBalanceResponse,
    StoryCard,
    StoryDetail,
    StoryList,
    EditionResponse,
    EditionContent,
    LabStoryCard,
    LabStoryDetail,
    LabStoryList,
    LabResponse,
    LabContent,
)
from services import (
    process_news_search,
    analyze_and_group_news_bias,
    fetch_serpapi_balance,
    compress_text_to_search_query,
)
from services.web_content import (
    story_card,
    story_detail,
    build_edition_response,
    lab_card,
    lab_detail,
    build_lab_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()



# -------------------------------------------------------------------------
# Core Analysis Endpoint (with DuckDB Caching & Redirection)
# -------------------------------------------------------------------------

@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Analyze news bias or retrieve cached result"
)
async def analyze_news_bias(request_body: AnalysisRequest, request: Request):
    """
    Search string / parsed article flow:
    1. If the query/topic is found in DuckDB, return the cached result immediately
       with the redirection URL to the web folder ('/story.html?id=...').
    2. If not found in DuckDB, run the live pipeline (SerpAPI Google News search +
       resilient scraper + SerpAPI Google AI Mode perspective analyzer), store the
       resulting story and analysis in DuckDB, and return it with the redirection URL.
    """
    raw_query = request_body.effective_query
    if not raw_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty search query or text must be provided."
        )

    # Convert/compress raw text (e.g. from article extraction) into clean search query via SerpAPI AI Mode
    search_query = await compress_text_to_search_query(raw_query) or raw_query

    # 1. DuckDB Cache Check (checking both search_query and raw_query)
    cached_data = database.get_analyzed_query(search_query) or database.get_analyzed_query(raw_query)
    if cached_data:
        logger.info(f"DuckDB cache HIT for query: '{search_query}'")
        story_id = cached_data.get("id") or cached_data.get("story_id") or "cjp-dipke-detained"
        return AnalysisResponse(
            status="success",
            id=story_id,
            news_group_id=story_id,
            redirect_url=f"/story.html?id={story_id}",
            web_url=f"http://localhost:8000/web/story.html?id={story_id}",
            cached=True,
        )

    logger.info(f"DuckDB cache MISS for query: '{search_query}'. Running analysis pipeline...")

    # 2. Live pipeline execution on cache miss
    articles = await process_news_search(search_query=search_query, target_count=request_body.num_articles)

    # AI Mode summarization and perspective analysis
    summary, analyzed_articles, viz_data = await analyze_and_group_news_bias(
        query=search_query,
        articles=articles
    )

    slug = re.sub(r"[^\w]+", "-", search_query.lower()).strip("-")[:40]
    story_id = slug or f"story-{uuid.uuid4().hex[:8]}"

    # 3. Store full analysis and story in DuckDB for future instant cache hits & web views
    try:
        storage_data = {
            "status": "success",
            "id": story_id,
            "news_group_id": story_id,
            "redirect_url": f"/story.html?id={story_id}",
            "web_url": f"http://localhost:8000/web/story.html?id={story_id}",
            "cached": True,
            "query_used": search_query,
            "articles_fetched_count": len(analyzed_articles),
            "articles": [a.model_dump() if hasattr(a, "model_dump") else a for a in analyzed_articles],
            "summary": summary.model_dump() if hasattr(summary, "model_dump") else summary,
            "visualization_data": viz_data.model_dump() if hasattr(viz_data, "model_dump") else viz_data,
        }
        database.save_analyzed_query(search_query, storage_data, story_id=story_id)
        if raw_query.lower() != search_query.lower():
            database.save_analyzed_query(raw_query, storage_data, story_id=story_id)
        database.save_story_from_analysis(storage_data, story_id, search_query)
        logger.info(f"Saved analysis and story '{story_id}' for query '{search_query}' to DuckDB")
    except Exception as e:
        logger.warning(f"Could not persist analysis to DuckDB: {e}")

    # Return only the concise redirection response needed by the extension
    return AnalysisResponse(
        status="success",
        id=story_id,
        news_group_id=story_id,
        redirect_url=f"/story.html?id={story_id}",
        web_url=f"http://localhost:8000/web/story.html?id={story_id}",
        cached=False,
    )


# -------------------------------------------------------------------------
# Edition Endpoints (Merged from web-apis)
# -------------------------------------------------------------------------

@router.get(
    "/edition",
    response_model=EditionResponse,
    tags=["Edition"],
    summary="Get reviewed India edition metadata"
)
def get_edition():
    return build_edition_response()


@router.get(
    "/edition/content",
    response_model=EditionContent,
    tags=["Edition"],
    summary="Load the complete India edition and stories"
)
def get_edition_content(request: Request):
    return EditionContent(
        edition=build_edition_response(),
        stories=[story_detail(request, story) for story in database.get_stories()],
    )


@router.get(
    "/stories",
    response_model=StoryList,
    tags=["Stories"],
    summary="List India stories"
)
def list_stories(
    request: Request,
    category: str | None = Query(None, description="Exact category, such as Politics or Economy"),
    topic: str | None = Query(None, description="Topic ID, such as narendra-modi"),
    q: str | None = Query(None, description="Case-insensitive search across story and publisher text"),
):
    stories = database.get_stories(category=category, topic=topic, query=q)
    items = [story_card(request, story) for story in stories]
    return StoryList(items=items, total=len(items))


@router.get(
    "/stories/{story_id}",
    response_model=StoryDetail,
    tags=["Stories"],
    summary="Get one India story comparison"
)
def get_story(story_id: str, request: Request):
    story = database.india_story(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Story '{story_id}' was not found")
    return story_detail(request, story)


# -------------------------------------------------------------------------
# Lens Lab Endpoints (Merged from web-apis)
# -------------------------------------------------------------------------

@router.get(
    "/lab",
    response_model=LabResponse,
    tags=["Lens Lab"],
    summary="Get fictional lens lab metadata"
)
def get_lab():
    return build_lab_response()


@router.get(
    "/lab/content",
    response_model=LabContent,
    tags=["Lens Lab"],
    summary="Load the complete fictional lens lab and stories"
)
def get_lab_content():
    return LabContent(
        lab=build_lab_response(),
        stories=[lab_detail(story) for story in database.lab_stories()],
    )


@router.get(
    "/lab/stories",
    response_model=LabStoryList,
    tags=["Lens Lab"],
    summary="List lens lab stories"
)
def list_lab_stories(
    category: str | None = Query(None, description="Exact lab category"),
    q: str | None = Query(None, description="Search lab titles, descriptions, and summaries"),
):
    stories = database.lab_stories(category=category, query=q)
    items = [lab_card(story) for story in stories]
    return LabStoryList(items=items, total=len(items))


@router.get(
    "/lab/stories/{story_id}",
    response_model=LabStoryDetail,
    tags=["Lens Lab"],
    summary="Get one lens lab story"
)
def get_lab_story(story_id: str):
    story = database.lab_story(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Lab story '{story_id}' was not found")
    return lab_detail(story)


# -------------------------------------------------------------------------
# SerpAPI Utility
# -------------------------------------------------------------------------

@router.get(
    "/serpapi/balance",
    response_model=SerpApiBalanceResponse,
    tags=["SerpAPI"],
    summary="Check SerpAPI account search quota"
)
async def check_serpapi_balance():
    try:
        balance = await fetch_serpapi_balance()
        return balance
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error checking SerpAPI balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check SerpAPI balance: {str(e)}"
        )
