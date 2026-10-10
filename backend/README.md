# News Bias Summarizer - Backend Architecture & Service Guide

High-performance, domain-aware REST API and persistent media intelligence service built with FastAPI and DuckDB, managed via [`uv`](https://github.com/astral-sh/uv).

The service handles:
- Multi-source Google News discovery via SerpAPI.
- Resilient web content extraction with TLS browser impersonation, anti-bot failover, and OpenGraph lead image extraction.
- Domain-aware AI perspective analysis and multi-angle summarization via **SerpAPI Google AI Mode**.
- Persistent DuckDB caching and query routing for instantaneous lookups (`< 20ms`).
- Serving the unified web portal dashboard (`/web`) and editorial SVG illustrations (`/static/illustrations/`).

---

## 1. System Architecture

```text
+-----------------------------------------------------------------------------------------+
|                                    CLIENT REQUEST                                       |
|                  (Web UI Dashboard / Chrome Extension / REST Client)                    |
+--------------------------------------------+--------------------------------------------+
                                             |
                      +----------------------+----------------------+
                      | POST /api/v1/analyze                        | GET /api/v1/serpapi/balance
                      v                                             v
         +--------------------------+                 +--------------------------+
         | FastAPI Router: routes.py|                 | SerpAPI Account Endpoint |
         +------------+-------------+                 +-------------+------------+
                      |                                             | (Free Call)
         +-------------------------------+
         | DuckDB Cache Check (database) |
         +---------------+---------------+
                        /                 \
            (Cache Hit)/                   \(Cache Miss)
                      v                     v
+-----------------------------+  +-------------------------------------------------------------+
| data/nonpartisan.duckdb     |  |                  LIVE PROCESSING PIPELINE                   |
| - Serves cached story & data|  |                                                             |
| - Returns instant redirect  |  | 1. Google News Candidate Search (serp_service.py)           |
|   (/story.html?id=...)      |  |    - Fetches up to 15 news candidates via SerpAPI           |
| - cached: true              |  |    - Extracts headlines, snippets, and image thumbnails     |
+-----------------------------+  |                                                             |
                                 | 2. Resilient Scraper & Image Grabber (article_scraper.py)   |
                                 |    - Primary: curl_cffi with Chrome 124 TLS Impersonation   |
                                 |    - Lead Media: Extracts <meta property="og:image"> tags   |
                                 |    - Fallback: r.jina.ai Reader Proxy if 403 / anti-bot     |
                                 |    - Validation: Rejects CloudFront 403s & challenge pages  |
                                 |    - Auto-Failover: Advances candidates until 5 clean texts |
                                 |                                                             |
                                 | 3. AI Perspective & Summarization (ai_bias_service.py)      |
                                 |    - Step A: Dynamic Domain Classification via SerpAPI AI   |
                                 |              (Political vs Tech/Business vs General)        |
                                 |    - Step B: Tailored AI Perspective Evaluation             |
                                 |              * Political: Left / Center / Right (-1 to +1)  |
                                 |              * Tech/Business: Critical/Neutral/Supportive   |
                                 |    - Step C: Consensus Summarization & Spectrum Extraction  |
                                 |                                                             |
                                 | 4. DuckDB Persistence (database.py)                         |
                                 |    - Stores analyzed query in analyzed_queries              |
                                 |    - Stores full story, reports, claims, and perspectives   |
                                 |    - Assigns dynamic lead image or SVG illustration         |
                                 +------------------------------+------------------------------+
                                                                |
                                                                v
                                                 +------------------------------+
                                                 |   Pydantic AnalysisResponse  |
                                                 |   - redirect_url & story id  |
                                                 |   - cached: false            |
                                                 |   - 5 Articles, Bias Groups, |
                                                 |     Key Points, Visualization|
                                                 +------------------------------+
```

---

## 2. Core Architectural Principles

### 2.1 Domain-Aware Perspective Analysis (Zero Hardcoded Slants)
Traditional bias checkers force every article onto an artificial 1-dimensional "Left vs. Right" political spectrum. However, for business, technological, or regulatory developments (such as *Starlink broadband expansion*, semiconductor trade restrictions, or EV subsidies), Left/Right classifications are artificial and unhelpful.

Our backend addresses this via a **dynamic two-phase AI pipeline**:
1. **Dynamic Domain Classification**: SerpAPI Google AI Mode analyzes the overarching topic to classify it as `Political`, `Technology & Business`, or `General / Non-Political`. There are **zero hardcoded keyword lists or company dictionaries**.
2. **Tailored Perspective Evaluation**:
   - **`Political`**: Evaluates partisan editorial bias across **`Left`**, **`Center`**, and **`Right`** (`-1.0` to `+1.0`), mapping each article to fine-grained leanings (`Left-leaning`, `Moderate / Centrist`, `Right-leaning`).
   - **`Technology & Business`**: Evaluates stakeholder framing across **`Critical / Skeptical`** (antitrust pushback, regulatory hurdles, security concerns), **`Neutral / Balanced`** (factual wire updates), and **`Supportive / Optimistic`** (connectivity expansion, commercial opportunities). Non-political stories are assigned `political_leaning: null`.
   - **`General / Non-Political`**: Evaluates balance and factual verification without forcing partisan categorization.

### 2.2 Resilient Multi-Candidate Scraping & Dynamic Media Extraction
News sites frequently employ aggressive anti-bot protections (Cloudflare, Akamai, CloudFront 403s) or subscription paywalls:
1. **Candidate Pool**: Searches up to 15 candidates from SerpAPI Google News.
2. **Browser TLS Fingerprint Impersonation**: Uses `curl_cffi` with Chrome 124 TLS cipher suites and headers.
3. **OpenGraph & Twitter Card Extraction**: Simultaneously extracts `<meta property="og:image">` and `<meta name="twitter:image">` tags from the live DOM for rich card imagery.
4. **Proxy Reader Fallback**: If a news site returns a 403, 503, or anti-bot challenge page, the scraper automatically falls back to `r.jina.ai`.
5. **Auto-Failover**: If an article fails validation or contains under 100 characters, it advances candidate-by-candidate until **exactly 5 clean, verified articles** are gathered.

### 2.3 Persistent DuckDB Storage & Redirection Flow
All analyzed news stories and queries are persisted into DuckDB (`data/nonpartisan.duckdb`):
- **Query Lookup**: Normalizes search terms (`"Jantar Mantar protest"` $\rightarrow$ `"jantar mantar protest"`).
- **Cache Hit**: Instantly returns `{ "cached": true, "redirect_url": "/story.html?id=cjp-dipke-detained", "id": "..." }`.
- **Cache Miss**: Runs the live scraping and AI pipeline, saves new records across `stories`, `reports`, `claims`, `perspectives`, and `analyzed_queries`, and returns the redirection URL.
- **Dynamic Images**: Stores the scraped lead image URL or falls back to category SVG illustrations (`/static/illustrations/{art}.svg`).

### 2.4 Test Isolation & Production Database Protection
To ensure production data is never corrupted or modified during testing:
- **Session-Scoped Isolation** ([`tests/conftest.py`](tests/conftest.py)): Pytest creates an isolated temporary DuckDB copy upon initialization and sets `DUCKDB_PATH`.
- **Database Hard Safety Guard** ([`database.py`](database.py)): `is_test_environment()` detects automated test environments (`pytest`, `TESTING=1`, `PYTEST_CURRENT_TEST`). If any operation attempts to connect to `data/nonpartisan.duckdb` during tests, it automatically redirects to an isolated test file or raises a safety error.

---

## 3. Directory & Module Structure

```text
backend/
├── pyproject.toml              # UV project configuration and dependencies
├── uv.lock                     # Deterministic dependency lockfile
├── .env.example                # Environment settings template
├── .env                        # Local environment variables (git-ignored)
├── constants.py                # Service constants and spectrum defaults
├── config.py                   # Pydantic BaseSettings configuration
├── logger_config.py            # Colored logging setup with severity prefixes
├── main.py                     # FastAPI application factory, lifespan hooks, static mounts
├── database.py                 # DuckDB schema management, queries, and caching logic
├── api/
│   ├── __init__.py
│   └── routes.py               # REST route handlers (/analyze, /edition, /stories, /lab, /serpapi)
├── data/
│   ├── nonpartisan.duckdb      # Persistent DuckDB database file
│   └── content.json            # Seed edition and lab stories dataset
├── schemas/
│   ├── __init__.py             # Unified re-exports for schemas and enums
│   ├── analysis.py             # AnalysisRequest, AnalysisResponse, VisualizationData
│   ├── article.py              # NewsArticle model with image_url
│   ├── bias.py                 # ArticleBias schema (topic domain, scores, leanings)
│   ├── summary.py              # BiasGroup and SummaryResult schemas
│   ├── edition.py              # EditionMetadata, StorySummary, StoryDetail schemas
│   ├── lab.py                  # LabMetadata, LabStorySummary schemas
│   ├── serpapi.py              # SerpApiBalanceResponse schema
│   └── enums/                  # Strongly-typed schema enumerations
│       ├── __init__.py
│       ├── bias.py             # TopicDomain, BiasCategory, BiasGroupCategory, PoliticalLeaning
│       └── status.py           # ResponseStatus (success, error)
├── services/
│   ├── __init__.py
│   ├── serp_service.py         # Google News fetching & SerpAPI Account API client
│   ├── article_scraper.py      # curl_cffi TLS impersonation, OpenGraph extraction & reader fallback
│   ├── news_processor.py       # Candidate gathering & 5-article failover pipeline
│   ├── ai_bias_service.py      # Google AI Mode dynamic perspective analysis engine
│   └── web_content.py          # Data transformers for edition & lab story models
└── tests/
    ├── conftest.py             # Automated test session DB isolation setup & teardown
    └── test_main.py            # Comprehensive test suite (13 passing tests)
```

---

## 4. Database Schema (DuckDB)

DuckDB table layout in `backend/data/nonpartisan.duckdb`:

| Table | Description |
| :--- | :--- |
| `stories` | Editorial and analyzed stories (id, category, title, description, summary, photo, etc.) |
| `reports` | Multi-source article reports associated with each story (headline, outlet, framing, quote) |
| `claims` | Fact-checked and asserted claims across perspectives |
| `perspectives` | Perspective groups and stakeholder angles (label, stance, outlet representation) |
| `analyzed_queries` | Normalized query lookup cache mapping search queries to cached story IDs and full responses |
| `lab_stories` | Lens Lab deep-dive stories |
| `lab_media` | Media outlets and credibility ratings |
| `lab_dimensions` | Editorial dimension metrics |
| `app_metadata` | System metadata (schema versions, last updated timestamps) |

---

## 5. REST API Reference

### 5.1 Analyze News Perspectives (`POST /api/v1/analyze`)
Takes a news query, checks DuckDB cache, runs the live multi-source AI pipeline on cache miss, stores the result in DuckDB, and returns the analysis and redirection URL.

- **Request Body**:
  ```json
  {
    "query": "Jantar mantar protest"
  }
  ```
  *(Note: `search_query` and `text` are also accepted for backward compatibility).*

- **Response (Cache Hit)**:
  ```json
  {
    "status": "success",
    "query_used": "Jantar mantar protest",
    "cached": true,
    "id": "cjp-dipke-detained",
    "news_group_id": "cjp-dipke-detained",
    "redirect_url": "/story.html?id=cjp-dipke-detained",
    "web_url": "http://localhost:8000/web/story.html?id=cjp-dipke-detained",
    "articles_fetched_count": 5,
    "articles": [...],
    "summary": {...},
    "visualization_data": {...}
  }
  ```

### 5.2 Edition & Story Endpoints
- **`GET /api/v1/edition`**: Returns current edition metadata (checked time, story count).
- **`GET /api/v1/edition/content`**: Returns the complete edition bundle used by the web frontend.
- **`GET /api/v1/stories`**: Lists all active stories with summary cards.
- **`GET /api/v1/stories/{id}`**: Detailed story breakdown with reports, perspectives, and claims.

### 5.3 Lens Lab Endpoints
- **`GET /api/v1/lab`**: Lens Lab metadata and lens dimensions.
- **`GET /api/v1/lab/stories`**: List of Lens Lab analytical stories.
- **`GET /api/v1/lab/content`**: Complete Lens Lab content bundle.

### 5.4 Free SerpAPI Quota & Balance Check (`GET /api/v1/serpapi/balance`)
Inspects remaining SerpAPI searches without consuming monthly credits.
- **Response**:
  ```json
  {
    "account_email": "user@example.com",
    "plan_name": "Free Plan",
    "total_searches_left": 1226,
    "plan_searches_left": 226,
    "searches_per_month": 250,
    "this_month_usage": 24,
    "this_hour_searches": 0,
    "account_rate_limit_per_hour": 200000,
    "plan_renewal_date": "2026-11-09"
  }
  ```

### 5.5 Static Editorial Illustrations (`GET /static/illustrations/{name}.svg`)
Serves lightweight vector illustrations (`economy`, `markets`, `protest`, `diplomacy`, `saudi`) when articles do not have photograph assets.

---

## 6. Setup & Execution Guide

### 1. Install Dependencies
```bash
cd backend
uv sync
```

### 2. Configure Environment (`.env`)
```bash
Copy-Item .env.example .env   # Windows
# cp .env.example .env        # Linux/macOS
```
Ensure your `SERP_API_KEY` is set in `.env`.

### 3. Start Development Server
```bash
uv run uvicorn main:app --reload --port 8000
```
- **Web UI**: [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html)
- **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health**: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run Automated Tests
```bash
uv run pytest
```
Output:
```text
tests/test_main.py .............                                         [100%]
============================= 13 passed in 4.18s ==============================
```
*(All 13 tests execute against an isolated temporary DuckDB file; the production database `data/nonpartisan.duckdb` is never modified).*
