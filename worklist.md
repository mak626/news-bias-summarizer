# Work List

## 1. Chrome Extension (`extension/`)
- [x] **1.1 Scrape user's current web page** &mdash; [`extension/`](extension/)
  - Extracts active news channel/article DOM content across Indian Express and generic news pages
- [x] **1.2 Parse to text** &mdash; [`extension/`](extension/)
  - Extracts article headline and synopsis text via [`utils/parsers.ts`](extension/utils/parsers.ts)
- [x] **1.3 AI query compression** &mdash; [`backend/services/query_compressor.py`](backend/services/query_compressor.py)
  - Compresses article text into concise search query under 20 words using SerpAPI Google AI Mode
- [x] **1.4 Search string & backend integration** &mdash; [`extension/`](extension/)
  - Sends `{ query: articleText }` to backend `/api/v1/analyze`, receives `web_url` / `redirect_url`, and redirects user to story view
- [x] **1.5 Offline Backend Detection & Error UI** &mdash; [`extension/`](extension/)
  - Real-time `/health` check on mount with status indicator (Online / Offline / Connecting)
  - Elegant error alerts with retry actions when backend service is offline, unreachable, or returns errors
- [x] **1.6 Flatten Extension Directory Structure** &mdash; [`extension/`](extension/)
  - Promoted `extension/client/` directly to `extension/` (removed redundant nesting after `extension/server/` deletion)

---

## 2. Backend (`backend/`)
- [x] **2.1 Search string to SerpAPI Google News Light API**
  - Implemented in [`backend/services/serp_service.py`](backend/services/serp_service.py)
- [x] **2.2 Fetch 5 news articles**
  - Implemented in [`backend/services/serp_service.py`](backend/services/serp_service.py) & [`backend/services/news_processor.py`](backend/services/news_processor.py)
- [x] **2.3 Fetch content of news pages & clean it up**
  - HTML extraction, script/boilerplate removal, anti-bot bypass via `curl_cffi` + reader fallback: [`backend/services/article_scraper.py`](backend/services/article_scraper.py)
  - Automatic failover retry if parsing fails until total count is 5: [`backend/services/news_processor.py`](backend/services/news_processor.py)
- [x] **2.4 Run biasing**
  - [x] **2.4.1 Personal biasing checks**
    - Implemented in [`backend/services/ai_bias_service.py`](backend/services/ai_bias_service.py), [`backend/schemas/bias.py`](backend/schemas/bias.py)
  - [x] **2.4.2 Left/Right political checks & grouping**
    - Implemented in [`backend/services/ai_bias_service.py`](backend/services/ai_bias_service.py), [`backend/schemas/bias.py`](backend/schemas/bias.py)
- [x] **2.5 Run summarization via SerpAPI Google AI Mode**
  - Multi-outlet summary, key points, and bias grouping
  - Implemented in [`backend/services/ai_bias_service.py`](backend/services/ai_bias_service.py), [`backend/schemas/summary.py`](backend/schemas/summary.py), [`backend/api/routes.py`](backend/api/routes.py)
- [x] **2.6 Generate visualization data**
  - Format bias scores, political spectrum counts, and distribution data
  - Implemented in [`backend/services/ai_bias_service.py`](backend/services/ai_bias_service.py), [`backend/schemas/analysis.py`](backend/schemas/analysis.py)
- [x] **2.7 DuckDB Analysis Caching & Query Routing**
  - Replaced Mock Mode with DuckDB persistent caching in [`backend/database.py`](backend/database.py) (`nonpartisan.duckdb`)
  - Normalized query lookups return cached analysis instantly (`< 20ms`) with `cached: true` and `redirect_url`
- [x] **2.8 Dynamic Domain-Aware Perspective Analysis**
  - Classifies stories into Political vs Technology & Business vs General via SerpAPI Google AI Mode
  - Evaluates non-political stories (e.g. Starlink) across Critical/Neutral/Supportive perspectives with `political_leaning=None`
- [x] **2.9 Anti-bot & 403 Block Page Rejection**
  - Detects CloudFront, Cloudflare, and proxy block pages in [`backend/services/article_scraper.py`](backend/services/article_scraper.py) and fails over to valid candidate articles
- [x] **2.10 SerpAPI Account & Balance Endpoint**
  - Free quota & search credits inspection at `GET /api/v1/serpapi/balance`
- [x] **2.11 Unified Backend & DuckDB Analysis Caching**
  - Consolidated `web-apis/` into `backend/` and removed standalone `web-apis/` folder
  - Persistent DuckDB schema using generic `stories` table (`stories`, `reports`, `claims`, `perspectives`, `analyzed_queries`)
  - Redirection routing: `/analyze` returns `redirect_url` (`/story.html?id=...`) and story ID if in DuckDB; otherwise executes live pipeline and caches result
  - Merged Edition (`/edition`, `/edition/content`, `/stories`), Lens Lab (`/lab`, `/lab/content`, `/lab/stories`), and SVG illustration endpoints into FastAPI service
  - Dynamic media extraction: OpenGraph `<meta property="og:image">` tags and SerpAPI thumbnails stored to DuckDB stories with SVG fallback
  - Schema alignment: Single clean `query: str` parameter on `AnalysisRequest` with backwards-compatible aliases
  - Test database isolation: Automated tests run against isolated session DuckDB copies with hard safety guards preventing writes to production `data/nonpartisan.duckdb`
- [x] **2.12 Extension Server Migration to Python & Server Deletion**
  - Converted TypeScript Hono server into Python [`backend/services/query_compressor.py`](backend/services/query_compressor.py) using SerpAPI Google AI Mode
  - Replaced Redis with DuckDB persistent caching
  - Deleted `extension/server/` and removed unwanted `.gitkeep` files



---

## 3. Frontend (`web/`)
- [ ] **3.1 Receive & render visualization** &mdash; [`web/`](web/)
  - Political spectrum chart (Left to Right)
  - Bias breakdown across the 5 fetched news sources
  - Multi-article AI summary comparison view
