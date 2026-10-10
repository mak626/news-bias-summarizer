# News Bias Summarizer

A full-stack media intelligence application that analyzes news bias, summarizes contrasting viewpoints, and visualizes perspective spectrums across diverse news outlets.

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
                  | Extracts active article                             | Interactive search portal
                  v                                                     v
+-----------------------------------------------------------------------------------------+
|                             FASTAPI BACKEND (backend/)                                  |
|   Endpoints: POST /api/v1/analyze  |  GET /api/v1/serpapi/balance  |  GET /health       |
+--------------------------------------------+--------------------------------------------+
                                             |
         +-----------------------------------+-----------------------------------+
         |                                                                       |
         v                                                                       v
+------------------------------------+                 +---------------------------------+
|  MOCK MODE (MOCK_MODE=true)        |                 |  LIVE PIPELINE (MOCK_MODE=false)|
|  Serves golden fixture instantly   |                 |                                 |
|  data/mock_response.json           |                 |  1. Candidate News Search       |
+------------------------------------+                 |     (SerpAPI Google News)       |
                                                       |                                 |
                                                       |  2. Resilient Scraper Failover  |
                                                       |     (curl_cffi TLS impersonation|
                                                       |      + Jina reader fallback;    |
                                                       |      rejects 403 blocks)        |
                                                       |                                 |
                                                       |  3. AI Perspective & Summarize  |
                                                       |     * Domain Classification     |
                                                       |     * Tailored Spectrum Grouping|
                                                       |     * Consensus Summarization   |
                                                       +----------------+----------------+
                                                                        |
                                                                        v
                                                       +---------------------------------+
                                                       |    Structured AnalysisResponse  |
                                                       |    (Articles, Groups, Spectrum) |
                                                       +---------------------------------+
```


---

## Repository Components

- **[`backend/`](backend/)**: FastAPI REST API managing SerpAPI Google News search, resilient scraping with automatic anti-bot failover, dynamic domain-aware perspective analysis via SerpAPI Google AI Mode, and quota management.
- **[`extension/`](extension/)**: Chrome Extension (Manifest V3) that extracts the active news article and queries the backend.
- **[`web/`](web/)**: Web frontend displaying multi-source consensus summaries, perspective spectrum visualizations, and bias breakdowns.
- **[`worklist.md`](worklist.md)**: Master engineering task tracking across all project modules.

---

## Key Backend Features

1. **Domain-Aware Perspective Analysis (Zero Hardcoded Ratings)**:
   - Does not force rigid 1D "Left/Right" labels on non-partisan stories (e.g. *Starlink Elon Musk India*, antitrust, or semiconductor chips).
   - Dynamically detects `Political` vs `Technology & Business` vs `General` domains using SerpAPI Google AI Mode.
   - Categorizes technology/business news across **Critical / Skeptical**, **Neutral / Balanced**, and **Supportive / Optimistic** angles.
2. **Resilient Failover Scraping**:
   - Uses `curl_cffi` Chrome 124 browser TLS impersonation to bypass Cloudflare/Akamai bot detection.
   - Falls back to `r.jina.ai` reader proxy if direct access is blocked.
   - Rejects anti-bot challenge pages and CloudFront 403 blocks, failing over to alternative candidates until **exactly 5 valid articles** are parsed.
3. **Mock Mode (`MOCK_MODE=true`)**:
   - Serves cached responses from [`backend/data/mock_response.json`](backend/data/mock_response.json) instantly without network requests or API costs.
4. **SerpAPI Balance & Quota Check (`GET /api/v1/serpapi/balance`)**:
   - Free API endpoint to check remaining searches, monthly limits, and hourly rate limits without consuming quota.

---

## Quickstart Guide

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager:
  - **Windows (PowerShell)**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - **macOS / Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 1. Install & Setup
```bash
cd backend
uv sync
```

### 2. Configure Environment
```bash
Copy-Item .env.example .env    # Windows
# cp .env.example .env         # macOS/Linux
```
Add your `SERP_API_KEY` in `backend/.env`.

### 3. Run Development Server
```bash
uv run uvicorn main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run Tests
```bash
uv run pytest
```

For in-depth architecture details, schemas, and endpoint specifications, see [backend/README.md](backend/README.md).
