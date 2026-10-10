from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "nonpartisan.duckdb"
SEED_PATH = BASE_DIR / "data" / "content.json"


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def initialize() -> None:
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL);
            CREATE TABLE IF NOT EXISTS india_stories (
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
        """)
        seeded = db.execute("SELECT count(*) FROM india_stories").fetchone()[0]
        if seeded:
            return
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        edition, lab = seed["edition"], seed["lab"]
        db.executemany("INSERT INTO app_metadata VALUES (?, ?)", [
            ("edition_checked", edition["checked"]),
            ("edition_through", edition["through"]),
        ])
        for order, story in enumerate(edition["stories"]):
            db.execute(
                "INSERT INTO india_stories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(value: str | None, fallback=None):
    return fallback if value is None else json.loads(value)


def metadata(key: str) -> str:
    with connect() as db:
        row = db.execute("SELECT value FROM app_metadata WHERE key = ?", [key]).fetchone()
    if not row:
        raise KeyError(key)
    return row[0]


def india_stories(category: str | None = None, topic: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM india_stories WHERE true"
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
            OR EXISTS (SELECT 1 FROM reports r WHERE r.story_id = india_stories.id
                       AND contains(lower(r.publisher), lower(?)))
        )"""
        params.extend([query] * 5)
    sql += " ORDER BY sort_order"
    with connect() as db:
        rows = db.execute(sql, params).fetchall()
    return [_india_row(row) for row in rows]


def india_story(story_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM india_stories WHERE id = ?", [story_id]).fetchone()
    return _india_row(row) if row else None


def _india_row(row) -> dict[str, Any]:
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


def india_story_ids(exclude: str | None = None) -> list[str]:
    sql, params = "SELECT id FROM india_stories", []
    if exclude:
        sql, params = sql + " WHERE id != ?", [exclude]
    with connect() as db:
        return [row[0] for row in db.execute(sql + " ORDER BY sort_order", params).fetchall()]


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
        india = db.execute("SELECT count(*) FROM india_stories").fetchone()[0]
        lab = db.execute("SELECT count(*) FROM lab_stories").fetchone()[0]
    return india, lab
