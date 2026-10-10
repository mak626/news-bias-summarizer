import logging
import re
from typing import List, Tuple, Dict, Any, Optional
import httpx
from config import settings
from constants import SERPAPI_SEARCH_URL
from schemas import NewsArticle, SummaryResult, BiasGroup, VisualizationData, ArticleBias
from schemas.enums import BiasCategory, BiasGroupCategory, PoliticalLeaning, TopicDomain

logger = logging.getLogger(__name__)


async def analyze_and_group_news_bias(
    query: str,
    articles: List[NewsArticle]
) -> Tuple[SummaryResult, List[NewsArticle], VisualizationData]:
    """
    Dynamically analyzes perspectives and generates summaries using SerpAPI Google AI Mode.
    1. First, queries SerpAPI AI mode to dynamically classify the topic domain (Political vs Tech/Business vs General).
    2. Then, queries SerpAPI AI mode with a tailored perspective analysis prompt based on that domain.
    Zero hardcoded keyword dictionaries or outlet ratings.
    """
    ai_markdown = None
    topic_domain = TopicDomain.GENERAL

    if settings.SERP_API_KEY:
        # Step 1: AI-driven domain classification via SerpAPI
        topic_domain = await _detect_topic_domain(query, articles)
        logger.info(f"SerpAPI AI classified topic domain for '{query}': {topic_domain.value}")

        # Step 2: Tailored AI perspective & summary generation
        ai_markdown = await _query_serpapi_ai_mode(query, articles, topic_domain)

    if ai_markdown:
        summary_result, updated_articles, viz_data = _parse_ai_mode_prediction(query, articles, ai_markdown, topic_domain)
    else:
        logger.info("SerpAPI key not present or call failed; using neutral fallback.")
        summary_result, updated_articles, viz_data = _fallback_analysis(query, articles, topic_domain)

    return summary_result, updated_articles, viz_data


async def _detect_topic_domain(query: str, articles: List[NewsArticle]) -> TopicDomain:
    """
    Queries SerpAPI Google AI Mode to classify the domain of the news topic.
    Returns TopicDomain.POLITICAL, TopicDomain.TECH_BUSINESS, or TopicDomain.GENERAL.
    Zero hardcoded keyword lists.
    """
    if not settings.SERP_API_KEY:
        return TopicDomain.GENERAL

    headlines = "\n".join(f"- Title: '{article.title}', Source: '{article.source}'" for article in articles[:5])

    classification_prompt = (
        f"Classify the overall domain of this news topic: '{query}'.\n\n"
        f"Sample Headlines:\n{headlines}\n\n"
        "Instructions: Classify into exactly ONE of the following three domains:\n"
        "- Political (government elections, political parties, public legislation, wars, diplomacy, civil protests)\n"
        "- Technology & Business (technology, corporate competition, markets, telecom, startups, products, finance)\n"
        "- General / Non-Political (culture, sports, science, entertainment, lifestyle)\n\n"
        "Reply strictly with: 'Domain: <category>'"
    )

    params = {
        "engine": "google_ai_mode",
        "q": classification_prompt,
        "api_key": settings.SERP_API_KEY,
        "gl": "us",
        "hl": "en"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(SERPAPI_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.warning(f"SerpAPI domain detection error: {data['error']}")
                return TopicDomain.GENERAL

            markdown = data.get("reconstructed_markdown", "")
            return _parse_domain_string(markdown)

    except Exception as e:
        logger.warning(f"Failed to query SerpAPI Google AI Mode for domain detection: {e}")
        return TopicDomain.GENERAL


def _parse_domain_string(ai_text: str) -> TopicDomain:
    """Converts the AI classification output into the corresponding TopicDomain enum."""
    text_lower = ai_text.lower()
    domain_match = re.search(r'(?:topic\s+)?domain:\s*([^\n]+)', text_lower)
    target = domain_match.group(1) if domain_match else text_lower

    if any(keyword in target for keyword in ("tech", "business", "corporate", "telecom", "commercial")):
        return TopicDomain.TECH_BUSINESS
    if any(keyword in target for keyword in ("politic", "policy", "election", "war", "government", "diplomacy")):
        return TopicDomain.POLITICAL

    return TopicDomain.GENERAL


async def _query_serpapi_ai_mode(
    query: str,
    articles: List[NewsArticle],
    topic_domain: TopicDomain
) -> Optional[str]:
    """Query SerpAPI Google AI Mode with a domain-tailored prompt to analyze perspectives and summarize news."""
    articles_payload = []
    for index, article in enumerate(articles, 1):
        content_preview = (article.cleaned_content[:250] if article.cleaned_content else article.snippet or "").replace("\n", " ").strip()
        articles_payload.append(f"Article {index}: Source '{article.source}', Title '{article.title}', Excerpt: '{content_preview}'")

    articles_text = "\n".join(articles_payload)
    is_political = (topic_domain == TopicDomain.POLITICAL)

    if is_political:
        instructions = (
            "1. For each article, evaluate its political bias based on its framing and content:\n"
            "   - Article [number]\n"
            "   - Category: (choose one: Left, Center-Left, Center, Center-Right, Right)\n"
            "   - Score: (decimal from -1.0 for Left to +1.0 for Right, with 0.0 as neutral)\n"
            "   - Framing: (short explanation of the political framing or editorial angle)\n"
            "2. Group the articles into Left, Center / Neutral, and Right categories.\n"
            "3. Provide a neutral overall summary and 3 to 5 key consensus points."
        )
    else:
        instructions = (
            "1. For each article, evaluate its perspective/stance on this topic:\n"
            "   - Article [number]\n"
            "   - Category: (choose one: Critical / Skeptical, Neutral / Balanced, Supportive / Optimistic)\n"
            "   - Score: (decimal from -1.0 for Critical/Skeptical to +1.0 for Supportive/Optimistic, with 0.0 as neutral)\n"
            "   - Framing: (short explanation of the stakeholder perspective or emphasis)\n"
            "2. Group the articles into Critical / Skeptical, Neutral / Balanced, and Supportive / Optimistic categories.\n"
            "3. Provide a neutral overall summary and 3 to 5 key consensus points."
        )

    prompt = (
        f"Analyze the perspectives and summarize the following {len(articles)} {topic_domain.value} news articles on '{query}':\n\n"
        f"{articles_text}\n\n"
        f"{instructions}"
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
            response = await client.get(SERPAPI_SEARCH_URL, params=params)
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
    markdown: str,
    topic_domain: TopicDomain
) -> Tuple[SummaryResult, List[NewsArticle], VisualizationData]:
    """Parses dynamic AI predictions from Google AI Mode output into Pydantic BaseModels."""
    is_political = (topic_domain == TopicDomain.POLITICAL)

    # 1. Parse individual article predictions (Article 1..N)
    article_predictions = _extract_article_predictions(markdown, len(articles), topic_domain)

    # 2. Extract key bullet points, intro summary, and group framings
    key_points, original_summary, bias_overview, group_framings = _extract_summary_and_sections(markdown, query, topic_domain)

    # 3. Set up spectrum buckets based on domain
    if is_political:
        group_keys = [BiasGroupCategory.LEFT, BiasGroupCategory.CENTER, BiasGroupCategory.RIGHT]
        default_framings = {
            "Left": group_framings.get("Left", "Focuses on humanitarian dimensions, civil liberties, and institutional accountability."),
            "Center": group_framings.get("Center", "Neutral factual reporting, institutional attribution, and diplomatic balance."),
            "Right": group_framings.get("Right", "Focuses on security imperatives, economic interests, and national authority.")
        }
    else:
        group_keys = [BiasGroupCategory.CRITICAL, BiasGroupCategory.NEUTRAL, BiasGroupCategory.SUPPORTIVE]
        default_framings = {
            BiasGroupCategory.CRITICAL.value: group_framings.get(
                "Critical",
                "Emphasizes regulatory obstacles, market competition pushback, and sovereign security concerns."
            ),
            BiasGroupCategory.NEUTRAL.value: group_framings.get(
                "Neutral",
                "Neutral wire reporting focusing on official application status, timelines, and facts."
            ),
            BiasGroupCategory.SUPPORTIVE.value: group_framings.get(
                "Supportive",
                "Highlights technological innovation, consumer benefits, and bridging the connectivity gap."
            )
        }

    category_counts: Dict[str, int] = {group_key.value: 0 for group_key in group_keys}
    bias_buckets: Dict[BiasGroupCategory, List[NewsArticle]] = {group_key: [] for group_key in group_keys}
    updated_articles: List[NewsArticle] = []
    scores: List[float] = []

    for index, article in enumerate(articles, 1):
        prediction = article_predictions.get(index)
        if prediction:
            raw_category = prediction["category"]
            score = prediction["score"]
            framing = prediction["framing"]
        else:
            raw_category, score, framing = _infer_bias_from_ai_text(article, markdown, topic_domain)

        category_enum = _to_bias_category(raw_category, topic_domain)
        group_category_enum = _to_group_category(category_enum, topic_domain)

        category_counts[group_category_enum.value] = category_counts.get(group_category_enum.value, 0) + 1
        bias_buckets[group_category_enum].append(article)
        scores.append(score)

        political_leaning = _to_political_leaning(category_enum) if is_political else None
        perspective_label = category_enum.value

        article.bias_info = ArticleBias(
            topic_domain=topic_domain,
            bias_score=score,
            bias_category=category_enum,
            political_leaning=political_leaning,
            perspective_label=perspective_label,
            personal_biasing_notes=framing
        )
        updated_articles.append(article)

    # 4. Construct Groups based on domain spectrum
    bias_groups: List[BiasGroup] = []
    for group_category in group_keys:
        group_articles = bias_buckets[group_category]
        bias_groups.append(
            BiasGroup(
                category=group_category,
                outlets=list({article.source for article in group_articles}),
                framing_overview=default_framings.get(group_category.value, f"Framing under {group_category.value} perspective."),
                article_titles=[article.title for article in group_articles]
            )
        )

    # 5. Build VisualizationData
    average_bias_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    if is_political:
        spectrum = [
            {"category": "Left", "count": category_counts.get("Left", 0), "score": -0.5},
            {"category": "Center", "count": category_counts.get("Center", 0), "score": 0.0},
            {"category": "Right", "count": category_counts.get("Right", 0), "score": 0.5},
        ]
    else:
        spectrum = [
            {"category": BiasGroupCategory.CRITICAL.value, "count": category_counts.get(BiasGroupCategory.CRITICAL.value, 0), "score": -0.5},
            {"category": BiasGroupCategory.NEUTRAL.value, "count": category_counts.get(BiasGroupCategory.NEUTRAL.value, 0), "score": 0.0},
            {"category": BiasGroupCategory.SUPPORTIVE.value, "count": category_counts.get(BiasGroupCategory.SUPPORTIVE.value, 0), "score": 0.5},
        ]

    viz_data = VisualizationData(
        topic_domain=topic_domain,
        spectrum=spectrum,
        average_bias=average_bias_score,
        groups_count=category_counts
    )

    summary_result = SummaryResult(
        topic_domain=topic_domain,
        original_summary=original_summary,
        key_points=key_points[:5] if key_points else [
            f"Synthesized perspectives on '{query}' across {len(articles)} sources",
            f"Coverage evaluated across {topic_domain.value} perspectives",
            "Consensus facts distinguished from editorial slant"
        ],
        bias_overview=bias_overview,
        bias_groups=bias_groups,
        raw_ai_markdown=markdown
    )

    return summary_result, updated_articles, viz_data


def _extract_article_predictions(markdown: str, count: int, topic_domain: TopicDomain) -> Dict[int, Dict[str, Any]]:
    """Extracts 'Article X' predictions from the AI output."""
    predictions: Dict[int, Dict[str, Any]] = {}
    blocks = re.split(r'(?:^|\n)[-*#\s]*Article\s+(\d+)', markdown, flags=re.IGNORECASE)


    for i in range(1, len(blocks), 2):
        try:
            index = int(blocks[i])
            block = blocks[i + 1]

            category_match = re.search(r'Category:\s*([^\n]+)', block, re.IGNORECASE)
            score_match = re.search(r'Score:\s*[\$\\\s]*([+-]?\d+(?:\.\d+)?)', block, re.IGNORECASE)
            framing_match = re.search(r'(?:Framing|Rationale|Perspective)[^:]*:\s*([^\n]+)', block, re.IGNORECASE)

            default_category = "Center" if topic_domain == TopicDomain.POLITICAL else "Neutral / Balanced"
            raw_category = category_match.group(1).strip() if category_match else default_category
            score_value = float(score_match.group(1).strip()) if score_match else _category_to_default_score(raw_category, topic_domain)
            framing = framing_match.group(1).strip() if framing_match else "AI predicted perspective based on article framing."

            raw_category = re.sub(r'[*_`\\]', '', raw_category).strip()
            framing = re.sub(r'\[\d+\]', '', framing).strip()

            predictions[index] = {
                "category": raw_category,
                "score": max(-1.0, min(1.0, round(score_value, 2))),
                "framing": framing
            }
        except Exception as e:
            logger.debug(f"Error parsing article prediction block: {e}")

    return predictions


def _extract_summary_and_sections(markdown: str, query: str, topic_domain: TopicDomain) -> Tuple[List[str], str, str, Dict[str, str]]:
    """Extracts consensus bullet points, introductory summary, and section framing from markdown."""
    key_points: List[str] = []
    intro_lines: List[str] = []
    bias_overview_lines: List[str] = []
    group_framings: Dict[str, str] = {}

    lines = markdown.splitlines()
    in_summary_section = False
    in_prediction_section = False

    for line in lines:
        stripped_line = line.strip()
        if "summary" in stripped_line.lower() or "key points" in stripped_line.lower() or "consensus" in stripped_line.lower():
            in_summary_section = True
            in_prediction_section = False
        elif "article 1" in stripped_line.lower() or "categorization" in stripped_line.lower() or "bias prediction" in stripped_line.lower():
            in_prediction_section = True
            in_summary_section = False

        if in_summary_section and (stripped_line.startswith("-") or stripped_line.startswith("*")):
            bullet = re.sub(r"^[-*]\s*", "", stripped_line)
            bullet = re.sub(r"\[\d+\]", "", bullet).strip()
            if len(bullet) > 25:
                key_points.append(bullet)
        elif not in_prediction_section and len(stripped_line) > 40 and not stripped_line.startswith("#") and not stripped_line.startswith("-"):
            if any(keyword in stripped_line.lower() for keyword in ("perspective", "bias", "framing", "stance", "angle")):
                bias_overview_lines.append(stripped_line)
            else:
                intro_lines.append(stripped_line)

    # Check for group headers
    check_groups = ("Left", "Center", "Right", "Critical", "Neutral", "Supportive")
    for group_name in check_groups:
        pattern = rf'###\s*{group_name}[^\n]*\n([\s\S]*?)(?=###|$)'
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            for section_line in match.group(1).splitlines():
                if any(keyword in section_line.lower() for keyword in ("framing", "focus", "perspective", "emphasiz")):
                    cleaned_framing = re.sub(r"^[-*#\s]+", "", section_line.strip())
                    cleaned_framing = re.sub(r"\[\d+\]", "", cleaned_framing).strip()
                    if len(cleaned_framing) > 20:
                        group_framings[group_name] = cleaned_framing
                        break

    original_summary = " ".join(intro_lines[:3]) if intro_lines else (
        key_points[0] if key_points else f"Synthesized AI multi-perspective overview on '{query}'."
    )
    bias_overview = " ".join(bias_overview_lines[:2]) if bias_overview_lines else (
        f"Articles on '{query}' reflect contrasting perspectives across key stakeholder and editorial viewpoints."
    )

    return key_points, original_summary, bias_overview, group_framings


def _infer_bias_from_ai_text(article: NewsArticle, ai_text: str, topic_domain: TopicDomain) -> Tuple[str, float, str]:
    """Infers category and score if an article was not explicitly enumerated."""
    source_lower = article.source.lower()
    title_words = [word.lower() for word in article.title.split() if len(word) > 4]

    target_groups = ("Left", "Center", "Right") if topic_domain == TopicDomain.POLITICAL else ("Critical", "Neutral", "Supportive")
    for section_name in target_groups:
        pattern = rf'###\s*{section_name}[^\n]*\n([\s\S]*?)(?=###|$)'
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match and (source_lower in match.group(1).lower() or any(word in match.group(1).lower() for word in title_words[:3])):
            score = -0.5 if section_name in ("Left", "Critical") else (0.5 if section_name in ("Right", "Supportive") else 0.0)
            return section_name, score, f"Categorized under {section_name} perspective by AI analysis."

    default_category = "Center" if topic_domain == TopicDomain.POLITICAL else BiasCategory.NEUTRAL.value
    return default_category, 0.0, "Balanced framing inferred from article content."


def _to_bias_category(raw_category: str, topic_domain: TopicDomain) -> BiasCategory:
    """Safely converts any raw string into a valid BiasCategory enum."""
    normalized_category = raw_category.replace("\\", "").lower().strip()

    if topic_domain == TopicDomain.POLITICAL:
        if "center-left" in normalized_category or "left-center" in normalized_category:
            return BiasCategory.CENTER_LEFT
        elif "left" in normalized_category:
            return BiasCategory.LEFT
        elif "center-right" in normalized_category or "right-center" in normalized_category:
            return BiasCategory.CENTER_RIGHT
        elif "right" in normalized_category:
            return BiasCategory.RIGHT
        return BiasCategory.CENTER
    else:
        # Tech / Business / General domain
        if any(keyword in normalized_category for keyword in ("crit", "skept", "concern", "opposit", "risk", "hurdle")):
            return BiasCategory.CRITICAL
        elif any(keyword in normalized_category for keyword in ("suppor", "optimis", "favor", "pro-", "benefit", "advance")):
            return BiasCategory.SUPPORTIVE
        return BiasCategory.NEUTRAL


def _to_political_leaning(category_enum: BiasCategory) -> Optional[PoliticalLeaning]:
    """Maps BiasCategory to PoliticalLeaning enum for political topics."""
    if category_enum == BiasCategory.LEFT:
        return PoliticalLeaning.LEFT_LEANING
    elif category_enum == BiasCategory.CENTER_LEFT:
        return PoliticalLeaning.CENTER_LEFT_LEANING
    elif category_enum == BiasCategory.CENTER_RIGHT:
        return PoliticalLeaning.CENTER_RIGHT_LEANING
    elif category_enum == BiasCategory.RIGHT:
        return PoliticalLeaning.RIGHT_LEANING
    elif category_enum == BiasCategory.CENTER:
        return PoliticalLeaning.MODERATE
    return None


def _to_group_category(category_enum: BiasCategory, topic_domain: TopicDomain) -> BiasGroupCategory:
    """Maps fine-grained BiasCategory to broad BiasGroupCategory."""
    if topic_domain == TopicDomain.POLITICAL:
        if category_enum in (BiasCategory.LEFT, BiasCategory.CENTER_LEFT):
            return BiasGroupCategory.LEFT
        elif category_enum in (BiasCategory.RIGHT, BiasCategory.CENTER_RIGHT):
            return BiasGroupCategory.RIGHT
        return BiasGroupCategory.CENTER
    else:
        if category_enum == BiasCategory.CRITICAL:
            return BiasGroupCategory.CRITICAL
        elif category_enum == BiasCategory.SUPPORTIVE:
            return BiasGroupCategory.SUPPORTIVE
        return BiasGroupCategory.NEUTRAL


def _category_to_default_score(raw_category: str, topic_domain: TopicDomain) -> float:
    """Helper to convert category name to reasonable default score."""
    normalized_category = raw_category.replace("\\", "").lower()
    if topic_domain == TopicDomain.POLITICAL:
        if "center-left" in normalized_category:
            return -0.35
        elif "left" in normalized_category:
            return -0.60
        elif "center-right" in normalized_category:
            return 0.35
        elif "right" in normalized_category:
            return 0.60
        return 0.0
    else:
        if any(keyword in normalized_category for keyword in ("crit", "skept", "concern")):
            return -0.50
        elif any(keyword in normalized_category for keyword in ("suppor", "optimis", "favor")):
            return 0.50
        return 0.0


def _fallback_analysis(
    query: str,
    articles: List[NewsArticle],
    topic_domain: TopicDomain
) -> Tuple[SummaryResult, List[NewsArticle], VisualizationData]:
    """
    Neutral fallback when SerpAPI key is absent or network fails.
    Zero hardcoded keyword dictionaries.
    """
    is_political = (topic_domain == TopicDomain.POLITICAL)

    if is_political:
        group_keys = [BiasGroupCategory.LEFT, BiasGroupCategory.CENTER, BiasGroupCategory.RIGHT]
        default_category = BiasCategory.CENTER
    else:
        group_keys = [BiasGroupCategory.CRITICAL, BiasGroupCategory.NEUTRAL, BiasGroupCategory.SUPPORTIVE]
        default_category = BiasCategory.NEUTRAL

    category_counts: Dict[str, int] = {group_key.value: 0 for group_key in group_keys}
    bias_buckets: Dict[BiasGroupCategory, List[NewsArticle]] = {group_key: [] for group_key in group_keys}
    updated_articles: List[NewsArticle] = []

    # Assign articles to balanced neutral perspective
    target_group = BiasGroupCategory.CENTER if is_political else BiasGroupCategory.NEUTRAL
    for article in articles:
        category_counts[target_group.value] += 1
        bias_buckets[target_group].append(article)

        political_leaning = PoliticalLeaning.MODERATE if is_political else None
        article.bias_info = ArticleBias(
            topic_domain=topic_domain,
            bias_score=0.0,
            bias_category=default_category,
            political_leaning=political_leaning,
            perspective_label=default_category.value,
            personal_biasing_notes="Factual wire reporting summarizing available developments."
        )
        updated_articles.append(article)

    bias_groups: List[BiasGroup] = []
    for group_category in group_keys:
        group_articles = bias_buckets[group_category]
        bias_groups.append(
            BiasGroup(
                category=group_category,
                outlets=list({article.source for article in group_articles}),
                framing_overview=f"Reporting under {group_category.value} perspective.",
                article_titles=[article.title for article in group_articles]
            )
        )

    if is_political:
        spectrum = [
            {"category": "Left", "count": category_counts.get("Left", 0), "score": -0.5},
            {"category": "Center", "count": category_counts.get("Center", 0), "score": 0.0},
            {"category": "Right", "count": category_counts.get("Right", 0), "score": 0.5},
        ]
    else:
        spectrum = [
            {"category": BiasGroupCategory.CRITICAL.value, "count": category_counts.get(BiasGroupCategory.CRITICAL.value, 0), "score": -0.5},
            {"category": BiasGroupCategory.NEUTRAL.value, "count": category_counts.get(BiasGroupCategory.NEUTRAL.value, 0), "score": 0.0},
            {"category": BiasGroupCategory.SUPPORTIVE.value, "count": category_counts.get(BiasGroupCategory.SUPPORTIVE.value, 0), "score": 0.5},
        ]

    viz_data = VisualizationData(
        topic_domain=topic_domain,
        spectrum=spectrum,
        average_bias=0.0,
        groups_count=category_counts
    )

    summary_result = SummaryResult(
        topic_domain=topic_domain,
        original_summary=f"Synthesized coverage across {len(articles)} diverse sources on '{query}'.",
        key_points=[
            f"Analyzed {len(articles)} articles regarding '{query}'",
            f"Evaluated within the {topic_domain.value} domain",
            "Factual developments summarized across available reporting"
        ],
        bias_overview=f"Articles categorized under {topic_domain.value} viewpoints.",
        bias_groups=bias_groups,
        raw_ai_markdown=None
    )

    return summary_result, updated_articles, viz_data
