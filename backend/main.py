import sys
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from api import router as api_router
from logger_config import setup_logging
import database

# Setup colored logging
setup_logging()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIST = BASE_DIR.parent / "web" / "dist"

ILLUSTRATIONS = {
    "economy": '<path d="M37 206h286M56 94l122-58 123 58zM64 113h233M70 190h222M84 114v74M129 114v74M176 114v74M222 114v74M271 114v74"/>',
    "markets": '<path d="M45 43v166h278M76 183l48-56 41 24 55-70 36 23 52-55M280 49h28v29"/>',
    "protest": '<rect x="34" y="27" width="105" height="65" rx="5"/><path d="M86 92v38M47 45h77M55 58h61M58 73h57"/><circle cx="57" cy="162" r="18"/><circle cx="117" cy="150" r="21"/><circle cx="185" cy="171" r="19"/>',
    "diplomacy": '<circle cx="180" cy="125" r="88"/><ellipse cx="180" cy="125" rx="42" ry="88"/><path d="M98 91h164M92 127h177M103 165h152"/>',
    "saudi": '<path d="M29 206h306M46 206v-50h35v50M106 206v-81h45v81M180 206V84h38v122M263 206V51l28-23 28 23v155"/>',
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DuckDB tables and default seed data
    database.initialize()
    stories, lab_stories = database.counts()
    logger.info(f"DuckDB initialized with {stories} stories and {lab_stories} Lab stories.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware (allows requests from Chrome extensions, web UI, local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in settings.CORS_ORIGINS else settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static web directory & images if available
if WEB_DIST.exists():
    images_dir = WEB_DIST / "images"
    if images_dir.exists():
        app.mount("/static/images", StaticFiles(directory=images_dir), name="images")
    app.mount("/web", StaticFiles(directory=WEB_DIST, html=True), name="web")


@app.get("/static/illustrations/{name}.svg", include_in_schema=False)
def illustration(name: str):
    drawing = ILLUSTRATIONS.get(name)
    if not drawing:
        raise HTTPException(404, detail="Illustration not found")
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 250"><rect width="360" height="250" fill="#181825"/><g fill="none" stroke="#b4befe" stroke-width="5">{drawing}</g></svg>'
    return Response(svg, media_type="image/svg+xml")


@app.get("/story.html", include_in_schema=False)
def redirect_story(request: Request):
    """Convenience redirect from /story.html?id=... to /web/story.html?id=..."""
    query = request.url.query
    target = f"/web/story.html?{query}" if query else "/web/story.html"
    return RedirectResponse(target)


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "web_portal": "/web/index.html"
    }


@app.get("/health", tags=["Health"])

async def health_check():
    stories, lab_stories = database.counts()
    return {
        "status": "healthy",
        "database": "duckdb",
        "stories": stories,
        "lab_stories": lab_stories
    }


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Top-level alias for /analyze (hidden from OpenAPI schema to prevent duplicate docs)
from schemas import AnalysisRequest
from api.routes import analyze_news_bias

@app.post("/analyze", include_in_schema=False)
async def analyze_alias(request_body: AnalysisRequest, request: Request):
    return await analyze_news_bias(request_body, request)


def main():
    """CLI Entrypoint for running directly or with `uv run python main.py`"""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
