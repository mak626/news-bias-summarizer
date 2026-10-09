from typing import Optional
from pydantic import BaseModel, Field


class ArticleBias(BaseModel):
    # TODO: AI Biasing check will populate these fields
    bias_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="AI calculated bias score: -1.0 (Left) to 1.0 (Right)")
    bias_category: Optional[str] = Field("Unanalyzed", description="Bias category: Left, Center-Left, Center, Center-Right, Right")
    personal_biasing_notes: Optional[str] = Field(None, description="Personal biasing check notes")
