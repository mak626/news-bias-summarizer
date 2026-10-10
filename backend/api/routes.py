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
    query = request_body.effective_query
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty search query or text must be provided."
        )

    # 1. DuckDB Cache Check
    cached_data = database.get_analyzed_query(query)
    if cached_data:
        logger.info(f"DuckDB cache HIT for query: '{query}'")
        cached_data["cached"] = True
        story_id = cached_data.get("id") or cached_data.get("story_id") or "cjp-dipke-detained"
        cached_data["id"] = story_id
        cached_data["news_group_id"] = story_id
        cached_data["redirect_url"] = f"/story.html?id={story_id}"
        cached_data["web_url"] = f"http://localhost:8000/web/story.html?id={story_id}"
        
        # Optionally populate story detail if available
        story_obj = database.india_story(story_id)
        if story_obj:
            cached_data["story"] = story_detail(request, story_obj)

        return AnalysisResponse(**cached_data)

    logger.info(f"DuckDB cache MISS for query: '{query}'. Running analysis pipeline...")

    # 2. Live pipeline execution on cache miss
    articles = await process_news_search(search_query=query, target_count=request_body.num_articles)

    # AI Mode summarization and perspective analysis
    summary, analyzed_articles, viz_data = await analyze_and_group_news_bias(
        query=query,
        articles=articles
    )

    slug = re.sub(r"[^\w]+", "-", query.lower()).strip("-")[:40]
    story_id = slug or f"story-{uuid.uuid4().hex[:8]}"

    response = AnalysisResponse(
        status="success",
        query_used=query,
        articles_fetched_count=len(analyzed_articles),
        articles=analyzed_articles,
        summary=summary,
        visualization_data=viz_data,
        id=story_id,
        news_group_id=story_id,
        redirect_url=f"/story.html?id={story_id}",
        web_url=f"http://localhost:8000/web/story.html?id={story_id}",
        cached=False
    )

    # 3. Store in DuckDB for future instant cache hits & web views
    try:
        response_data = response.model_dump()
        database.save_analyzed_query(query, response_data, story_id=response.id)
        database.save_story_from_analysis(response_data, response.id, query)
        logger.info(f"Saved analysis and story '{response.id}' for query '{query}' to DuckDB")
    except Exception as e:
        logger.warning(f"Could not persist analysis to DuckDB: {e}")

    return response


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
