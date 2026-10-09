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
- [ ] **2.4 Run biasing**
  - [ ] **2.4.1 Personal biasing checks**
    - File paths: [`backend/services/news_processor.py`](backend/services/news_processor.py), [`backend/schemas/bias.py`](backend/schemas/bias.py)
  - [ ] **2.4.2 Left/Right political checks**
    - File paths: [`backend/services/news_processor.py`](backend/services/news_processor.py), [`backend/schemas/bias.py`](backend/schemas/bias.py)
- [ ] **2.5 Run summarization**
  - Aggregate multi-outlet summaries and key points
  - File paths: [`backend/services/news_processor.py`](backend/services/news_processor.py), [`backend/schemas/summary.py`](backend/schemas/summary.py), [`backend/api/routes.py`](backend/api/routes.py)
- [ ] **2.6 Generate visualization data**
  - Format bias scores and distribution data for frontend rendering
  - File paths: [`backend/api/routes.py`](backend/api/routes.py), [`backend/schemas/analysis.py`](backend/schemas/analysis.py)

---

## 3. Frontend (`web/`)
- [ ] **3.1 Receive & render visualization** &mdash; [`web/`](web/)
  - Political spectrum chart (Left to Right)
  - Bias breakdown across the 5 fetched news sources
  - Multi-article AI summary comparison view
