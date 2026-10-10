from typing import Optional
from pydantic import BaseModel, Field


class ArticleBias(BaseModel):
    bias_score: Optional[float] = Field(0.0, ge=-1.0, le=1.0, description="AI calculated bias score: -1.0 (Left) to 1.0 (Right)")
    bias_category: str = Field("Center", description="Bias category: Left, Center-Left, Center, Center-Right, Right")
    political_leaning: Optional[str] = Field(None, description="Editorial leaning e.g. Left-leaning, Moderate, Conservative")
    personal_biasing_notes: Optional[str] = Field(None, description="Editorial framing notes")
