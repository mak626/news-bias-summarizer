# nonpartisan.ink Web API

Interactive FastAPI/Swagger service for the static content used by the local web prototype. API responses are queried from DuckDB rather than assembled from hardcoded route payloads.

## Run

```bash
cd web-apis
uv sync
uv run uvicorn main:app --reload --port 8001
```

Open [http://localhost:8001/docs](http://localhost:8001/docs). Swagger's **Try it out** buttons call the mock endpoints directly.

If `uv` is unavailable:

```bash
python3 -m venv .venv
.venv/bin/pip install 'duckdb>=1.4.0' 'fastapi>=0.143.0' 'pydantic>=2.14.0' 'uvicorn[standard]>=0.54.0'
.venv/bin/uvicorn main:app --reload --port 8001
```

The API reads `data/nonpartisan.duckdb`. On a fresh checkout, `data/content.json` is imported once to create normalized story, report, claim, perspective, lab-story, media, and lens tables. Subsequent requests query DuckDB directly. The extraction helper can refresh the seed snapshot from `../web/dist`; Node.js is not required to run the API.

Useful endpoints:

- `GET /api/v1/edition/content` — complete edition in one frontend request
- `GET /api/v1/stories`
- `GET /api/v1/stories/cjp-dipke-detained`
- `GET /api/v1/lab/content` — complete lens lab in one frontend request
- `GET /api/v1/lab/stories`
- `GET /api/v1/lab/stories/metro`
- `GET /openapi.json`
