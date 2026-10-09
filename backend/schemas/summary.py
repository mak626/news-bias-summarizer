from typing import List
from pydantic import BaseModel, Field


class SummaryResult(BaseModel):
    # TODO: AI Summarization will populate this structure
    original_summary: str = Field("AI Summarization pending", description="Summary of original article")
    key_points: List[str] = Field(default_factory=list, description="Key bullet points")
    bias_overview: str = Field("AI Biasing comparison pending", description="Cross-outlet bias analysis")
