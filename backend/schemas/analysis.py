from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .article import NewsArticle
from .summary import SummaryResult


class AnalysisRequest(BaseModel):
    search_query: str = Field(..., description="Search string for Google News API via SerpAPI")
    url: Optional[str] = Field(None, description="Optional original URL of the news article")
    text: Optional[str] = Field(None, description="Optional parsed text of the current news article")
    num_articles: int = Field(5, ge=1, le=10, description="Number of news articles to fetch (default: 5)")


class AnalysisResponse(BaseModel):
    status: str = "success"
    query_used: str
    articles_fetched_count: int
    articles: List[NewsArticle]
    summary: Optional[SummaryResult] = Field(default_factory=SummaryResult, description="AI Summarization result")
    visualization_data: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "status": "TODO",
            "message": "AI biasing visualization will be generated here"
        },
        description="Visualization data structure"
    )
