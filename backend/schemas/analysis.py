from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .article import NewsArticle
from .summary import SummaryResult
from .enums import ResponseStatus


class VisualizationData(BaseModel):
    spectrum: List[Dict[str, Any]] = Field(default_factory=list, description="Distribution across Left, Center, Right")
    average_bias: float = Field(0.0, description="Average bias score from -1.0 to 1.0")
    groups_count: Dict[str, int] = Field(default_factory=dict, description="Count of articles per political spectrum bucket")


class AnalysisRequest(BaseModel):
    search_query: str = Field(..., description="Search string for Google News API via SerpAPI")
    url: Optional[str] = Field(None, description="Optional original URL of the news article")
    text: Optional[str] = Field(None, description="Optional parsed text of the current news article")
    num_articles: int = Field(5, ge=1, le=10, description="Number of news articles to fetch (default: 5)")


class AnalysisResponse(BaseModel):
    status: ResponseStatus = Field(ResponseStatus.SUCCESS, description="Status of the response")
    query_used: str
    articles_fetched_count: int
    articles: List[NewsArticle]
    summary: SummaryResult
    visualization_data: VisualizationData
