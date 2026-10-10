# Work List

## 1. Chrome Extension (`extension/`)
- [ ] **1.1 Scrape user's current web page** &mdash; [`extension/`](extension/)
  - Extract active news channel/article DOM content
- [ ] **1.2 Parse to text** &mdash; [`extension/`](extension/)
  - Extract article headline and body text
- [ ] **1.3 AI summarization** &mdash; [`extension/`](extension/)
  - Generate brief initial summary of user's current article
- [ ] **1.4 Search string** &mdash; [`extension/`](extension/)
  - Derive search query string and send payload to backend

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
- [x] **2.7 Cache response for Mock Mode**
  - Persists analysis response to [`backend/data/mock_response.json`](backend/data/mock_response.json) without accidental test overwrites
- [x] **2.8 Dynamic Domain-Aware Perspective Analysis**
  - Classifies stories into Political vs Technology & Business vs General via SerpAPI Google AI Mode
  - Evaluates non-political stories (e.g. Starlink) across Critical/Neutral/Supportive perspectives with `political_leaning=None`
- [x] **2.9 Anti-bot & 403 Block Page Rejection**
  - Detects CloudFront, Cloudflare, and proxy block pages in [`backend/services/article_scraper.py`](backend/services/article_scraper.py) and fails over to valid candidate articles
- [x] **2.10 SerpAPI Account & Balance Endpoint**
  - Free quota & search credits inspection at `GET /api/v1/serpapi/balance`


---

## 3. Frontend (`web/`)
- [ ] **3.1 Receive & render visualization** &mdash; [`web/`](web/)
  - Political spectrum chart (Left to Right)
  - Bias breakdown across the 5 fetched news sources
  - Multi-article AI summary comparison view
