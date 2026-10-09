# News Bias Summarizer

A full-stack application that analyzes news bias, summarizes viewpoints, and visualizes political leanings across diverse news outlets.

## Architecture & Components

- **`backend/`**: FastAPI REST API managing SerpAPI Google News search, article content scraping/cleanup, bias checks, and summarization.
- **`extension/`**: Chrome extension that extracts current article text and communicates with the backend.
- **`web/`**: Web UI displaying bias analysis and interactive visual spectrums.

---

## Backend Setup & Run Guide

The backend uses [`uv`](https://github.com/astral-sh/uv) for fast and reproducible Python dependency management.

### Prerequisites

- Python 3.12+
- `uv` installed:
  - **Windows**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - **macOS / Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 1. Install Dependencies & Build Virtual Environment

```bash
cd backend
uv sync
```
This automatically sets up a `.venv` virtual environment in the `backend/` folder and installs all dependencies.

### 2. Configure Environment

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `backend/.env` and optionally set your `SERP_API_KEY`. If left empty, fallback mock results are provided for local development.

### 3. Run the Development Server

```bash
uv run uvicorn main:app --reload --port 8000
```

The API will be live at `http://localhost:8000`.

- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Run Tests

```bash
uv run pytest
```

For detailed backend documentation, see [backend/README.md](backend/README.md).
