from typing import Optional
from pydantic import BaseModel, Field
from .enums import BiasCategory, PoliticalLeaning, TopicDomain


class ArticleBias(BaseModel):
    topic_domain: TopicDomain = Field(TopicDomain.POLITICAL, description="Topic domain classification (Political, Tech/Business, General)")
    bias_score: Optional[float] = Field(0.0, ge=-1.0, le=1.0, description="Score from -1.0 (Left/Critical) to 1.0 (Right/Supportive)")
    bias_category: BiasCategory = Field(BiasCategory.CENTER, description="Perspective or bias category")
    political_leaning: Optional[PoliticalLeaning] = Field(None, description="Editorial leaning (only for political stories)")
    perspective_label: Optional[str] = Field(None, description="Perspective framing label (e.g. Critical, Balanced, Supportive)")
    personal_biasing_notes: Optional[str] = Field(None, description="Editorial framing notes")

