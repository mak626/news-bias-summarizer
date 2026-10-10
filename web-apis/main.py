from __future__ import annotations

from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
import database

BASE_DIR = Path(__file__).resolve().parent
WEB_DIST = BASE_DIR.parent / "web" / "dist"


database.initialize()


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
    source_url: str | None = None
    license: str | None = None
    license_url: str | None = None


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
    topics: list[str] = []
    place: str
    date: str
    title: str
    description: str
    reading_time: str
    image: ImageAsset
    report_count: int
    sources: list[SourceBadge]
    alignment_distribution: list[CoverageGroup]
    focus_distribution: list[CoverageGroup]


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
    url: HttpUrl
    access: str
    evidence: str
    reasoning: str = Field(alias="why")
    voices: str = Field(alias="voice")
    scope: str
    host: str | None = None
    language: str | None = None
    source_role: str | None = Field(default=None, alias="sourceRole")

    model_config = ConfigDict(populate_by_name=True)


class Claim(BaseModel):
    status: str
    text: str
    report_id: str | None = None
    source_url: str | None = None


class Perspective(BaseModel):
    title: str
    text: str
    report_id: str | None = None
    source_url: str | None = None


class Link(BaseModel):
    label: str
    url: HttpUrl


class StoryDetail(StoryCard):
    summary: str
    takeaway: str
    claims: list[Claim]
    perspectives: list[Perspective]
    open_questions: list[str]
    reports: list[Report]
    primary_document: Link | None = None
    related_story_ids: list[str]


class StoryList(BaseModel):
    items: list[StoryCard]
    total: int


class EditionResponse(BaseModel):
    dataset: Literal["reviewed_sample"] = "reviewed_sample"
    is_mock: bool = True
    checked: str
    through: str
    lead_story_id: str
    story_count: int
    categories: list[str]
    topics: list[str]
    alignment_groups: list[dict[str, str]]
    focus_groups: list[dict[str, str]]
    methodology: str


class LensDefinition(BaseModel):
    id: str
    name: str
    title: str
    labels: list[str]
    description: str


class LabArticle(BaseModel):
    id: str
    publisher: str
    initials: str
    language: str
    owner: str
    headline: str
    excerpt: str
    classifications: dict[str, str]
    contexts_included: list[str]


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
    contexts: list[str]
    commonly_reported: str
    disputed: str
    less_widely_covered: str
    articles: list[LabArticle]
    distributions: dict[str, list[CoverageGroup]]


class LabStoryList(BaseModel):
    items: list[LabStoryCard]
    total: int


class LabResponse(BaseModel):
    dataset: Literal["fictional_demo"] = "fictional_demo"
    is_mock: bool = True
    notice: str
    categories: list[str]
    lenses: list[LensDefinition]
    methodology: str


ALIGNMENTS = [
    ("opposition", "Opposition / critical"),
    ("mixed", "Mixed / contextual"),
    ("ruling", "Ruling party / official"),
    ("unclear", "Unclear / insufficient evidence"),
]
FOCUSES = [
    ("rights", "Rights & scrutiny"),
    ("context", "Context & impacts"),
    ("official", "Official response"),
]


def absolute(request: Request, relative: str) -> str:
    return str(request.base_url).rstrip("/") + "/" + relative.lstrip("/")


def distribution(story: dict[str, Any], field: str) -> list[CoverageGroup]:
    groups = ALIGNMENTS if field == "alignment" else FOCUSES
    values = Counter(report[field] for report in story["reports"])
    return [CoverageGroup(id=key, label=label, count=values[key]) for key, label in groups]


def india_image(request: Request, story: dict[str, Any]) -> ImageAsset:
    photo = story.get("photo")
    if photo:
        url = photo["url"]
        if not url.startswith(("http://", "https://")):
            url = absolute(request, f"static/images/{url.removeprefix('images/')}")
        return ImageAsset(
            kind="photo", url=url, alt=photo["alt"], credit=photo["credit"],
            source_url=photo.get("source"),
        )
    return ImageAsset(
        kind="illustration",
        url=absolute(request, f"static/illustrations/{story.get('art', 'economy')}.svg"),
        alt=f"Editorial illustration for {story['category']}",
        credit="nonpartisan.ink editorial illustration",
    )


def story_card(request: Request, story: dict[str, Any]) -> StoryCard:
    reports = story["reports"]
    return StoryCard(
        id=story["id"], category=story["category"], topics=story.get("topics", []),
        place=story["place"], date=story["date"], title=story["title"],
        description=story["dek"], reading_time=story["read"], image=india_image(request, story),
        report_count=len(reports),
        sources=[SourceBadge(report_id=r["id"], publisher=r["publisher"], initials=r["initials"], alignment=r["alignment"], focus=r["focus"]) for r in reports],
        alignment_distribution=distribution(story, "alignment"),
        focus_distribution=distribution(story, "focus"),
    )


def linked_item(item: dict[str, Any], model: type[Claim] | type[Perspective]):
    values = {"text": item["text"]}
    if model is Claim:
        values["status"] = item["status"]
    if model is Perspective:
        values["title"] = item["title"]
    if item.get("source"):
        values["report_id"] = item["source"]
    if item.get("url"):
        values["source_url"] = item["url"]
    return model(**values)


def story_detail(request: Request, story: dict[str, Any]) -> StoryDetail:
    card = story_card(request, story).model_dump()
    all_ids = database.india_story_ids(exclude=story["id"])
    return StoryDetail(
        **card,
        summary=story["summary"], takeaway=story["takeaway"],
        claims=[linked_item(item, Claim) for item in story.get("claims", [])],
        perspectives=[linked_item(item, Perspective) for item in story.get("perspectives", [])],
        open_questions=story.get("gaps", []), reports=[Report(**report) for report in story["reports"]],
        primary_document=Link(**story["primary"]) if story.get("primary") else None,
        related_story_ids=all_ids[:3],
    )


def lab_image(story: dict[str, Any]) -> ImageAsset:
    visual = story["visual"]
    return ImageAsset(
        kind="photo", url=visual["image"], alt=visual["alt"], credit=visual["credit"],
        source_url=visual["source"], license=visual["license"], license_url=visual["licenseUrl"],
    )


def lab_card(story: dict[str, Any]) -> LabStoryCard:
    return LabStoryCard(
        id=story["id"], category=story["category"], time_label=story["time"],
        title=story["title"], description=story["short"], summary=story["summary"],
        image=lab_image(story), article_count=len(story["ids"]),
    )


def lab_detail(story: dict[str, Any]) -> LabStoryDetail:
    dimensions = database.lab_dimensions()
    media = database.lab_media()
    articles = []
    for position, media_id in enumerate(story["ids"]):
        publisher = media[media_id]
        classifications = {dimension["id"]: dimension["labels"][publisher[dimension["id"]]] for dimension in dimensions}
        included = [context for index, context in enumerate(story["contexts"]) if 2 - publisher["gaps"] >= index]
        articles.append(LabArticle(
            id=f"{story['id']}-{media_id}", publisher=publisher["name"], initials=publisher["abbr"],
            language=publisher["lang"], owner=publisher["owner"], headline=story["headlines"][position],
            excerpt=story["quotes"][position], classifications=classifications, contexts_included=included,
        ))
    distributions = {}
    for dimension in dimensions:
        counts = Counter(article.classifications[dimension["id"]] for article in articles)
        distributions[dimension["id"]] = [CoverageGroup(id=str(index), label=label, count=counts[label]) for index, label in enumerate(dimension["labels"])]
    return LabStoryDetail(
        **lab_card(story).model_dump(), topic=story["topic"], contexts=story["contexts"],
        commonly_reported=story["common"], disputed=story["disputed"],
        less_widely_covered=story["unique"], articles=articles, distributions=distributions,
    )


app = FastAPI(
    title="nonpartisan.ink Mock Content API",
    summary="Interactive mock API for the nonpartisan.ink India edition and fictional lens lab.",
    description="Use **Try it out** to browse the same static stories, comparisons, evidence, and image links used by the local web design.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Edition", "description": "Reviewed India edition metadata."},
        {"name": "Stories", "description": "India story cards and source-by-source comparisons."},
        {"name": "Lens Lab", "description": "Clearly labelled fictional comparison data."},
        {"name": "Health", "description": "Service status."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4173", "http://localhost:4173"],
    allow_methods=["GET"], allow_headers=["*"],
)
app.mount("/static/images", StaticFiles(directory=WEB_DIST / "images"), name="images")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", tags=["Health"], summary="Check service health")
def health():
    stories, lab_stories = database.counts()
    return {"status": "healthy", "database": "duckdb", "stories": stories, "lab_stories": lab_stories}


@app.get("/api/v1/edition", response_model=EditionResponse, tags=["Edition"])
def get_edition():
    stories = database.india_stories()
    return EditionResponse(
        checked=database.metadata("edition_checked"), through=database.metadata("edition_through"), lead_story_id=stories[0]["id"],
        story_count=len(stories), categories=sorted({story["category"] for story in stories}),
        topics=sorted({topic for story in stories for topic in story.get("topics", [])}),
        alignment_groups=[{"id": key, "label": label} for key, label in ALIGNMENTS],
        focus_groups=[{"id": key, "label": label} for key, label in FOCUSES],
        methodology="Assessments describe the framing of each reviewed article, not a publisher's party affiliation or factuality.",
    )


@app.get("/api/v1/stories", response_model=StoryList, tags=["Stories"], summary="List India stories")
def list_stories(
    request: Request,
    category: str | None = Query(None, description="Exact category, such as Politics or Economy"),
    topic: str | None = Query(None, description="Topic ID, such as narendra-modi"),
    q: str | None = Query(None, description="Case-insensitive search across story and publisher text"),
):
    stories = database.india_stories(category=category, topic=topic, query=q)
    items = [story_card(request, story) for story in stories]
    return StoryList(items=items, total=len(items))


@app.get("/api/v1/stories/{story_id}", response_model=StoryDetail, tags=["Stories"], summary="Get one India story comparison")
def get_story(story_id: str, request: Request):
    story = database.india_story(story_id)
    if not story:
        raise HTTPException(404, detail=f"Story '{story_id}' was not found")
    return story_detail(request, story)


@app.get("/api/v1/lab", response_model=LabResponse, tags=["Lens Lab"])
def get_lab():
    stories = database.lab_stories()
    dimensions = database.lab_dimensions()
    return LabResponse(
        notice="Stories, publishers, excerpts, and assessments in the lens lab are fictional demonstration content.",
        categories=sorted({story["category"] for story in stories}),
        lenses=[LensDefinition(**{key: value for key, value in lens.items() if key in {"id", "name", "title", "labels", "description"}}) for lens in dimensions],
        methodology="Each article receives one classification per lens. Counts apply only to the selected fictional sample.",
    )


@app.get("/api/v1/lab/stories", response_model=LabStoryList, tags=["Lens Lab"])
def list_lab_stories(
    category: str | None = Query(None, description="Exact lab category"),
    q: str | None = Query(None, description="Search lab titles, descriptions, and summaries"),
):
    stories = database.lab_stories(category=category, query=q)
    items = [lab_card(story) for story in stories]
    return LabStoryList(items=items, total=len(items))


@app.get("/api/v1/lab/stories/{story_id}", response_model=LabStoryDetail, tags=["Lens Lab"])
def get_lab_story(story_id: str):
    story = database.lab_story(story_id)
    if not story:
        raise HTTPException(404, detail=f"Lab story '{story_id}' was not found")
    return lab_detail(story)


ILLUSTRATIONS = {
    "economy": '<path d="M37 206h286M56 94l122-58 123 58zM64 113h233M70 190h222M84 114v74M129 114v74M176 114v74M222 114v74M271 114v74"/>',
    "markets": '<path d="M45 43v166h278M76 183l48-56 41 24 55-70 36 23 52-55M280 49h28v29"/>',
    "protest": '<rect x="34" y="27" width="105" height="65" rx="5"/><path d="M86 92v38M47 45h77M55 58h61M58 73h57"/><circle cx="57" cy="162" r="18"/><circle cx="117" cy="150" r="21"/><circle cx="185" cy="171" r="19"/>',
    "diplomacy": '<circle cx="180" cy="125" r="88"/><ellipse cx="180" cy="125" rx="42" ry="88"/><path d="M98 91h164M92 127h177M103 165h152"/>',
    "saudi": '<path d="M29 206h306M46 206v-50h35v50M106 206v-81h45v81M180 206V84h38v122M263 206V51l28-23 28 23v155"/>',
}


@app.get("/static/illustrations/{name}.svg", include_in_schema=False)
def illustration(name: str):
    drawing = ILLUSTRATIONS.get(name)
    if not drawing:
        raise HTTPException(404, detail="Illustration not found")
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 250"><rect width="360" height="250" fill="#181825"/><g fill="none" stroke="#b4befe" stroke-width="5">{drawing}</g></svg>'
    return Response(svg, media_type="image/svg+xml")
