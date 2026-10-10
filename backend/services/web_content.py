from __future__ import annotations

from collections import Counter
from typing import Any
from fastapi import Request
from schemas.edition import (
    Alignment,
    Focus,
    ImageAsset,
    CoverageGroup,
    SourceBadge,
    StoryCard,
    Report,
    Claim,
    Perspective,
    Link,
    StoryDetail,
    EditionResponse
)
from schemas.lab import (
    LensDefinition,
    LabArticle,
    LabStoryCard,
    LabStoryDetail,
    LabResponse
)
import database

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


def absolute(request: Request | None, relative: str) -> str:
    if request:
        return str(request.base_url).rstrip("/") + "/" + relative.lstrip("/")
    return "/" + relative.lstrip("/")


def distribution(story: dict[str, Any], field: str) -> list[CoverageGroup]:
    groups = ALIGNMENTS if field == "alignment" else FOCUSES
    values = Counter(report.get(field, "unclear") for report in story.get("reports", []))
    return [CoverageGroup(id=key, label=label, count=values[key]) for key, label in groups]


def india_image(request: Request | None, story: dict[str, Any]) -> ImageAsset:
    photo = story.get("photo")
    if photo:
        url = photo["url"]
        if not url.startswith(("http://", "https://")):
            url = absolute(request, f"static/images/{url.removeprefix('images/')}")
        return ImageAsset(
            kind="photo",
            url=url,
            alt=photo["alt"],
            credit=photo["credit"],
            source_url=photo.get("source"),
        )
    return ImageAsset(
        kind="illustration",
        url=absolute(request, f"static/illustrations/{story.get('art', 'economy')}.svg"),
        alt=f"Editorial illustration for {story.get('category', 'News')}",
        credit="nonpartisan.ink editorial illustration",
    )


def story_card(request: Request | None, story: dict[str, Any]) -> StoryCard:
    reports = story.get("reports", [])
    return StoryCard(
        id=story["id"],
        category=story.get("category", "General"),
        topics=story.get("topics", []),
        place=story.get("place", "India"),
        date=story.get("date", ""),
        title=story.get("title", ""),
        description=story.get("dek", story.get("description", "")),
        reading_time=story.get("read", story.get("reading_time", "3 min")),
        image=india_image(request, story),
        report_count=len(reports),
        sources=[
            SourceBadge(
                report_id=r["id"],
                publisher=r["publisher"],
                initials=r.get("initials", r["publisher"][:3].upper()),
                alignment=r.get("alignment", Alignment.unclear),
                focus=r.get("focus", Focus.context),
            )
            for r in reports
        ],
        alignment_distribution=distribution(story, "alignment"),
        focus_distribution=distribution(story, "focus"),
    )


def linked_item(item: dict[str, Any], model: type[Claim] | type[Perspective]):
    values = {"text": item["text"]}
    if model is Claim:
        values["status"] = item.get("status", "Reported")
    if model is Perspective:
        values["title"] = item.get("title", "Perspective")
    if item.get("source"):
        values["report_id"] = item["source"]
    if item.get("url"):
        values["source_url"] = item["url"]
    return model(**values)


def story_detail(request: Request | None, story: dict[str, Any]) -> StoryDetail:
    card = story_card(request, story).model_dump()
    all_ids = database.india_story_ids(exclude=story["id"])
    return StoryDetail(
        **card,
        summary=story.get("summary", ""),
        takeaway=story.get("takeaway", ""),
        claims=[linked_item(item, Claim) for item in story.get("claims", [])],
        perspectives=[linked_item(item, Perspective) for item in story.get("perspectives", [])],
        open_questions=story.get("gaps", story.get("open_questions", [])),
        reports=[Report(**report) for report in story.get("reports", [])],
        primary_document=Link(**story["primary"]) if story.get("primary") else None,
        related_story_ids=all_ids[:3],
    )


def build_edition_response() -> EditionResponse:
    stories = database.get_stories()
    lead_id = stories[0]["id"] if stories else "lead"
    return EditionResponse(
        checked=database.metadata("edition_checked"),
        through=database.metadata("edition_through"),
        lead_story_id=lead_id,
        story_count=len(stories),
        categories=sorted({story["category"] for story in stories}),
        topics=sorted({topic for story in stories for topic in story.get("topics", [])}),
        alignment_groups=[{"id": key, "label": label} for key, label in ALIGNMENTS],
        focus_groups=[{"id": key, "label": label} for key, label in FOCUSES],
        methodology="Assessments describe the framing of each reviewed article, not a publisher's party affiliation or factuality.",
    )


def lab_image(story: dict[str, Any]) -> ImageAsset:
    visual = story["visual"]
    return ImageAsset(
        kind="photo",
        url=visual["image"],
        alt=visual["alt"],
        credit=visual["credit"],
        source_url=visual["source"],
        license=visual.get("license"),
        license_url=visual.get("licenseUrl"),
    )


def lab_card(story: dict[str, Any]) -> LabStoryCard:
    return LabStoryCard(
        id=story["id"],
        category=story["category"],
        time_label=story["time"],
        title=story["title"],
        description=story["short"],
        summary=story["summary"],
        image=lab_image(story),
        article_count=len(story["ids"]),
    )


def lab_detail(story: dict[str, Any]) -> LabStoryDetail:
    dimensions = database.lab_dimensions()
    media = database.lab_media()
    articles = []
    for position, media_id in enumerate(story["ids"]):
        publisher = media[media_id]
        classifications = {
            dimension["id"]: dimension["labels"][publisher[dimension["id"]]]
            for dimension in dimensions
        }
        included = [
            context
            for index, context in enumerate(story["contexts"])
            if 2 - publisher["gaps"] >= index
        ]
        articles.append(
            LabArticle(
                id=f"{story['id']}-{media_id}",
                publisher=publisher["name"],
                initials=publisher["abbr"],
                language=publisher["lang"],
                owner=publisher["owner"],
                headline=story["headlines"][position],
                excerpt=story["quotes"][position],
                classifications=classifications,
                contexts_included=included,
            )
        )
    distributions = {}
    for dimension in dimensions:
        counts = Counter(article.classifications[dimension["id"]] for article in articles)
        distributions[dimension["id"]] = [
            CoverageGroup(id=str(index), label=label, count=counts[label])
            for index, label in enumerate(dimension["labels"])
        ]
    return LabStoryDetail(
        **lab_card(story).model_dump(),
        topic=story["topic"],
        contexts=story["contexts"],
        commonly_reported=story["common"],
        disputed=story["disputed"],
        less_widely_covered=story["unique"],
        articles=articles,
        distributions=distributions,
    )


def build_lab_response() -> LabResponse:
    stories = database.lab_stories()
    dimensions = database.lab_dimensions()
    return LabResponse(
        notice="Stories, publishers, excerpts, and assessments in the lens lab are fictional demonstration content.",
        categories=sorted({story["category"] for story in stories}),
        lenses=[
            LensDefinition(
                **{
                    key: value
                    for key, value in lens.items()
                    if key in {"id", "name", "title", "labels", "description"}
                }
            )
            for lens in dimensions
        ],
        methodology="Each article receives one classification per lens. Counts apply only to the selected fictional sample.",
    )
