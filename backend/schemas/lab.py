from __future__ import annotations

from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field
from .edition import ImageAsset, CoverageGroup


class LensDefinition(BaseModel):
    id: str
    name: str
    title: str
    labels: List[str]
    description: str


class LabArticle(BaseModel):
    id: str
    publisher: str
    initials: str
    language: str
    owner: str
    headline: str
    excerpt: str
    classifications: Dict[str, str]
    contexts_included: List[str]


class LabStoryCard(BaseModel):
    id: str
    dataset: Literal["fictional_demo"] = "fictional_demo"
    is_mock: bool = True
    category: str
    time_label: str
    title: str
    description: str
    summary: str
    image: ImageAsset
    article_count: int


class LabStoryDetail(LabStoryCard):
    topic: str
    contexts: List[str]
    commonly_reported: str
    disputed: str
    less_widely_covered: str
    articles: List[LabArticle]
    distributions: Dict[str, List[CoverageGroup]]


class LabStoryList(BaseModel):
    items: List[LabStoryCard]
    total: int


class LabResponse(BaseModel):
    dataset: Literal["fictional_demo"] = "fictional_demo"
    is_mock: bool = True
    notice: str
    categories: List[str]
    lenses: List[LensDefinition]
    methodology: str


class LabContent(BaseModel):
    lab: LabResponse
    stories: List[LabStoryDetail]
