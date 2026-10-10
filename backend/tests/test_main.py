import pytest
from fastapi.testclient import TestClient
from main import app
from services.article_scraper import clean_html_content
from services.news_processor import process_news_search
from unittest.mock import patch
from config import settings

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "docs" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


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
    """
    Test that if parsing fails for some candidate news articles,
    the pipeline keeps trying until total count reaches 5.
    """
    mock_candidates = [
        {"title": f"Article {i}", "url": f"https://example.com/{i}", "source": f"Source {i}", "snippet": "", "date": ""}
        for i in range(10)
    ]

    async def mock_fetch_content(url, timeout=8.0):
        if "0" in url or "2" in url:
            return None  # Parsing fails
        return f"This is valid cleaned content for {url} with sufficient length to pass the threshold requirement easily."

    with patch("services.news_processor.fetch_google_news", return_value=mock_candidates):
        with patch("services.news_processor.fetch_and_clean_article_content", side_effect=mock_fetch_content):
            results = await process_news_search("test query", target_count=5)
            assert len(results) == 5
            urls = [a.url for a in results]
            assert "https://example.com/0" not in urls
            assert "https://example.com/2" not in urls


def test_analyze_endpoint_live():
    with patch.object(settings, "MOCK_MODE", False):
        payload = {
            "search_query": "renewable energy breakthroughs",
            "num_articles": 5
        }
        response = client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["articles"]) == 5
        assert "summary" in data
        assert "bias_groups" in data["summary"]
        assert "visualization_data" in data
        assert "spectrum" in data["visualization_data"]


def test_analyze_endpoint_mock_mode():
    with patch.object(settings, "MOCK_MODE", True):
        payload = {"search_query": "Palestine and Israel conflict"}
        response = client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["articles"]) == 5
        assert bool(data["articles"][0]["source"])
        assert "bias_groups" in data["summary"]
        assert len(data["summary"]["bias_groups"]) == 3
