"""Persistent memory layer - SQLite-backed state for the agent swarm.

Tracks published content, keyword positions, topical clusters, and
competitive scan history so agents get smarter over time.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path("output/memory.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS published_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            primary_keyword TEXT,
            url TEXT,
            contentful_entry_id TEXT,
            cluster_name TEXT,
            word_count INTEGER,
            published_at TEXT NOT NULL DEFAULT (datetime('now')),
            meta_description TEXT
        );
        CREATE TABLE IF NOT EXISTS keyword_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            position INTEGER,
            volume INTEGER,
            traffic INTEGER,
            url TEXT,
            scanned_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            theme TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS cluster_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_name TEXT NOT NULL,
            keyword TEXT NOT NULL,
            volume INTEGER,
            difficulty INTEGER,
            status TEXT DEFAULT 'opportunity',
            UNIQUE(cluster_name, keyword)
        );
        CREATE TABLE IF NOT EXISTS scout_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date TEXT NOT NULL,
            dwc_organic_keywords INTEGER,
            dwc_organic_traffic INTEGER,
            clusters_found INTEGER,
            top_pick_keyword TEXT,
            top_pick_volume INTEGER,
            report_json TEXT,
            scanned_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS competitor_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            traffic INTEGER,
            keywords INTEGER,
            domain_rating REAL,
            scanned_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def get_published_content() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT title, slug, primary_keyword, url, cluster_name, published_at "
            "FROM published_content ORDER BY published_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def record_published_content(
    title: str, slug: str, primary_keyword: str, url: str = "",
    contentful_entry_id: str = "", cluster_name: str = "",
    word_count: int = 0, meta_description: str = "",
) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO published_content "
            "(title, slug, primary_keyword, url, contentful_entry_id, cluster_name, word_count, meta_description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, slug, primary_keyword, url, contentful_entry_id, cluster_name, word_count, meta_description),
        )
        conn.commit()
    return {"status": "recorded", "slug": slug}


def get_keyword_positions(keyword: str = "", limit: int = 50) -> list[dict]:
    with _connect() as conn:
        if keyword:
            rows = conn.execute(
                "SELECT keyword, position, volume, traffic, url, scanned_at "
                "FROM keyword_positions WHERE keyword = ? ORDER BY scanned_at DESC LIMIT ?",
                (keyword, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT keyword, position, volume, traffic, url, scanned_at "
                "FROM keyword_positions ORDER BY scanned_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def record_keyword_positions(keywords: list[dict]) -> dict:
    with _connect() as conn:
        for kw in keywords:
            conn.execute(
                "INSERT INTO keyword_positions (keyword, position, volume, traffic, url) VALUES (?, ?, ?, ?, ?)",
                (kw["keyword"], kw.get("position"), kw.get("volume"), kw.get("traffic"), kw.get("url", "")),
            )
        conn.commit()
    return {"status": "recorded", "count": len(keywords)}


def get_cluster_map() -> list[dict]:
    with _connect() as conn:
        clusters_list = conn.execute("SELECT name, theme, created_at, updated_at FROM clusters ORDER BY name").fetchall()
        result = []
        for c in clusters_list:
            kws = conn.execute(
                "SELECT keyword, volume, difficulty, status FROM cluster_keywords WHERE cluster_name = ?",
                (c["name"],),
            ).fetchall()
            published = conn.execute(
                "SELECT title, slug, primary_keyword FROM published_content WHERE cluster_name = ?",
                (c["name"],),
            ).fetchall()
            result.append({**dict(c), "keywords": [dict(k) for k in kws], "published_articles": [dict(p) for p in published]})
    return result


def update_cluster(name: str, theme: str = "", keywords: list[dict] = None) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO clusters (name, theme) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET theme = COALESCE(NULLIF(?, ''), theme), updated_at = datetime('now')",
            (name, theme, theme),
        )
        if keywords:
            for kw in keywords:
                conn.execute(
                    "INSERT OR REPLACE INTO cluster_keywords (cluster_name, keyword, volume, difficulty, status) VALUES (?, ?, ?, ?, ?)",
                    (name, kw["keyword"], kw.get("volume"), kw.get("difficulty"), kw.get("status", "opportunity")),
                )
        conn.commit()
    return {"status": "updated", "cluster": name}


def record_scout_scan(report: dict) -> dict:
    metrics = report.get("dwc_current_metrics", {})
    top_pick = report.get("top_pick", {})
    with _connect() as conn:
        conn.execute(
            "INSERT INTO scout_scans (scan_date, dwc_organic_keywords, dwc_organic_traffic, clusters_found, top_pick_keyword, top_pick_volume, report_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (report.get("scan_date", datetime.now().isoformat()), metrics.get("organic_keywords"), metrics.get("organic_traffic"),
             len(report.get("clusters", [])), top_pick.get("primary_keyword"), top_pick.get("volume"), json.dumps(report)),
        )
        conn.commit()
    return {"status": "recorded"}


def get_recent_scans(limit: int = 7) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT scan_date, dwc_organic_keywords, dwc_organic_traffic, clusters_found, top_pick_keyword, top_pick_volume, scanned_at "
            "FROM scout_scans ORDER BY scanned_at DESC LIMIT ?", (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def record_competitor_snapshot(domain: str, traffic: int, keywords: int, domain_rating: float) -> dict:
    with _connect() as conn:
        conn.execute("INSERT INTO competitor_snapshots (domain, traffic, keywords, domain_rating) VALUES (?, ?, ?, ?)",
                     (domain, traffic, keywords, domain_rating))
        conn.commit()
    return {"status": "recorded", "domain": domain}


def get_competitor_history(domain: str, limit: int = 30) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT domain, traffic, keywords, domain_rating, scanned_at FROM competitor_snapshots WHERE domain = ? ORDER BY scanned_at DESC LIMIT ?",
            (domain, limit),
        ).fetchall()
    return [dict(r) for r in rows]
