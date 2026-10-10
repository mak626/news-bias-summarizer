# nonpartisan.ink Web API

Interactive FastAPI/Swagger service for the static content used by the local web prototype.

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
.venv/bin/pip install 'fastapi>=0.143.0' 'pydantic>=2.14.0' 'uvicorn[standard]>=0.54.0'
.venv/bin/uvicorn main:app --reload --port 8001
```

The API serves a bundled JSON snapshot of the current edition and fictional lens-lab fixtures. The included extraction helper can refresh that snapshot from `../web/dist` during development; Node.js is not required to run the API.

Useful endpoints:

- `GET /api/v1/stories`
- `GET /api/v1/stories/cjp-dipke-detained`
- `GET /api/v1/lab/stories`
- `GET /api/v1/lab/stories/metro`
- `GET /openapi.json`
