from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from .article import NewsArticle
from .summary import SummaryResult
from .enums import ResponseStatus, TopicDomain
from .edition import StoryDetail


class VisualizationData(BaseModel):
    topic_domain: TopicDomain = Field(TopicDomain.POLITICAL, description="Topic domain of the spectrum")
    spectrum: List[Dict[str, Any]] = Field(default_factory=list, description="Distribution across spectrum buckets")
    average_bias: float = Field(0.0, description="Average bias or stance score from -1.0 to 1.0")
    groups_count: Dict[str, int] = Field(default_factory=dict, description="Count of articles per spectrum bucket")


class AnalysisRequest(BaseModel):
    query: str = Field(..., description="Search query or article text to analyze")
    url: Optional[str] = Field(None, description="Optional original URL of the news article")
    num_articles: int = Field(5, ge=1, le=10, description="Number of news articles to fetch (default: 5)")

    @model_validator(mode="before")
    @classmethod
    def resolve_query(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("query"):
                fallback = data.get("search_query") or data.get("text")
                if fallback:
                    data["query"] = fallback
        return data

    @property
    def effective_query(self) -> str:
        return self.query.strip()

    @property
    def search_query(self) -> str:
        return self.query.strip()


class AnalysisResponse(BaseModel):
    status: ResponseStatus = Field(ResponseStatus.SUCCESS, description="Status of the response")
    query_used: str
    articles_fetched_count: int
    articles: List[NewsArticle]
    summary: SummaryResult
    visualization_data: VisualizationData
    id: Optional[str] = Field(None, description="Story or news-group ID for frontend routing")
    news_group_id: Optional[str] = Field(None, description="Alias for extension redirection")
    redirect_url: Optional[str] = Field(None, description="Relative URL to view the story in web app")
    web_url: Optional[str] = Field(None, description="Direct URL to view the story in web app")
    cached: bool = Field(False, description="True if served from DuckDB cache")
    story: Optional[StoryDetail] = Field(None, description="Full story detail formatted for web edition")
