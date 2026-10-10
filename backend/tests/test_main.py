import pytest
from fastapi.testclient import TestClient
from main import app
from services.article_scraper import clean_html_content
from services.news_processor import process_news_search
from unittest.mock import patch
from config import settings
import database

# Initialize test database
database.initialize()
client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "docs" in data
    assert "web_portal" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "duckdb"
    assert data["stories"] > 0
    assert data["lab_stories"] > 0


def test_html_cleaning():
    html = """
    <html>
        <head><title>News Title</title></head>
        <body>
            <header><nav><a href="/">Home</a></nav></header>
            <script>alert('ad script');</script>
            <article>
                <h1>Major Economic Milestone Reached</h1>
                <p>Economic indicators have demonstrated steady growth across key manufacturing and technology sectors.</p>
                <p>Analysts suggest policy adaptations contributed significantly to this quarter's unprecedented momentum.</p>
            </article>
            <footer><p>&copy; 2026 News Co. All rights reserved.</p></footer>
        </body>
    </html>
    """
    cleaned = clean_html_content(html)
    assert "Economic indicators have demonstrated" in cleaned
    assert "alert('ad script')" not in cleaned
    assert "All rights reserved" not in cleaned


@pytest.mark.asyncio
async def test_news_processor_failover_count():
    mock_candidates = [
        {"title": f"Article {i}", "url": f"https://example.com/{i}", "source": f"Source {i}", "snippet": "", "date": ""}
        for i in range(10)
    ]

    async def mock_fetch_content_and_img(url, timeout=8.0):
        if "0" in url or "2" in url:
            return None, None
        return f"This is valid cleaned content for {url} with sufficient length to pass the threshold requirement easily.", f"https://example.com/img-{url[-1]}.jpg"

    with patch("services.news_processor.fetch_google_news", return_value=mock_candidates):
        with patch("services.news_processor.fetch_article_content_and_image", side_effect=mock_fetch_content_and_img):
            results = await process_news_search("test query", target_count=5)
            assert len(results) == 5
            urls = [a.url for a in results]
            assert "https://example.com/0" not in urls
            assert "https://example.com/2" not in urls


def test_analyze_endpoint_cached_duckdb():
    """Verify DuckDB cache hit serves redirect_url and cached flag."""
    payload = {"query": "Jantar mantar protest"}
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cached"] is True
    assert "redirect_url" in data
    assert data["redirect_url"] == "/story.html?id=cjp-dipke-detained"
    assert data["id"] == "cjp-dipke-detained"


def test_analyze_endpoint_live_and_duckdb_storage():
    """Verify cache miss runs pipeline, saves into DuckDB, and subsequent call is a cache hit."""
    from schemas import NewsArticle, SummaryResult, VisualizationData, TopicDomain, ArticleBias, BiasCategory
    
    mock_articles = [
        NewsArticle(
            title=f"Sample Test Article {i}",
            source=f"Source {i}",
            url=f"https://example.com/test-{i}",
            snippet="snippet",
            date="10/10/2026",
            cleaned_content="Valid body text of the article for analysis verification.",
            content_length=60,
            bias_info=ArticleBias(
                topic_domain=TopicDomain.GENERAL,
                bias_category=BiasCategory.NEUTRAL,
                bias_score=0.0
            )
        )
        for i in range(5)
    ]
    mock_summary = SummaryResult(
        original_summary="Original neutral summary for test analysis.",
        bias_overview="Comparative analysis overview across perspectives.",
        topic_domain=TopicDomain.GENERAL,
        key_points=["Key point 1", "Key point 2"],
        bias_groups=[]
    )
    mock_viz = VisualizationData(
        topic_domain=TopicDomain.GENERAL,
        spectrum=[],
        average_bias=0.0
    )

    import uuid
    test_id = uuid.uuid4().hex[:6]
    test_query = f"unique test query {test_id}"
    try:
        with patch("api.routes.process_news_search", return_value=mock_articles):
            with patch("api.routes.analyze_and_group_news_bias", return_value=(mock_summary, mock_articles, mock_viz)):
                payload = {"query": test_query}
                # 1. First call: Cache miss -> runs pipeline -> stores to DuckDB
                resp1 = client.post("/api/v1/analyze", json=payload)
                assert resp1.status_code == 200
                data1 = resp1.json()
                assert data1["status"] == "success"
                assert data1["cached"] is False
                assert "redirect_url" in data1
                assert test_id in data1["id"]

                # 2. Second call: DuckDB cache hit!
                resp2 = client.post("/api/v1/analyze", json=payload)
                assert resp2.status_code == 200
                data2 = resp2.json()
                assert data2["status"] == "success"
                assert data2["cached"] is True
                assert data2["id"] == data1["id"]
                assert data2["redirect_url"] == data1["redirect_url"]
    finally:
        with database.connect() as db:
            story_key = f"unique-test-query-{test_id}"
            db.execute("DELETE FROM reports WHERE story_id = ?", [story_key])
            db.execute("DELETE FROM claims WHERE story_id = ?", [story_key])
            db.execute("DELETE FROM perspectives WHERE story_id = ?", [story_key])
            db.execute("DELETE FROM stories WHERE id = ?", [story_key])
            db.execute("DELETE FROM analyzed_queries WHERE query_key = ?", [test_query])


def test_edition_endpoints():
    """Test merged edition endpoints from web-apis."""
    # 1. Edition metadata
    resp_meta = client.get("/api/v1/edition")
    assert resp_meta.status_code == 200
    meta = resp_meta.json()
    assert meta["story_count"] >= 9
    assert "checked" in meta

    # 2. Stories list
    resp_stories = client.get("/api/v1/stories")
    assert resp_stories.status_code == 200
    stories_data = resp_stories.json()
    assert stories_data["total"] >= 9
    assert len(stories_data["items"]) >= 9

    # 3. Single story detail
    first_id = stories_data["items"][0]["id"]
    resp_detail = client.get(f"/api/v1/stories/{first_id}")
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["id"] == first_id
    assert len(detail["reports"]) > 0

    # 4. Full edition content (used by web frontend)
    resp_content = client.get("/api/v1/edition/content")
    assert resp_content.status_code == 200
    content = resp_content.json()
    assert "edition" in content
    assert len(content["stories"]) >= 9


def test_lab_endpoints():
    """Test merged Lens Lab endpoints from web-apis."""
    # 1. Lab metadata
    resp_lab = client.get("/api/v1/lab")
    assert resp_lab.status_code == 200
    lab_meta = resp_lab.json()
    assert len(lab_meta["lenses"]) == 8

    # 2. Lab stories
    resp_stories = client.get("/api/v1/lab/stories")
    assert resp_stories.status_code == 200
    lab_stories = resp_stories.json()
    assert lab_stories["total"] >= 4

    # 3. Lab content
    resp_content = client.get("/api/v1/lab/content")
    assert resp_content.status_code == 200
    content = resp_content.json()
    assert "lab" in content
    assert len(content["stories"]) >= 4


def test_static_illustration_endpoint():
    """Verify SVG illustration serving."""
    response = client.get("/static/illustrations/protest.svg")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert "<svg" in response.text


@pytest.mark.asyncio
async def test_domain_aware_tech_analysis():
    from services.ai_bias_service import analyze_and_group_news_bias
    from schemas import NewsArticle, TopicDomain, BiasCategory

    mock_tech_articles = [
        NewsArticle(
            title="Starlink gains rapid adoption in rural regions with high speed satellite connectivity",
            source="Tech Wire",
            url="https://example.com/starlink-growth",
            snippet="Massive breakthrough in rural broadband connectivity and consumer benefits.",
            date="10/10/2026",
            cleaned_content="A massive breakthrough in rural broadband connectivity brings huge advantages and opportunities.",
            content_length=150
        ),
        NewsArticle(
            title="Domestic telecom operators voice concern over spectrum allocation and regulatory hurdles",
            source="Financial Daily",
            url="https://example.com/telecom-dispute",
            snippet="Antitrust pushback, security concern, and regulatory delays raised by local telcos.",
            date="10/10/2026",
            cleaned_content="Antitrust pushback, national security concerns, and monopoly risks prompt regulatory challenges.",
            content_length=160
        )
    ]

    mock_ai_markdown = """
Domain: Technology & Business

Article 1
Category: Supportive / Optimistic
Score: 0.6
Framing: Highlights consumer connectivity advantages and technological progress.

Article 2
Category: Critical / Skeptical
Score: -0.5
Framing: Emphasizes domestic market competition concerns and regulatory hurdles.

### Supportive
Highlights high speed satellite broadband expansion.

### Critical
Focuses on local telecom antitrust pushback and spectrum allocation disputes.

### Summary
Key consensus points:
- Satellite internet deployment advances rapidly across remote regions
- Regulatory debates over spectrum allocation remain unresolved
"""

    with patch("services.ai_bias_service._detect_topic_domain", return_value=TopicDomain.TECH_BUSINESS):
        with patch("services.ai_bias_service._query_serpapi_ai_mode", return_value=mock_ai_markdown):
            summary_result, updated_articles, viz_data = await analyze_and_group_news_bias(
                query="Starlink Elon Musk India",
                articles=mock_tech_articles
            )

            assert summary_result.topic_domain == TopicDomain.TECH_BUSINESS
            assert viz_data.topic_domain == TopicDomain.TECH_BUSINESS
            categories = [a.bias_info.bias_category for a in updated_articles]
            assert BiasCategory.SUPPORTIVE in categories
            assert BiasCategory.CRITICAL in categories
            for art in updated_articles:
                assert art.bias_info.political_leaning is None


def test_serpapi_balance_endpoint():
    response = client.get("/api/v1/serpapi/balance")
    assert response.status_code == 200
    data = response.json()
    assert "total_searches_left" in data
    assert "plan_name" in data
    assert isinstance(data["total_searches_left"], int)


def test_blocked_content_detection():
    from services.article_scraper import is_blocked_or_error_content

    error_page = (
        "Warning: Target URL returned error 403: Forbidden\n\n"
        "Request blocked. We can't connect to the server for this app or website at this time. "
        "Generated by cloudfront (CloudFront) Request ID: 12345"
    )
    assert is_blocked_or_error_content(error_page) is True

    valid_news = (
        "Demonstrators gathered in central New Delhi on Saturday to demand electoral roll reforms. "
        "Authorities deployed thousands of security personnel and temporarily shut down transit lines."
    )
    assert is_blocked_or_error_content(valid_news) is False


def test_production_duckdb_file_isolation():
    """Verify that test execution runs against an isolated DB and never touches production DB."""
    assert database.is_test_environment() is True
    active_db = database.get_db_path().resolve()
    prod_db = database.DB_PATH.resolve()
    assert active_db != prod_db, "Tests must never point to production DuckDB file!"
    assert "duckdb_test_" in str(active_db) or "test_" in active_db.name


def test_extension_analyze_response_fields():
    """Verify that /analyze returns the exact fields needed by the extension."""
    payload = {"query": "Jantar mantar protest"}
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cjp-dipke-detained"
    assert data["news_group_id"] == "cjp-dipke-detained"
    assert data["redirect_url"] == "/story.html?id=cjp-dipke-detained"
    assert data["web_url"] == "http://localhost:8000/web/story.html?id=cjp-dipke-detained"
    assert data["cached"] is True



