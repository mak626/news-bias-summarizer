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
                  | Extracts active article & sends query to backend    | Interactive search portal & stories
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
|  - Serves cached story & analysis  |                 |  1. Google AI Query Compression |
|  - Returns instant redirect_url    |                 |     (SerpAPI Google AI Mode)    |
|    (/story.html?id=...)            |                 |                                 |
|  - cached: true                    |                 |  2. Candidate News Discovery    |
|                                    |                 |     (SerpAPI Google News)       |
|                                    |                 |                                 |
|                                    |                 |  3. Resilient Scraper & Images  |
|                                    |                 |     - curl_cffi TLS impersonate |
|                                    |                 |     - OpenGraph lead photo grab |
|                                    |                 |     - r.jina.ai proxy fallback  |
|                                    |                 |     - Auto-failover to 5 texts  |
|                                    |                 |                                 |
|                                    |                 |  4. AI Perspective & Summarize  |
|                                    |                 |     - Dynamic Domain Detection  |
|                                    |                 |     - Tailored Spectrum Labels  |
|                                    |                 |     - Consensus Summarization   |
|                                    |                 |                                 |
|                                    |                 |  5. Store to DuckDB & Return    |
|                                    |                 |     - Inserts into DuckDB tables|
|                                    |                 |     - Returns redirection URLs  |
+------------------------------------+                 +----------------+----------------+
                                                                        |
                                                                        v
                                                       +---------------------------------+
                                                       |   Streamlined Analyze Response  |
                                                       |   { id, news_group_id,          |
                                                       |     redirect_url, web_url }     |
                                                       +---------------------------------+
```

---

## Repository Components

- **[`backend/`](backend/)**: Unified FastAPI REST API handling DuckDB storage, SerpAPI Google News search, resilient anti-bot web scraping, OpenGraph lead image extraction, domain-aware perspective analysis via SerpAPI Google AI Mode, and web asset serving (`/web`).
- **[`extension/`](extension/)**: Manifest V3 Chrome Extension built with WXT, React, TypeScript, and `pnpm`. Features real-time backend connection status monitoring, offline error handling, and in-page news extraction.
- **[`web/`](web/)**: Editorial web application displaying edition top stories, multi-perspective breakdowns, interactive viewpoint spectrums, and Lens Lab analysis.
- **[`Makefile`](Makefile)**: Global project orchestration script for installing dependencies, running dev servers, building the extension, and running automated tests.
- **[`worklist.md`](worklist.md)**: Engineering task checklist tracking architecture migrations, features, and QA status.

---

## Key Features

1. **Persistent DuckDB Storage & Instant Caching**:
   - Stores analyzed queries and stories in DuckDB ([`backend/data/nonpartisan.duckdb`](backend/data/nonpartisan.duckdb)).
   - Cache hits return in `< 20ms` with `cached: true` and a ready-to-navigate `redirect_url` (`/story.html?id=...`).
2. **Domain-Aware Perspective Analysis (Zero Hardcoded Slants)**:
   - Evaluates political news across standard editorial leanings (**Left**, **Center**, **Right**).
   - Dynamically routes corporate, scientific, and technology news (e.g., *Starlink*, AI regulations, EV subsidies) across stakeholder dimensions (**Critical / Skeptical**, **Neutral / Balanced**, **Supportive / Optimistic**).
   - Zero hardcoded domain keywords; uses SerpAPI Google AI Mode for dynamic classification.
3. **Resilient Failover Scraping & Dynamic Media Extraction**:
   - Uses `curl_cffi` Chrome 124 browser TLS impersonation to bypass Cloudflare and Akamai bot protections.
   - Automatically falls back to `r.jina.ai` reader proxy when sites return anti-bot challenges or 403 blocks.
   - Extracts dynamic lead images via OpenGraph / Twitter cards (`<meta property="og:image">`) or SerpAPI thumbnails, falling back gracefully to thematic editorial SVG illustrations.
4. **Streamlined Web Extension Integration**:
   - Extension sends article context directly to `POST /api/v1/analyze`.
   - Backend returns a lightweight redirection payload (`web_url`, `redirect_url`, `id`).
   - Extension includes real-time backend health checking (`/health`) and displays helpful error banners with retry buttons if the backend service is offline.
5. **Unified API & Frontend Serving on Port 8000**:
   - FastAPI serves API routes, static SVG editorial illustrations (`/static/illustrations/{art}.svg`), and mounts the web UI dashboard at `/web`.
6. **Strict Test Database Isolation**:
   - Automated tests run against isolated session-scoped temporary DuckDB copies.
   - Hard safety guard in `backend/database.py` prevents test executions from ever reading or modifying the production DuckDB file.
7. **Free SerpAPI Quota Monitoring (`GET /api/v1/serpapi/balance`)**:
   - Inspect remaining monthly searches, hourly rate limits, and plan details without consuming search credits.

---

## Quickstart Guide

### Prerequisites
- Python 3.12+ with [`uv`](https://github.com/astral-sh/uv)
- Node.js 18+ with [`pnpm`](https://pnpm.io/) (`corepack enable` or `npm install -g pnpm`)
- Make (optional, for running convenience Makefile targets)

---

### 1. Using the Global Makefile (Recommended)

The root [`Makefile`](Makefile) provides simple commands for the entire stack:

```bash
# Install all dependencies (Backend uv sync + Extension pnpm install)
make setup

# Start the FastAPI backend server (http://localhost:8000)
make run
# or: make backend-dev

# In a separate terminal: Start Chrome Extension in live dev mode
make extension-dev

# Build production Chrome extension bundle
make extension-build

# Run Backend automated test suite
make test
# or verbose: make test-v

# Inspect DuckDB database path and story counts
make db-info

# Clean caches and temporary build artifacts
make clean
```

---

### 2. Manual Setup

#### Backend Setup:
```bash
cd backend
uv sync

# Configure environment
cp .env.example .env    # On Windows: Copy-Item .env.example .env
# Add your SERP_API_KEY inside backend/.env

# Run server
uv run uvicorn main:app --reload --port 8000
```
- **Web Portal**: [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

#### Chrome Extension Setup:
```bash
cd extension
pnpm install

# Build for production
pnpm build
```

#### Loading Extension in Google Chrome:
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked** and select the directory:
   ```text
   extension/.output/chrome-mv3
   ```
4. Click the Nonpartisan extension icon on any news article page to see diverse perspectives!

---

For detailed backend architecture documentation, database schemas, and API references, see [`backend/README.md`](backend/README.md).
For extension architecture, see [`extension/README.md`](extension/README.md).
