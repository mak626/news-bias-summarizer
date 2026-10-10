# News Bias Summarizer - Backend Architecture & Service Guide

High-performance, domain-aware REST API built with FastAPI and managed via [`uv`](https://github.com/astral-sh/uv). It ingests news queries, performs multi-source Google News discovery, runs resilient content extraction with automatic failover, and leverages **SerpAPI Google AI Mode** to dynamically summarize and group coverage across tailored perspective spectrums (e.g. *Left / Center / Right* for politics, or *Critical / Neutral / Supportive* for technology and business).

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
         +------------+------------+                                v
         | MOCK_MODE check         |                 +--------------------------+
         +------------+------------+                 |  SerpAPI: account.json   |
        /                           \                +--------------------------+
(MOCK_MODE=true)             (MOCK_MODE=false)
       v                             v
+------------------------+  +-------------------------------------------------------------+
| data/mock_response.json|  |                  LIVE PROCESSING PIPELINE                   |
| (Saved Golden Fixture) |  |                                                             |
| Returns instant JSON   |  | 1. Google News Candidate Search (serp_service.py)           |
+------------------------+  |    - Fetches up to 15 news candidate items via SerpAPI      |
                            |                                                             |
                            | 2. Resilient Scraper & Failover Engine (news_processor.py)  |
                            |    - Primary: curl_cffi with Chrome 124 TLS Impersonation   |
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
                            +------------------------------+------------------------------+
                                                           |
                                                           v
                                            +------------------------------+
                                            |   Pydantic AnalysisResponse  |
                                            |   (5 Articles, Bias Groups,  |
                                            |   Key Points, Visualization) |
                                            +------------------------------+
```


---

## 2. Core Architectural Principles

### 2.1 Domain-Aware Perspective Analysis (Zero Hardcoded Ratings)
Traditional media bias engines force a rigid 1-dimensional "Left vs. Right" political spectrum onto every news story. However, for technology, corporate, and scientific news (e.g. *Starlink Elon Musk India*, semiconductor export controls, AI licensing, or EV tariffs), traditional Left-Right categories are artificial and inaccurate.

Our backend addresses this via a **two-stage AI classification pipeline**:
1. **Dynamic Domain Detection**: The backend first queries SerpAPI Google AI Mode to classify whether the topic is `Political`, `Technology & Business`, or `General / Non-Political`. There are **zero hardcoded keyword lists or company dictionaries**.
2. **Tailored Perspective Evaluation**:
   - **`Political`**: Evaluates partisan editorial bias across **`Left`**, **`Center`**, and **`Right`** (`-1.0` to `+1.0`), mapping each article to fine-grained editorial leanings (`Left-leaning`, `Moderate / Centrist`, `Right-leaning`).
   - **`Technology & Business`**: Evaluates stakeholder framing across **`Critical / Skeptical`** (e.g., regulatory hurdles, local telecom opposition, security clearances), **`Neutral / Balanced`** (wire facts and status updates), and **`Supportive / Optimistic`** (e.g., tech disruption, digital divide bridging, consumer advantages). Non-political articles are assigned `political_leaning: None`.
   - **`General / Non-Political`**: Evaluates balance and factual attribution without imposing artificial partisan slant.

### 2.2 Resilient Multi-Candidate Scraping with Failover
News websites frequently employ Cloudflare, Akamai bot protections, or aggressive paywalls that reject generic HTTP requests. The scraper implements a multi-tier resilience strategy:
1. **Multi-Candidate Candidate Pool**: Searches up to 15 candidates from SerpAPI Google News.
2. **Browser TLS Fingerprint Impersonation**: Uses `curl_cffi` with Chrome 124 browser headers and TLS fingerprinting.
3. **Reader Fallback**: If a site blocks direct scraping (HTTP 403/503), it automatically falls back to a reader proxy (`r.jina.ai`).
4. **Automatic Failover**: If content length is under 100 characters or parsing fails, the pipeline immediately advances to the next candidate article until **exactly 5 clean, verified articles** are collected.

### 2.3 Account Quota Monitoring (Free of Charge)
The backend provides a dedicated endpoint to inspect SerpAPI account quotas and remaining searches (`GET /api/v1/serpapi/balance`). Calls to SerpAPI's `account.json` are **completely free of charge** and do not consume monthly search credits.

---

## 3. Directory & Module Structure

```text
backend/
├── pyproject.toml              # UV project configuration and dependencies
├── uv.lock                     # Deterministic dependency lockfile
├── .env.example                # Template for environment settings
├── .env                        # Local environment variables (git-ignored)
├── constants.py                # Service endpoints and default visualization weights
├── config.py                   # Pydantic BaseSettings configuration
├── logger_config.py            # Colored logging setup with severity prefixes
├── main.py                     # FastAPI application factory and lifespan hooks
├── api/
│   ├── __init__.py
│   └── routes.py               # API route declarations (/analyze, /serpapi/balance)
├── data/
│   └── mock_response.json      # Golden static mock response fixture
├── schemas/
│   ├── __init__.py             # Unified re-exports for schemas and enums
│   ├── analysis.py             # AnalysisRequest, AnalysisResponse, VisualizationData
│   ├── article.py              # NewsArticle model
│   ├── bias.py                 # ArticleBias schema (topic domain, scores, leanings)
│   ├── summary.py              # BiasGroup and SummaryResult schemas
│   ├── serpapi.py              # SerpApiBalanceResponse schema
│   └── enums/                  # Schema constraint enumerations (str, Enum)
│       ├── __init__.py
│       ├── bias.py             # TopicDomain, BiasCategory, BiasGroupCategory, PoliticalLeaning
│       └── status.py           # ResponseStatus (success, error)
├── services/
│   ├── __init__.py
│   ├── serp_service.py         # Google News fetching & SerpAPI Account API client
│   ├── article_scraper.py      # curl_cffi TLS impersonation & reader fallback scraper
│   ├── news_processor.py       # Candidate gathering & 5-article failover pipeline
│   └── ai_bias_service.py      # Google AI Mode dynamic perspective analysis engine
└── tests/
    └── test_main.py            # Comprehensive test suite (8 unit & integration tests)
```

---

## 4. Schemas & Enums Architecture

All schema fields use strongly typed Python `(str, Enum)` enumerations located under [`backend/schemas/enums/`](schemas/enums/):

### Enums ([`schemas/enums/bias.py`](schemas/enums/bias.py))
- **`TopicDomain`**: `Political`, `Technology & Business`, `General / Non-Political`
- **`BiasCategory`**:
  - *Political*: `Left`, `Center-Left`, `Center`, `Center-Right`, `Right`
  - *Tech/Business*: `Critical / Skeptical`, `Neutral / Balanced`, `Supportive / Optimistic`
  - *Fallback*: `Unanalyzed`
- **`BiasGroupCategory`**: `Left`, `Center`, `Right`, `Critical / Skeptical`, `Neutral / Balanced`, `Supportive / Optimistic`
- **`PoliticalLeaning`**: `Left-leaning`, `Center-Left-leaning`, `Moderate / Centrist`, `Center-Right-leaning`, `Right-leaning`

---

## 5. REST API Reference

### 5.1 Analyze News Perspectives
- **Method**: `POST`
- **Path**: `/api/v1/analyze`
- **Request Body**:
  ```json
  {
    "search_query": "Starlink Elon Musk India",
    "num_articles": 5
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "query_used": "Starlink Elon Musk India",
    "articles_fetched_count": 5,
    "articles": [
      {
        "title": "Article Headline",
        "source": "Outlet Name",
        "url": "https://...",
        "snippet": "...",
        "date": "...",
        "cleaned_content": "Cleaned article text...",
        "content_length": 1540,
        "bias_info": {
          "topic_domain": "Technology & Business",
          "bias_score": -0.4,
          "bias_category": "Critical / Skeptical",
          "political_leaning": null,
          "perspective_label": "Critical / Skeptical",
          "personal_biasing_notes": "Emphasizes spectrum allocation dispute and domestic telecom resistance."
        }
      }
    ],
    "summary": {
      "topic_domain": "Technology & Business",
      "original_summary": "Synthesized AI multi-source summary...",
      "key_points": [
        "Satellite deployment advances into rural connectivity zones.",
        "Regulatory licensing and spectrum auction debates remain active."
      ],
      "bias_overview": "Comparative breakdown of stakeholder perspectives.",
      "bias_groups": [
        {
          "category": "Critical / Skeptical",
          "outlets": ["Financial Daily"],
          "framing_overview": "Focuses on regulatory compliance and market competition.",
          "article_titles": ["..."]
        },
        {
          "category": "Neutral / Balanced",
          "outlets": ["Reuters"],
          "framing_overview": "Factual status updates on IN-SPACe clearances.",
          "article_titles": ["..."]
        },
        {
          "category": "Supportive / Optimistic",
          "outlets": ["Tech Wire"],
          "framing_overview": "Emphasizes digital divide bridging and high-speed broadband access.",
          "article_titles": ["..."]
        }
      ]
    },
    "visualization_data": {
      "topic_domain": "Technology & Business",
      "spectrum": [
        {"category": "Critical / Skeptical", "count": 2, "score": -0.5},
        {"category": "Neutral / Balanced", "count": 1, "score": 0.0},
        {"category": "Supportive / Optimistic", "count": 2, "score": 0.5}
      ],
      "average_bias": 0.04,
      "groups_count": {
        "Critical / Skeptical": 2,
        "Neutral / Balanced": 1,
        "Supportive / Optimistic": 2
      }
    }
  }
  ```

### 5.2 SerpAPI Account & Balance Check
- **Method**: `GET`
- **Path**: `/api/v1/serpapi/balance`
- **Cost**: **Free** (does not count against monthly search quotas)
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

---

## 6. Setup & Execution Guide

### Prerequisites
- Python 3.12+
- `uv` installed (`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` on Windows)

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
Edit `.env`:
```env
HOST=0.0.0.0
PORT=8000
DEBUG=True
CORS_ORIGINS=*
MOCK_MODE=false
SERP_API_KEY=your_serpapi_key_here
```
*(When `MOCK_MODE=true`, the server instantly serves static data from `data/mock_response.json` without any live network calls).*

### 3. Start Development Server
```bash
uv run uvicorn main:app --reload --port 8000
```
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run Automated Tests
```bash
uv run pytest
```
Output:
```text
tests/test_main.py ........                                              [100%]
============================== 8 passed in 7.20s ==============================
```
