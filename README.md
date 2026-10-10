# News Bias Summarizer

A full-stack media intelligence platform and news bias summarizer that analyzes news coverage, summarizes contrasting perspectives, visualizes viewpoint spectrums across diverse media outlets, and serves persistent editions via an interactive web portal and Chrome extension.

---

## Architecture Overview

```text
+-----------------------------------------------------------------------------------------+
|                                        END USERS                                        |
|               (Reading Articles via Chrome Extension or Web UI Dashboard)               |
+--------------------------------------------+--------------------------------------------+
                                             |
                  +--------------------------+--------------------------+
                  | Chrome Extension (extension/)                       | Web UI Dashboard (web/)
                  | Extracts active article & sends query               | Interactive search portal & stories
                  v                                                     v
+-----------------------------------------------------------------------------------------+
|                             FASTAPI BACKEND (backend/)                                  |
|   Endpoints:                                                                            |
|   - POST /api/v1/analyze           - GET /api/v1/edition/content   - GET /api/v1/stories|
|   - GET /api/v1/stories/{id}       - GET /api/v1/lab/content       - GET /health        |
|   - GET /api/v1/serpapi/balance    - GET /static/illustrations/... - Static: /web       |
+--------------------------------------------+--------------------------------------------+
                                             |
         +-----------------------------------+-----------------------------------+
         |                                                                       |
         v                                                                       v
+------------------------------------+                 +---------------------------------+
|  DUCKDB CACHED HIT                 |                 |  LIVE PIPELINE (CACHE MISS)     |
|  Query found in DuckDB:            |                 |                                 |
|  - Serves cached story & analysis  |                 |  1. Candidate News Discovery    |
|  - Returns instant redirect_url    |                 |     (SerpAPI Google News)       |
|    (/story.html?id=...)            |                 |                                 |
|  - cached: true                    |                 |  2. Resilient Scraper & Images  |
+------------------------------------+                 |     - curl_cffi TLS impersonate |
                                                       |     - OpenGraph lead photo grab |
                                                       |     - r.jina.ai proxy fallback  |
                                                       |     - Rejects 403s / challenges |
                                                       |     - Auto-failover to 5 texts  |
                                                       |                                 |
                                                       |  3. AI Perspective & Summarize  |
                                                       |     - Dynamic Domain Detection  |
                                                       |     - Tailored Spectrum Labels  |
                                                       |     - Consensus Summarization   |
                                                       |                                 |
                                                       |  4. Store to DuckDB & Return    |
                                                       |     - Inserts into DuckDB tables|
                                                       |       (stories, reports, etc.)  |
                                                       |     - Returns redirect_url & id |
                                                       +----------------+----------------+
                                                                        |
                                                                        v
                                                       +---------------------------------+
                                                       |    Structured AnalysisResponse  |
                                                       |    (Articles, Groups, Spectrum, |
                                                       |     redirect_url, id, cached)   |
                                                       +---------------------------------+
```

---

## Repository Components

- **[`backend/`](backend/)**: Unified FastAPI REST API handling DuckDB storage, SerpAPI Google News search, resilient anti-bot web scraping, OpenGraph lead image extraction, domain-aware perspective analysis via SerpAPI Google AI Mode, and web asset serving (`/web`).
- **[`web/`](web/)**: Editorial web application displaying edition top stories, multi-perspective breakdowns, interactive viewpoint spectrums, and Lens Lab analysis.
- **[`extension/`](extension/)**: Manifest V3 Chrome Extension that extracts the current page article context and queries the backend.
- **[`worklist.md`](worklist.md)**: Engineering task checklist tracking architecture migrations, features, and QA status.

---

## Key Features

1. **Persistent DuckDB Storage & Instant Caching**:
   - Stores analyzed queries and stories in DuckDB ([`backend/data/nonpartisan.duckdb`](backend/data/nonpartisan.duckdb)).
   - Cache hits return in `< 20ms` with `cached: true` and a ready-to-navigate `redirect_url` (`/story.html?id=...`).
   - Relational schema storing stories, multi-source reports, claims, perspectives, and query keys.
2. **Domain-Aware Perspective Analysis (Zero Hardcoded Slants)**:
   - Evaluates political news across standard editorial leanings (**Left**, **Center**, **Right**).
   - Dynamically routes corporate, scientific, and technology news (e.g., *Starlink*, AI regulations, EV subsidies) across stakeholder dimensions (**Critical / Skeptical**, **Neutral / Balanced**, **Supportive / Optimistic**).
   - Zero hardcoded domain keywords; uses SerpAPI Google AI Mode for dynamic classification.
3. **Resilient Failover Scraping & Dynamic Media Extraction**:
   - Uses `curl_cffi` Chrome 124 browser TLS impersonation to bypass Cloudflare and Akamai bot protections.
   - Automatically falls back to `r.jina.ai` reader proxy when sites return anti-bot challenges or 403 blocks.
   - Extracts dynamic lead images via OpenGraph / Twitter cards (`<meta property="og:image">`) or SerpAPI thumbnails, falling back gracefully to thematic editorial SVG illustrations.
4. **Unified API & Frontend Serving on Port 8000**:
   - Merged former `web-apis/` directly into `backend/`.
   - FastAPI serves API routes, static SVG editorial illustrations (`/static/illustrations/{art}.svg`), and mounts the web UI dashboard at `/web`.
5. **Strict Test Database Isolation**:
   - Automated tests run against isolated session-scoped temporary DuckDB copies.
   - Hard safety guard in `backend/database.py` prevents test executions from ever reading or modifying the production DuckDB file.
6. **Free SerpAPI Quota Monitoring (`GET /api/v1/serpapi/balance`)**:
   - Inspect remaining monthly searches, hourly rate limits, and plan details without consuming search credits.

---

## Quickstart Guide

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager:
  - **Windows (PowerShell)**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - **macOS / Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 1. Install Dependencies
```bash
cd backend
uv sync
```

### 2. Configure Environment
```bash
Copy-Item .env.example .env    # Windows
# cp .env.example .env         # macOS/Linux
```
Configure your `SERP_API_KEY` inside `backend/.env`.

### 3. Run Development Server
```bash
uv run uvicorn main:app --reload --port 8000
```
- **Web Portal**: [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run Automated Tests
```bash
uv run pytest
```

---

For in-depth architecture details, database schema layouts, and API specifications, see [`backend/README.md`](backend/README.md).
