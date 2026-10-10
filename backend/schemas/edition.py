from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Alignment(str, Enum):
    opposition = "opposition"
    mixed = "mixed"
    ruling = "ruling"
    unclear = "unclear"


class Focus(str, Enum):
    rights = "rights"
    context = "context"
    official = "official"


class ImageAsset(BaseModel):
    kind: Literal["photo", "illustration"]
    url: str
    alt: str
    credit: str
    source_url: Optional[str] = None
    license: Optional[str] = None
    license_url: Optional[str] = None


class CoverageGroup(BaseModel):
    id: str
    label: str
    count: int


class SourceBadge(BaseModel):
    report_id: str
    publisher: str
    initials: str
    alignment: Alignment
    focus: Focus


class StoryCard(BaseModel):
    id: str
    dataset: Literal["reviewed_sample"] = "reviewed_sample"
    is_mock: bool = True
    category: str
    topics: List[str] = Field(default_factory=list)
    place: str
    date: str
    title: str
    description: str
    reading_time: str
    image: ImageAsset
    report_count: int
    sources: List[SourceBadge]
    alignment_distribution: List[CoverageGroup]
    focus_distribution: List[CoverageGroup]


class Report(BaseModel):
    id: str
    publisher: str
    initials: str
    date: str
    origin: str
    alignment: Alignment
    focus: Focus
    confidence: str
    title: str
    url: str
    access: str
    evidence: str
    reasoning: str = Field(default="Perspective assessment", alias="why")
    voices: str = Field(default="Source", alias="voice")
    scope: str
    host: Optional[str] = None
    language: Optional[str] = None
    source_role: Optional[str] = Field(default=None, alias="sourceRole")

    model_config = ConfigDict(populate_by_name=True)


class Claim(BaseModel):
    status: str
    text: str
    report_id: Optional[str] = None
    source_url: Optional[str] = None


class Perspective(BaseModel):
    title: str
    text: str
    report_id: Optional[str] = None
    source_url: Optional[str] = None


class Link(BaseModel):
    label: str
    url: str


class StoryDetail(StoryCard):
    summary: str
    takeaway: str
    claims: List[Claim] = Field(default_factory=list)
    perspectives: List[Perspective] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    reports: List[Report] = Field(default_factory=list)
    primary_document: Optional[Link] = None
    related_story_ids: List[str] = Field(default_factory=list)


class StoryList(BaseModel):
    items: List[StoryCard]
    total: int


class EditionResponse(BaseModel):
    dataset: Literal["reviewed_sample"] = "reviewed_sample"
    is_mock: bool = True
    checked: str
    through: str
    lead_story_id: str
    story_count: int
    categories: List[str]
    topics: List[str]
    alignment_groups: List[dict[str, str]]
    focus_groups: List[dict[str, str]]
    methodology: str


class EditionContent(BaseModel):
    edition: EditionResponse
    stories: List[StoryDetail]
