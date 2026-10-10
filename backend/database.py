from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

import os

import sys
import shutil

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "nonpartisan.duckdb"
SEED_PATH = BASE_DIR / "data" / "content.json"
MOCK_PATH = BASE_DIR / "tests" / "fixtures" / "mock_response.json"


def is_test_environment() -> bool:
    """Detect if running under a pytest or automated test environment."""
    return (
        os.getenv("TESTING") == "1"
        or "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
    )


def get_db_path() -> Path:
    override = os.getenv("DUCKDB_PATH")
    if override:
        path = Path(override)
    else:
        path = DB_PATH

    # Hard safety guard: Never allow tests to access the production database
    if is_test_environment() and path.resolve() == DB_PATH.resolve():
        test_fallback = BASE_DIR / "data" / "test_isolated.duckdb"
        if not test_fallback.exists() and DB_PATH.exists():
            shutil.copyfile(DB_PATH, test_fallback)
        return test_fallback

    return path


def connect() -> duckdb.DuckDBPyConnection:
    path = get_db_path()
    if is_test_environment() and path.resolve() == DB_PATH.resolve():
        raise RuntimeError(
            "SAFETY VIOLATION: Attempted to connect to production database "
            f"'{DB_PATH}' during automated testing!"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(value: str | None, fallback=None):
    return fallback if value is None else json.loads(value)


def normalize_query_key(query: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", query.lower())
    return " ".join(cleaned.split())


def initialize() -> None:
    with connect() as db:
        # Automatic Migration: rename legacy india_stories to generic stories if present
        existing_tables = [t[0] for t in db.execute("SHOW TABLES").fetchall()]
        if "india_stories" in existing_tables and "stories" not in existing_tables:
            db.execute("ALTER TABLE india_stories RENAME TO stories")

        db.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL);
            CREATE TABLE IF NOT EXISTS stories (
                id VARCHAR PRIMARY KEY, sort_order INTEGER NOT NULL, category VARCHAR NOT NULL,
                topics JSON NOT NULL, place VARCHAR NOT NULL, display_date VARCHAR NOT NULL,
                title VARCHAR NOT NULL, description VARCHAR NOT NULL, reading_time VARCHAR NOT NULL,
                summary VARCHAR NOT NULL, takeaway VARCHAR NOT NULL, art VARCHAR,
                photo JSON, primary_document JSON, open_questions JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                id VARCHAR PRIMARY KEY, story_id VARCHAR NOT NULL, sort_order INTEGER NOT NULL,
                publisher VARCHAR NOT NULL, alignment VARCHAR NOT NULL, focus VARCHAR NOT NULL,
                payload JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS claims (
                story_id VARCHAR NOT NULL, sort_order INTEGER NOT NULL, payload JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS perspectives (
                story_id VARCHAR NOT NULL, sort_order INTEGER NOT NULL, payload JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lab_dimensions (
                id VARCHAR PRIMARY KEY, sort_order INTEGER NOT NULL, payload JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lab_media (
                id INTEGER PRIMARY KEY, payload JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lab_stories (
                id VARCHAR PRIMARY KEY, sort_order INTEGER NOT NULL, category VARCHAR NOT NULL,
                title VARCHAR NOT NULL, description VARCHAR NOT NULL, payload JSON NOT NULL,
                visual JSON NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analyzed_queries (
                query_key VARCHAR PRIMARY KEY,
                search_query VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                story_id VARCHAR NOT NULL,
                response JSON NOT NULL
            );
        """)

        seeded = db.execute("SELECT count(*) FROM stories").fetchone()[0]
        if not seeded and SEED_PATH.exists():
            seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            edition, lab = seed["edition"], seed["lab"]
            db.executemany("INSERT INTO app_metadata VALUES (?, ?)", [
                ("edition_checked", edition["checked"]),
                ("edition_through", edition["through"]),
            ])
            for order, story in enumerate(edition["stories"]):
                db.execute(
                    "INSERT INTO stories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [story["id"], order, story["category"], _json(story.get("topics", [])),
                     story["place"], story["date"], story["title"], story["dek"], story["read"],
                     story["summary"], story["takeaway"], story.get("art"), _json(story.get("photo")),
                     _json(story.get("primary")), _json(story.get("gaps", []))],
                )
                for index, report in enumerate(story["reports"]):
                    db.execute("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?)", [
                        report["id"], story["id"], index, report["publisher"], report["alignment"],
                        report["focus"], _json(report),
                    ])
                for index, claim in enumerate(story.get("claims", [])):
                    db.execute("INSERT INTO claims VALUES (?, ?, ?)", [story["id"], index, _json(claim)])
                for index, perspective in enumerate(story.get("perspectives", [])):
                    db.execute("INSERT INTO perspectives VALUES (?, ?, ?)", [story["id"], index, _json(perspective)])
            for order, dimension in enumerate(lab["dimensions"]):
                db.execute("INSERT INTO lab_dimensions VALUES (?, ?, ?)", [dimension["id"], order, _json(dimension)])
            for media_id, item in enumerate(lab["media"]):
                db.execute("INSERT INTO lab_media VALUES (?, ?)", [media_id, _json(item)])
            for order, story in enumerate(lab["stories"]):
                db.execute("INSERT INTO lab_stories VALUES (?, ?, ?, ?, ?, ?, ?)", [
                    story["id"], order, story["category"], story["title"], story["short"],
                    _json(story), _json(lab["visuals"][story["id"]]),
                ])

        # Seed mock response into analyzed_queries if mock exists and table is empty
        mock_seeded = db.execute("SELECT count(*) FROM analyzed_queries").fetchone()[0]
        if not mock_seeded and MOCK_PATH.exists():
            try:
                mock_data = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
                query_str = mock_data.get("query_used", "Jantar mantar protest")
                mock_data["id"] = "cjp-dipke-detained"
                mock_data["news_group_id"] = "cjp-dipke-detained"
                mock_data["redirect_url"] = "/story.html?id=cjp-dipke-detained"
                mock_data["web_url"] = "http://localhost:8000/web/story.html?id=cjp-dipke-detained"
                mock_data["cached"] = True
                save_analyzed_query(query_str, mock_data, story_id="cjp-dipke-detained")
            except Exception:
                pass


def metadata(key: str) -> str:
    with connect() as db:
        row = db.execute("SELECT value FROM app_metadata WHERE key = ?", [key]).fetchone()
    if not row:
        defaults = {
            "edition_checked": "10 October 2026",
            "edition_through": "9 October 2026"
        }
        if key in defaults:
            return defaults[key]
        raise KeyError(key)
    return row[0]


def get_stories(category: str | None = None, topic: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM stories WHERE true"
    params: list[Any] = []
    if category:
        sql += " AND lower(category) = lower(?)"
        params.append(category)
    if topic:
        sql += " AND contains(lower(CAST(topics AS VARCHAR)), lower(?))"
        params.append(f'"{topic}"')
    if query:
        sql += """ AND (
            contains(lower(title), lower(?)) OR contains(lower(description), lower(?))
            OR contains(lower(place), lower(?)) OR contains(lower(category), lower(?))
            OR EXISTS (SELECT 1 FROM reports r WHERE r.story_id = stories.id
                       AND contains(lower(r.publisher), lower(?)))
        )"""
        params.extend([query] * 5)
    sql += " ORDER BY sort_order"
    with connect() as db:
        rows = db.execute(sql, params).fetchall()
    return [_story_row(row) for row in rows]


def get_story(story_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM stories WHERE id = ?", [story_id]).fetchone()
    return _story_row(row) if row else None


# Backward-compatible aliases
india_stories = get_stories
india_story = get_story


def _story_row(row) -> dict[str, Any]:
    story = {
        "id": row[0], "category": row[2], "topics": _decode(row[3], []), "place": row[4],
        "date": row[5], "title": row[6], "dek": row[7], "read": row[8], "summary": row[9],
        "takeaway": row[10], "art": row[11], "photo": _decode(row[12]),
        "primary": _decode(row[13]), "gaps": _decode(row[14], []),
    }
    with connect() as db:
        story["reports"] = [_decode(item[0]) for item in db.execute(
            "SELECT payload FROM reports WHERE story_id = ? ORDER BY sort_order", [story["id"]]
        ).fetchall()]
        story["claims"] = [_decode(item[0]) for item in db.execute(
            "SELECT payload FROM claims WHERE story_id = ? ORDER BY sort_order", [story["id"]]
        ).fetchall()]
        story["perspectives"] = [_decode(item[0]) for item in db.execute(
            "SELECT payload FROM perspectives WHERE story_id = ? ORDER BY sort_order", [story["id"]]
        ).fetchall()]
    return story


def story_ids(exclude: str | None = None) -> list[str]:
    sql, params = "SELECT id FROM stories", []
    if exclude:
        sql, params = sql + " WHERE id != ?", [exclude]
    with connect() as db:
        return [row[0] for row in db.execute(sql + " ORDER BY sort_order", params).fetchall()]


# Backward-compatible alias
india_story_ids = story_ids


def lab_dimensions() -> list[dict[str, Any]]:
    with connect() as db:
        return [_decode(row[0]) for row in db.execute("SELECT payload FROM lab_dimensions ORDER BY sort_order").fetchall()]


def lab_media() -> list[dict[str, Any]]:
    with connect() as db:
        return [_decode(row[0]) for row in db.execute("SELECT payload FROM lab_media ORDER BY id").fetchall()]


def lab_stories(category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    sql, params = "SELECT payload, visual FROM lab_stories WHERE true", []
    if category:
        sql += " AND lower(category) = lower(?)"
        params.append(category)
    if query:
        sql += " AND (contains(lower(title), lower(?)) OR contains(lower(description), lower(?)) OR contains(lower(CAST(payload AS VARCHAR)), lower(?)))"
        params.extend([query, query, query])
    with connect() as db:
        rows = db.execute(sql + " ORDER BY sort_order", params).fetchall()
    return [_lab_row(row) for row in rows]


def lab_story(story_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT payload, visual FROM lab_stories WHERE id = ?", [story_id]).fetchone()
    return _lab_row(row) if row else None


def _lab_row(row) -> dict[str, Any]:
    story = _decode(row[0])
    story["visual"] = _decode(row[1])
    return story


def counts() -> tuple[int, int]:
    with connect() as db:
        stories_cnt = db.execute("SELECT count(*) FROM stories").fetchone()[0]
        lab_cnt = db.execute("SELECT count(*) FROM lab_stories").fetchone()[0]
    return stories_cnt, lab_cnt


# -------------------------------------------------------------------------
# DuckDB Cache & Live Analysis Storage
# -------------------------------------------------------------------------

def get_analyzed_query(query: str) -> dict[str, Any] | None:
    key = normalize_query_key(query)
    with connect() as db:
        # 1. Check exact key or match in analyzed_queries table
        row = db.execute(
            """SELECT response FROM analyzed_queries 
               WHERE query_key = ? 
                  OR lower(search_query) = lower(?)
               LIMIT 1""",
            [key, query.strip()]
        ).fetchone()
        if row:
            data = json.loads(row[0])
            return data

        # 2. Check substring or token overlap in analyzed_queries
        row = db.execute(
            """SELECT response FROM analyzed_queries 
               WHERE contains(query_key, ?) OR contains(?, query_key)
               LIMIT 1""",
            [key, key]
        ).fetchone()
        if row:
            data = json.loads(row[0])
            return data

        # 3. Check if query matches an existing story in stories
        story_row = db.execute(
            """SELECT id FROM stories 
               WHERE lower(id) = ? 
                  OR contains(lower(title), ?) 
                  OR contains(lower(summary), ?)
               LIMIT 1""",
            [key, key, key]
        ).fetchone()
        if story_row:
            matched_story_id = story_row[0]
            # Check if there is an analyzed query associated with this story_id
            cached_row = db.execute(
                "SELECT response FROM analyzed_queries WHERE story_id = ? LIMIT 1",
                [matched_story_id]
            ).fetchone()
            if cached_row:
                return json.loads(cached_row[0])

    return None


def save_analyzed_query(query: str, response: dict[str, Any], story_id: str | None = None) -> None:
    key = normalize_query_key(query)
    sid = story_id or response.get("id") or response.get("story_id") or "story-unknown"
    now = datetime.now(timezone.utc).isoformat()
    response_json = json.dumps(response, ensure_ascii=False)
    with connect() as db:
        db.execute(
            """INSERT OR REPLACE INTO analyzed_queries (query_key, search_query, created_at, story_id, response)
               VALUES (?, ?, ?, ?, ?)""",
            [key, query, now, sid, response_json]
        )


def save_story_from_analysis(response: dict[str, Any], story_id: str, query: str) -> None:
    """Stores the newly analyzed story into stories, reports, claims, perspectives."""
    summary_data = response.get("summary", {})
    articles_data = response.get("articles", [])
    vis_data = response.get("visualization_data", {})

    category = "Politics" if vis_data.get("topic_domain", "").lower() == "political" else "General"
    title = summary_data.get("headline") or query.title()
    summary_text = summary_data.get("executive_summary") or f"Analysis for: {query}"
    dek = summary_text[:180] + ("..." if len(summary_text) > 180 else "")
    key_findings = summary_data.get("key_findings", [])
    takeaway = key_findings[0] if key_findings else "Review perspectives across sources."
    today_str = datetime.now().strftime("%d %b %Y")

    topics = [query.lower().replace(" ", "-")]
    art = "protest" if category == "Politics" else "economy"

    photo = None
    for art_item in articles_data:
        img_url = art_item.get("image_url")
        if img_url and img_url.startswith(("http://", "https://")):
            photo = {
                "url": img_url,
                "alt": f"Coverage photo for {title}",
                "credit": art_item.get("source", "News Source"),
                "source": art_item.get("url")
            }
            break

    with connect() as db:
        # Check if story already exists
        exists = db.execute("SELECT count(*) FROM stories WHERE id = ?", [story_id]).fetchone()[0]
        if exists:
            return

        order_val = db.execute("SELECT coalesce(min(sort_order), 0) - 1 FROM stories").fetchone()[0]

        db.execute(
            "INSERT INTO stories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                story_id,
                order_val,
                category,
                _json(topics),
                "India",
                today_str,
                title,
                dek,
                "3 min",
                summary_text,
                takeaway,
                art,
                _json(photo),
                None,
                _json(summary_data.get("open_questions", []))
            ]
        )

        for idx, art_item in enumerate(articles_data):
            report_id = f"{story_id}-rep-{idx+1}"
            bias_info = art_item.get("bias_info", {})
            bias_cat = bias_info.get("bias_category", "").lower()
            if "left" in bias_cat:
                alignment = "opposition"
            elif "right" in bias_cat:
                alignment = "ruling"
            elif "center" in bias_cat:
                alignment = "mixed"
            else:
                alignment = "unclear"

            rep_payload = {
                "id": report_id,
                "publisher": art_item.get("source", "Unknown Source"),
                "initials": art_item.get("source", "SRC")[:3].upper(),
                "date": today_str[:6],
                "origin": art_item.get("source", "Unknown Source"),
                "alignment": alignment,
                "focus": "context",
                "confidence": "Medium",
                "title": art_item.get("title", ""),
                "url": art_item.get("url", ""),
                "access": "Full report reviewed",
                "evidence": (art_item.get("cleaned_content") or art_item.get("snippet") or "")[:250],
                "why": bias_info.get("personal_biasing_notes") or "Automated perspective classification",
                "voice": art_item.get("source") or "Source",
                "scope": "Main event"
            }
            db.execute("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?)", [
                report_id, story_id, idx, rep_payload["publisher"], alignment, "context", _json(rep_payload)
            ])

        for idx, finding in enumerate(key_findings):
            claim_payload = {
                "status": "Reported",
                "text": finding,
                "source": f"{story_id}-rep-1" if articles_data else None
            }
            db.execute("INSERT INTO claims VALUES (?, ?, ?)", [story_id, idx, _json(claim_payload)])

        for idx, pers in enumerate(summary_data.get("perspectives", [])):
            pers_payload = {
                "title": pers.get("name", "Perspective"),
                "text": pers.get("summary", ""),
                "source": f"{story_id}-rep-1" if articles_data else None
            }
            db.execute("INSERT INTO perspectives VALUES (?, ?, ?)", [story_id, idx, _json(pers_payload)])
