from typing import Optional
from pydantic import BaseModel, Field
from .bias import ArticleBias


class NewsArticle(BaseModel):
    title: str = Field(..., description="Article title")
    source: str = Field(..., description="News outlet / source name")
    url: str = Field(..., description="Article web URL")
    snippet: Optional[str] = Field(None, description="Search result snippet")
    date: Optional[str] = Field(None, description="Published date / time relative")
    cleaned_content: Optional[str] = Field(None, description="Cleaned text content extracted from article page")
    content_length: Optional[int] = Field(0, description="Length of cleaned content in characters")
    bias_info: Optional[ArticleBias] = Field(default_factory=ArticleBias, description="Biasing check results (TODO)")
