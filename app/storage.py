from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("GOMBO_DB", ROOT / "data" / "opportunities_v6.sqlite"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                organization TEXT,
                source TEXT,
                location TEXT,
                remote_type TEXT,
                opportunity_type TEXT,
                track TEXT NOT NULL DEFAULT 'emploi-data',
                domain TEXT NOT NULL DEFAULT 'data-bi',
                deadline TEXT,
                posted_at TEXT,
                discovered_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'nouveau',
                summary TEXT,
                description TEXT,
                keywords_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                source_count INTEGER NOT NULL DEFAULT 0,
                found_count INTEGER NOT NULL DEFAULT 0,
                saved_count INTEGER NOT NULL DEFAULT 0,
                errors_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )


def start_scan(source_count: int) -> int:
    init_db()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO scan_runs (started_at, source_count) VALUES (?, ?)",
            (now_iso(), source_count),
        )
        return int(cur.lastrowid)


def finish_scan(scan_id: int, found_count: int, saved_count: int, errors: list[str]) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE scan_runs
            SET finished_at = ?, found_count = ?, saved_count = ?, errors_json = ?
            WHERE id = ?
            """,
            (now_iso(), found_count, saved_count, json.dumps(errors, ensure_ascii=True), scan_id),
        )


def upsert_opportunities(items: list[dict[str, Any]]) -> int:
    init_db()
    saved = 0
    timestamp = now_iso()
    with connect() as conn:
        for item in items:
            if not item.get("url") or not item.get("title"):
                continue
            conn.execute(
                """
                INSERT INTO opportunities (
                    url, title, organization, source, location, remote_type, opportunity_type, track, domain,
                    deadline, posted_at, discovered_at, last_seen_at, score, summary,
                    description, keywords_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    organization = excluded.organization,
                    source = excluded.source,
                    location = excluded.location,
                    remote_type = excluded.remote_type,
                    opportunity_type = excluded.opportunity_type,
                    track = excluded.track,
                    domain = excluded.domain,
                    deadline = excluded.deadline,
                    posted_at = excluded.posted_at,
                    last_seen_at = excluded.last_seen_at,
                    score = excluded.score,
                    summary = excluded.summary,
                    description = excluded.description,
                    keywords_json = excluded.keywords_json
                """,
                (
                    item.get("url"),
                    item.get("title"),
                    item.get("organization"),
                    item.get("source"),
                    item.get("location"),
                    item.get("remote_type"),
                    item.get("opportunity_type"),
                    item.get("track") or "emploi-data",
                    item.get("domain") or "data-bi",
                    item.get("deadline"),
                    item.get("posted_at"),
                    timestamp,
                    timestamp,
                    int(item.get("score") or 0),
                    item.get("summary"),
                    item.get("description"),
                    json.dumps(item.get("keywords") or [], ensure_ascii=True),
                ),
            )
            saved += 1
    return saved


def list_opportunities(
    status: str | None = None,
    track: str | None = None,
    domain: str | None = None,
    min_score: int = 0,
    query: str | None = None,
    limit: int = 300,
) -> list[dict[str, Any]]:
    init_db()
    where = ["score >= ?"]
    params: list[Any] = [min_score]
    if status and status != "all":
        where.append("status = ?")
        params.append(status)
    if track and track != "all":
        where.append("track = ?")
        params.append(track)
    if domain and domain != "all":
        where.append("domain = ?")
        params.append(domain)
    if query:
        where.append("(title LIKE ? OR organization LIKE ? OR description LIKE ? OR location LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like, like])
    params.append(limit)
    sql = f"""
        SELECT *
        FROM opportunities
        WHERE {' AND '.join(where)}
        ORDER BY
            CASE status
                WHEN 'a-postuler' THEN 1
                WHEN 'nouveau' THEN 2
                WHEN 'postule' THEN 3
                ELSE 4
            END,
            score DESC,
            COALESCE(deadline, '9999-12-31') ASC,
            last_seen_at DESC
        LIMIT ?
    """
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(row) for row in rows]


def update_status(item_id: int, status: str) -> dict[str, Any] | None:
    init_db()
    allowed = {"nouveau", "a-postuler", "postule", "ignore"}
    if status not in allowed:
        raise ValueError("Invalid status")
    with connect() as conn:
        conn.execute("UPDATE opportunities SET status = ? WHERE id = ?", (status, item_id))
        row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict(row) if row else None


def recent_scans(limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [row_to_dict(row) for row in rows]


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "keywords_json" in data:
        data["keywords"] = json.loads(data.pop("keywords_json") or "[]")
    if "errors_json" in data:
        data["errors"] = json.loads(data.pop("errors_json") or "[]")
    return data
