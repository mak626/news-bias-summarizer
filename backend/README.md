# News Bias Summarizer - Backend

FastAPI application for news article search, content extraction/cleanup, bias analysis, summarization, and visualization data generation.

Managed using [`uv`](https://github.com/astral-sh/uv).

---

## Prerequisites

- **Python**: 3.12 or newer
- **uv**: Modern, fast Python package and project manager.
  - **Windows (PowerShell)**:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
  - **macOS / Linux**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

---

## Setup & Installation

### 1. Navigate to the backend directory
```bash
cd backend
```

### 2. Install dependencies & initialize virtual environment
`uv` will automatically create the `.venv` directory inside `backend/` and install all required dependencies:

```bash
uv sync
```

### 3. Configure environment variables
Create a `.env` file from the provided example:

- **Windows (PowerShell)**:
  ```powershell
  Copy-Item .env.example .env
  ```
- **macOS / Linux**:
  ```bash
  cp .env.example .env
  ```

Open `.env` and set your credentials:
```env
HOST=0.0.0.0
PORT=8000
DEBUG=True
CORS_ORIGINS=*
MOCK_MODE=false
SERP_API_KEY=your_serpapi_key_here
```
*(Note: Set `MOCK_MODE=true` to instantly return static JSON from `data/mock_response.json` without making any external network requests).*

---

## Running the Application

### Option A: Run directly using `uv` (Recommended)
You do not need to manually activate the virtual environment; `uv run` handles environment execution automatically:

```bash
uv run uvicorn main:app --reload --port 8000
```

### Option B: Activate the virtual environment manually

- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  uvicorn main:app --reload --port 8000
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  uvicorn main:app --reload --port 8000
  ```

The server will be available at: **`http://localhost:8000`**

---

## Testing the API

### 1. Interactive Documentation
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 2. Health Check
```bash
curl http://localhost:8000/health
```
Response:
```json
{"status": "healthy"}
```

### 3. Analyze News Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "Content-Type: application/json" \
     -d '{"search_query": "renewable energy policy", "num_articles": 5}'
```

---

## Running the Automated Test Suite

Run all unit and integration tests using pytest via `uv`:

```bash
uv run pytest
```

---

## Project Structure

```text
backend/
├── pyproject.toml      # Project configuration & dependencies managed by uv
├── uv.lock             # Lockfile for reproducible environment
├── .env.example        # Environment variables template
├── .env                # Local environment settings (git-ignored)
├── .gitignore          # Git ignore rules for .venv, caches, etc.
├── main.py             # FastAPI app initialization & entrypoint
├── config.py           # Configuration management (Pydantic / dotenv)
├── api/
│   ├── __init__.py
│   └── routes.py       # REST API endpoints (/api/v1/analyze)
├── schemas/
│   ├── __init__.py
│   └── analysis.py     # Request / Response schemas & data models
├── services/
│   ├── __init__.py
│   ├── serp_service.py     # SerpAPI Google News API search
│   ├── article_scraper.py  # HTML page fetching and text cleanup
│   └── news_processor.py   # 5-article search & failover pipeline
├── tests/
│   └── test_main.py    # Test suite
└── .venv/              # Virtual environment created by uv
```
