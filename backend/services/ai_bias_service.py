import logging
import re
from typing import List, Tuple, Dict, Any, Optional
import httpx
from config import settings
from schemas import NewsArticle, SummaryResult, BiasGroup, VisualizationData, ArticleBias
from schemas.enums import BiasCategory, BiasGroupCategory, PoliticalLeaning

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"


async def analyze_and_group_news_bias(
    query: str,
    articles: List[NewsArticle]
) -> Tuple[SummaryResult, List[NewsArticle], VisualizationData]:
    """
    Dynamically predicts bias and generates summaries using SerpAPI Google AI Mode.
    No hardcoded outlet ratings: the AI analyzes the article text/titles and predicts
    bias categories, scores, and groupings.
    """
    ai_markdown = None
    if settings.SERP_API_KEY:
        ai_markdown = await _query_serpapi_ai_mode(query, articles)

    if ai_markdown:
        summary_result, updated_articles, viz_data = _parse_ai_mode_prediction(query, articles, ai_markdown)
    else:
        logger.info("SerpAPI key not present or call failed; using dynamic content heuristic.")
        summary_result, updated_articles, viz_data = _dynamic_text_heuristic(query, articles)

    return summary_result, updated_articles, viz_data


async def _query_serpapi_ai_mode(query: str, articles: List[NewsArticle]) -> Optional[str]:
    """Query SerpAPI Google AI Mode to predict bias and summarize news articles."""
    articles_payload = []
    for idx, art in enumerate(articles, 1):
        content_preview = (art.cleaned_content[:250] if art.cleaned_content else art.snippet or "").replace("\n", " ").strip()
        articles_payload.append(f"Article {idx}: Source '{art.source}', Title '{art.title}', Excerpt: '{content_preview}'")

    articles_text = "\n".join(articles_payload)

    prompt = (
        f"Analyze the political bias and summarize the following {len(articles)} news articles on '{query}':\n\n"
        f"{articles_text}\n\n"
        "Please provide:\n"
        "1. For each article, predict its political bias based on its framing and content:\n"
        "   - Article [number]\n"
        "   - Category: (choose one: Left, Center-Left, Center, Center-Right, Right)\n"
        "   - Score: (decimal from -1.0 for Left to +1.0 for Right, with 0.0 as neutral)\n"
        "   - Framing: (short explanation of the editorial perspective)\n"
        "2. Group the articles into Left, Center / Neutral, and Right categories.\n"
        "3. Provide a neutral overall summary and 3 to 5 key consensus points."
    )

    params = {
        "engine": "google_ai_mode",
        "q": prompt,
        "api_key": settings.SERP_API_KEY,
        "gl": "us",
        "hl": "en"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.warning(f"SerpAPI AI mode error: {data['error']}")
                return None

            markdown = data.get("reconstructed_markdown")
            if markdown and len(markdown.strip()) > 100:
                logger.info("Successfully received dynamic AI predictions from SerpAPI Google AI Mode.")
                return markdown

    except Exception as e:
        logger.warning(f"Failed to query SerpAPI Google AI Mode: {e}")

    return None


def _parse_ai_mode_prediction(
    query: str,
    articles: List[NewsArticle],
    markdown: str
) -> Tuple[SummaryResult, List[NewsArticle], VisualizationData]:
    """Parses dynamic AI predictions from Google AI Mode output into Pydantic BaseModels."""
    # 1. Parse individual article predictions (Article 1..N)
    article_predictions = _extract_article_predictions(markdown, len(articles))

    # 2. Extract key bullet points, intro summary, and group framings
    key_points, original_summary, bias_overview, group_framings = _extract_summary_and_sections(markdown, query)

    # 3. Apply predicted bias to each article
    updated_articles: List[NewsArticle] = []
    scores: List[float] = []
    category_counts = {"Left": 0, "Center": 0, "Right": 0}
    bias_buckets: Dict[BiasGroupCategory, List[NewsArticle]] = {
        BiasGroupCategory.LEFT: [],
        BiasGroupCategory.CENTER: [],
        BiasGroupCategory.RIGHT: []
    }

    for idx, art in enumerate(articles, 1):
        pred = article_predictions.get(idx)
        if pred:
            raw_cat = pred["category"]
            score = pred["score"]
            framing = pred["framing"]
        else:
            raw_cat, score, framing = _infer_bias_from_ai_text(art, markdown)

        cat_enum = _to_bias_category(raw_cat)
        group_enum = _to_group_category(cat_enum)
        category_counts[group_enum.value] = category_counts.get(group_enum.value, 0) + 1
        bias_buckets[group_enum].append(art)
        scores.append(score)

        art.bias_info = ArticleBias(
            bias_score=score,
            bias_category=cat_enum,
            political_leaning=_to_political_leaning(cat_enum),
            personal_biasing_notes=framing
        )
        updated_articles.append(art)

    # 4. Construct BiasGroups based purely on AI grouping
    bias_groups = [
        BiasGroup(
            category=BiasGroupCategory.LEFT,
            outlets=list({a.source for a in bias_buckets[BiasGroupCategory.LEFT]}),
            framing_overview=group_framings.get("Left", "Focuses on humanitarian dimensions, civil liberties, and systemic critiques."),
            article_titles=[a.title for a in bias_buckets[BiasGroupCategory.LEFT]]
        ),
        BiasGroup(
            category=BiasGroupCategory.CENTER,
            outlets=list({a.source for a in bias_buckets[BiasGroupCategory.CENTER]}),
            framing_overview=group_framings.get("Center", "Neutral factual reporting, institutional attribution, and diplomatic balance."),
            article_titles=[a.title for a in bias_buckets[BiasGroupCategory.CENTER]]
        ),
        BiasGroup(
            category=BiasGroupCategory.RIGHT,
            outlets=list({a.source for a in bias_buckets[BiasGroupCategory.RIGHT]}),
            framing_overview=group_framings.get("Right", "Focuses on security imperatives, economic interests, and national authority."),
            article_titles=[a.title for a in bias_buckets[BiasGroupCategory.RIGHT]]
        )
    ]

    # 5. Build VisualizationData
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    viz_data = VisualizationData(
        spectrum=[
            {"category": "Left", "count": category_counts["Left"], "score": -0.5},
            {"category": "Center", "count": category_counts["Center"], "score": 0.0},
            {"category": "Right", "count": category_counts["Right"], "score": 0.5},
        ],
        average_bias=avg_score,
        groups_count=category_counts
    )

    summary_result = SummaryResult(
        original_summary=original_summary,
        key_points=key_points[:5] if key_points else [
            f"Synthesized dynamic perspectives on '{query}' across {len(articles)} sources",
            "Editorial framing evaluated and grouped across Left, Center, and Right spectrums",
            "Consensus facts identified and distinguished from partisan framing"
        ],
        bias_overview=bias_overview,
        bias_groups=bias_groups,
        raw_ai_markdown=markdown
    )

    return summary_result, updated_articles, viz_data


def _extract_article_predictions(markdown: str, count: int) -> Dict[int, Dict[str, Any]]:
    """Extracts 'Article X' predictions from the AI output."""
    predictions: Dict[int, Dict[str, Any]] = {}
    blocks = re.split(r'[-*#]+\s+Article\s+(\d+)', markdown, flags=re.IGNORECASE)

    for i in range(1, len(blocks), 2):
        try:
            idx = int(blocks[i])
            block = blocks[i + 1]

            cat_match = re.search(r'Category:\s*([^\n]+)', block, re.IGNORECASE)
            score_match = re.search(r'Score:\s*[\$\\\s]*([+-]?\d+(?:\.\d+)?)', block, re.IGNORECASE)
            framing_match = re.search(r'(?:Framing|Rationale)[^:]*:\s*([^\n]+)', block, re.IGNORECASE)

            cat = cat_match.group(1).strip() if cat_match else "Center"
            score_val = float(score_match.group(1).strip()) if score_match else _category_to_default_score(cat)
            framing = framing_match.group(1).strip() if framing_match else "AI predicted editorial stance based on article framing."

            cat = re.sub(r'[*_`]', '', cat).strip()
            framing = re.sub(r'\[\d+\]', '', framing).strip()

            predictions[idx] = {
                "category": cat,
                "score": max(-1.0, min(1.0, round(score_val, 2))),
                "framing": framing
            }
        except Exception as e:
            logger.debug(f"Error parsing article prediction block: {e}")

    return predictions


def _extract_summary_and_sections(markdown: str, query: str) -> Tuple[List[str], str, str, Dict[str, str]]:
    """Extracts consensus bullet points, introductory summary, and section framing from markdown."""
    key_points: List[str] = []
    intro_lines: List[str] = []
    bias_overview_lines: List[str] = []
    group_framings: Dict[str, str] = {}

    lines = markdown.splitlines()
    in_summary_section = False
    in_prediction_section = False

    for line in lines:
        stripped = line.strip()
        if "summary" in stripped.lower() or "key points" in stripped.lower() or "consensus" in stripped.lower():
            in_summary_section = True
            in_prediction_section = False
        elif "article 1" in stripped.lower() or "categorization" in stripped.lower() or "bias prediction" in stripped.lower():
            in_prediction_section = True
            in_summary_section = False

        if in_summary_section and (stripped.startswith("-") or stripped.startswith("*")):
            bullet = re.sub(r"^[-*]\s*", "", stripped)
            bullet = re.sub(r"\[\d+\]", "", bullet).strip()
            if len(bullet) > 25:
                key_points.append(bullet)
        elif not in_prediction_section and len(stripped) > 40 and not stripped.startswith("#") and not stripped.startswith("-"):
            if "media" in stripped.lower() or "bias" in stripped.lower() or "perspective" in stripped.lower():
                bias_overview_lines.append(stripped)
            else:
                intro_lines.append(stripped)

    # Check for group headers like ### Left, ### Center, ### Right
    for group_name in ("Left", "Center", "Right"):
        pattern = rf'###\s*{group_name}[^\n]*\n([\s\S]*?)(?=###|$)'
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            for l in match.group(1).splitlines():
                if "framing" in l.lower() or "focus" in l.lower() or "perspective" in l.lower():
                    clean_f = re.sub(r"^[-*#\s]+", "", l.strip())
                    clean_f = re.sub(r"\[\d+\]", "", clean_f).strip()
                    if len(clean_f) > 20:
                        group_framings[group_name] = clean_f
                        break

    original_summary = " ".join(intro_lines[:3]) if intro_lines else (
        key_points[0] if key_points else f"Synthesized AI multi-perspective overview on '{query}'."
    )
    bias_overview = " ".join(bias_overview_lines[:2]) if bias_overview_lines else (
        "Articles show distinct political framing across human-interest, institutional diplomacy, and national security."
    )

    return key_points, original_summary, bias_overview, group_framings


def _infer_bias_from_ai_text(article: NewsArticle, ai_text: str) -> Tuple[str, float, str]:
    """Infers category and score if an article was not enumerated in a numbered list."""
    source_lower = article.source.lower()
    title_words = [w.lower() for w in article.title.split() if len(w) > 4]

    for section_name in ("Left", "Center", "Right"):
        pattern = rf'###\s*{section_name}[^\n]*\n([\s\S]*?)(?=###|$)'
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match and (source_lower in match.group(1).lower() or any(w in match.group(1).lower() for w in title_words[:3])):
            score = -0.5 if section_name == "Left" else (0.5 if section_name == "Right" else 0.0)
            return section_name, score, f"Categorized under {section_name} perspective by AI analysis."

    return "Center", 0.0, "Balanced or non-partisan framing inferred from article content."


def _to_bias_category(cat_str: str) -> BiasCategory:
    """Safely convert any raw string into a BiasCategory enum."""
    cl = cat_str.lower()
    if "center-left" in cl or "left-center" in cl:
        return BiasCategory.CENTER_LEFT
    elif "left" in cl:
        return BiasCategory.LEFT
    elif "center-right" in cl or "right-center" in cl:
        return BiasCategory.CENTER_RIGHT
    elif "right" in cl:
        return BiasCategory.RIGHT
    return BiasCategory.CENTER


def _to_political_leaning(cat: BiasCategory) -> PoliticalLeaning:
    """Map BiasCategory to PoliticalLeaning enum."""
    if cat == BiasCategory.LEFT:
        return PoliticalLeaning.LEFT_LEANING
    elif cat == BiasCategory.CENTER_LEFT:
        return PoliticalLeaning.CENTER_LEFT_LEANING
    elif cat == BiasCategory.CENTER_RIGHT:
        return PoliticalLeaning.CENTER_RIGHT_LEANING
    elif cat == BiasCategory.RIGHT:
        return PoliticalLeaning.RIGHT_LEANING
    return PoliticalLeaning.MODERATE


def _to_group_category(cat: BiasCategory) -> BiasGroupCategory:
    """Map fine-grained BiasCategory to broad BiasGroupCategory."""
    if cat in (BiasCategory.LEFT, BiasCategory.CENTER_LEFT):
        return BiasGroupCategory.LEFT
    elif cat in (BiasCategory.RIGHT, BiasCategory.CENTER_RIGHT):
        return BiasGroupCategory.RIGHT
    return BiasGroupCategory.CENTER


def _category_to_default_score(cat: str) -> float:
    """Helper to convert category name to reasonable default score."""
    cl = cat.lower()
    if "center-left" in cl or "left-center" in cl:
        return -0.35
    elif "left" in cl:
        return -0.60
    elif "center-right" in cl or "right-center" in cl:
        return 0.35
    elif "right" in cl:
        return 0.60
    return 0.0


def _dynamic_text_heuristic(
    query: str,
    articles: List[NewsArticle]
) -> Tuple[SummaryResult, List[NewsArticle], VisualizationData]:
    """Dynamic fallback based on article text and titles when AI mode is unavailable."""
    scores = []
    category_counts = {"Left": 0, "Center": 0, "Right": 0}
    bias_buckets: Dict[BiasGroupCategory, List[NewsArticle]] = {
        BiasGroupCategory.LEFT: [],
        BiasGroupCategory.CENTER: [],
        BiasGroupCategory.RIGHT: []
    }
    updated_articles: List[NewsArticle] = []

    left_markers = {"humanitarian", "civilian", "human rights", "activist", "displaced", "ethnic cleansing", "blockade", "sanctions", "palestinian"}
    right_markers = {"security", "defense", "military", "counter-terrorism", "threat", "deterrence", "hamas", "iran", "allies", "strategic"}

    for art in articles:
        text = f"{art.title} {art.cleaned_content[:500] if art.cleaned_content else art.snippet or ''}".lower()
        left_hits = sum(1 for m in left_markers if m in text)
        right_hits = sum(1 for m in right_markers if m in text)

        diff = right_hits - left_hits
        if diff >= 2:
            cat_enum = BiasCategory.RIGHT
            score = 0.5
            framing = "Framing highlights strategic security, defense imperatives, and state alliances."
        elif diff <= -2:
            cat_enum = BiasCategory.LEFT
            score = -0.5
            framing = "Framing centers humanitarian impact, civilian tolls, and human rights scrutiny."
        else:
            cat_enum = BiasCategory.CENTER
            score = 0.0
            framing = "Factual reporting balancing multiple perspectives and institutional statements."

        group_enum = _to_group_category(cat_enum)
        category_counts[group_enum.value] += 1
        bias_buckets[group_enum].append(art)
        scores.append(score)

        art.bias_info = ArticleBias(
            bias_score=score,
            bias_category=cat_enum,
            political_leaning=_to_political_leaning(cat_enum),
            personal_biasing_notes=framing
        )
        updated_articles.append(art)

    bias_groups = [
        BiasGroup(
            category=BiasGroupCategory.LEFT,
            outlets=list({a.source for a in bias_buckets[BiasGroupCategory.LEFT]}),
            framing_overview="Emphasizes civilian impact, humanitarian conditions, and human rights.",
            article_titles=[a.title for a in bias_buckets[BiasGroupCategory.LEFT]]
        ),
        BiasGroup(
            category=BiasGroupCategory.CENTER,
            outlets=list({a.source for a in bias_buckets[BiasGroupCategory.CENTER]}),
            framing_overview="Focuses on verified wire facts, diplomatic developments, and multi-sided statements.",
            article_titles=[a.title for a in bias_buckets[BiasGroupCategory.CENTER]]
        ),
        BiasGroup(
            category=BiasGroupCategory.RIGHT,
            outlets=list({a.source for a in bias_buckets[BiasGroupCategory.RIGHT]}),
            framing_overview="Emphasizes national defense, strategic interests, and security threats.",
            article_titles=[a.title for a in bias_buckets[BiasGroupCategory.RIGHT]]
        )
    ]

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    viz_data = VisualizationData(
        spectrum=[
            {"category": "Left", "count": category_counts["Left"], "score": -0.5},
            {"category": "Center", "count": category_counts["Center"], "score": 0.0},
            {"category": "Right", "count": category_counts["Right"], "score": 0.5},
        ],
        average_bias=avg_score,
        groups_count=category_counts
    )

    summary_result = SummaryResult(
        original_summary=f"Synthesized coverage across {len(articles)} diverse sources on '{query}'.",
        key_points=[
            f"Analyzed {len(articles)} articles regarding '{query}'",
            "Outlets demonstrate distinct political framing based on text and content analysis",
            "Balance between humanitarian concerns, diplomatic negotiations, and security considerations"
        ],
        bias_overview="Content analysis reveals divergent framing across progressive, centrist, and conservative perspectives.",
        bias_groups=bias_groups,
        raw_ai_markdown=None
    )

    return summary_result, updated_articles, viz_data
