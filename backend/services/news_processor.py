import asyncio
import logging
from typing import List
from services.serp_service import fetch_google_news
from services.article_scraper import fetch_and_clean_article_content
from schemas import NewsArticle, ArticleBias

logger = logging.getLogger(__name__)


async def process_news_search(search_query: str, target_count: int = 5) -> List[NewsArticle]:
    """
    Pipeline:
    1. Search string to SerpAPI Google News API -> fetch candidates (e.g. up to 15)
    2. Attempt to fetch & clean content for candidate news items
    3. If parsing fails for an article, fetch/try the next news item until target_count (5) valid articles are collected
    4. TODO: Mark AI biasing as pending
    """
    # Fetch extra candidates so we have replacements if parsing fails
    max_candidates = max(target_count * 3, 15)
    candidates = await fetch_google_news(query=search_query, max_candidates=max_candidates)

    successfully_parsed: List[NewsArticle] = []

    # Process candidates in parallel batches to be fast while respecting failover
    batch_size = 5
    for i in range(0, len(candidates), batch_size):
        if len(successfully_parsed) >= target_count:
            break

        batch = candidates[i:i + batch_size]
        tasks = [fetch_and_clean_article_content(item["url"]) for item in batch]
        cleaned_results = await asyncio.gather(*tasks, return_exceptions=True)

        for item, content in zip(batch, cleaned_results):
            if len(successfully_parsed) >= target_count:
                break

            if isinstance(content, Exception) or not content:
                logger.warning(f"Parsing failed for news item '{item.get('title')}' at {item.get('url')}. Fetching next candidate.")
                continue  # Skip failed article and continue to next

            # Parsing succeeded!
            # TODO: AI Biasing check will run here in the future
            bias_info = ArticleBias(
                bias_score=None,
                bias_category="Unanalyzed",
                personal_biasing_notes="TODO: AI political and personal biasing checks pending"
            )

            article = NewsArticle(
                title=item.get("title", "No Title"),
                source=item.get("source", "Unknown Source"),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                date=item.get("date", ""),
                cleaned_content=content,
                content_length=len(content),
                bias_info=bias_info
            )
            successfully_parsed.append(article)

    logger.info(f"Successfully parsed {len(successfully_parsed)} articles out of candidate pool for query '{search_query}'.")
    return successfully_parsed[:target_count]
