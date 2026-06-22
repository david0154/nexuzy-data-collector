"""
duplicate_guard.py  —  TinyLlama-1.1B-Chat-v1.0 Powered
═══════════════════════════════════════════════════════════
Automatic 3-tier duplicate detection for Nexuzy Data Collector.

Tier 1  ▸  Exact key-column match          (instant SQL WHERE)
Tier 2  ▸  SHA-256 full-row hash           (catches bit-for-bit duplicates)
Tier 3  ▸  TinyLlama-1.1B semantic score   (catches near-duplicates:
            same hotel spelled differently, same place with extra spaces, etc.)

TinyLlama is loaded ONCE, shared across all calls (lazy singleton).
Falls back gracefully if the model is not yet downloaded.

Public API
──────────
  is_duplicate(conn, table, row, key_cols)  -> bool
      Call before every INSERT.  Runs all 3 tiers automatically.

  scan_all_tables(db_path, ai_verify=True)  -> dict[table, DupReport]
      Full scan with AI verification of near-duplicates.

  remove_duplicates(db_path)               -> dict[table, int]
      Delete confirmed duplicate rows, keep lowest rowid.

  warm_up_model()
      Pre-load TinyLlama so first INSERT isn't slow.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)

# ── Public exports (fixes 'cannot import name DupReport' on stale .pyc) ──────
__all__ = [
    "DupReport",
    "is_duplicate",
    "scan_all_tables",
    "remove_duplicates",
    "warm_up_model",
    "row_hash_value",
]

# ── TinyLlama model path (matches ModelDownloadTab convention) ────────────────
_MODEL_DIRS = [
    Path("models/tinyllama"),
    Path("models/TinyLlama-1.1B-Chat-v1.0"),
    Path("models"),
]
_MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Semantic similarity threshold: 0.0 = totally different, 1.0 = identical
SEMANTIC_THRESHOLD = 0.82

# Max characters sent to TinyLlama per row representation
_MAX_ROW_CHARS = 400

# ── Lazy singleton ────────────────────────────────────────────────────────────
_model_lock = threading.Lock()
_pipeline = None
_model_available = None   # None=unknown, True=loaded, False=unavailable


# ══════════════════════════════════════════════════════════════════════════════
# DupReport — defined at module top-level so 'from duplicate_guard import DupReport'
# always works regardless of .pyc cache state.
# ══════════════════════════════════════════════════════════════════════════════

class DupReport(NamedTuple):
    """Result of scanning one table for duplicates."""
    exact_dups:    int   # bit-for-bit duplicate rows
    semantic_dups: int   # near-duplicates caught by TinyLlama
    total:         int   # exact_dups + semantic_dups


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def warm_up_model() -> bool:
    """Pre-load TinyLlama.  Call once at app startup (non-blocking via thread)."""
    threading.Thread(target=_get_pipeline, daemon=True).start()
    return True


def is_duplicate(
    conn: sqlite3.Connection,
    table: str,
    row: dict[str, Any],
    key_cols: list[str] | None = None,
) -> bool:
    """
    Returns True if *row* is a duplicate of any existing row in *table*.
    Runs all 3 tiers automatically.
    """
    if _exact_key_match(conn, table, row, key_cols):
        logger.debug("[DupGuard] Tier-1 exact key match in '%s'", table)
        return True
    if _hash_match(conn, table, row):
        logger.debug("[DupGuard] Tier-2 hash match in '%s'", table)
        return True
    candidate = _fetch_best_candidate(conn, table, row, key_cols)
    if candidate and _semantic_duplicate(row, candidate):
        logger.debug("[DupGuard] Tier-3 TinyLlama semantic match in '%s'", table)
        return True
    return False


def scan_all_tables(
    db_path: str | Path,
    ai_verify: bool = True,
) -> dict[str, DupReport]:
    """
    Scan every table in *db_path* for duplicates.
    Returns {table_name: DupReport}.
    """
    results: dict[str, DupReport] = {}
    db_path = Path(db_path)
    if not db_path.exists():
        logger.warning("[DupGuard] DB not found: %s", db_path)
        return results

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for tbl in tables:
            exact    = _count_exact_duplicates(conn, tbl)
            semantic = _count_semantic_duplicates(conn, tbl) if ai_verify else 0
            results[tbl] = DupReport(
                exact_dups=exact,
                semantic_dups=semantic,
                total=exact + semantic,
            )
            logger.info(
                "[DupGuard] %s → exact=%d  semantic=%d", tbl, exact, semantic
            )
    finally:
        conn.close()

    return results


def remove_duplicates(db_path: str | Path) -> dict[str, int]:
    """Delete exact duplicate rows (keeps lowest rowid). Returns {table: rows_deleted}."""
    removed: dict[str, int] = {}
    db_path = Path(db_path)
    if not db_path.exists():
        return removed
    conn = sqlite3.connect(db_path)
    try:
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for tbl in tables:
            removed[tbl] = _remove_exact_dups(conn, tbl)
        conn.commit()
    finally:
        conn.close()
    return removed


def row_hash_value(row: dict[str, Any]) -> str:
    """SHA-256 fingerprint of a row dict."""
    return _row_hash(row)


# ══════════════════════════════════════════════════════════════════════════════
# TinyLlama integration
# ══════════════════════════════════════════════════════════════════════════════

def _get_pipeline():
    global _pipeline, _model_available
    with _model_lock:
        if _model_available is True:
            return _pipeline
        if _model_available is False:
            return None
        model_path = _find_local_model()
        source = model_path or _MODEL_ID
        try:
            from transformers import pipeline as hf_pipeline
            logger.info("[DupGuard] Loading TinyLlama from: %s", source)
            _pipeline = hf_pipeline(
                "text-generation",
                model=str(source),
                tokenizer=str(source),
                max_new_tokens=16,
                do_sample=False,
                temperature=1.0,
                device_map="auto",
            )
            _model_available = True
            logger.info("[DupGuard] TinyLlama ready ✓")
        except Exception as exc:
            logger.warning("[DupGuard] TinyLlama unavailable (%s) — AI tier skipped", exc)
            _model_available = False
            _pipeline = None
        return _pipeline


def _find_local_model() -> Path | None:
    for d in _MODEL_DIRS:
        if d.exists() and any(d.iterdir()):
            return d
    return None


def _semantic_duplicate(row_a: dict[str, Any], row_b: dict[str, Any]) -> bool:
    pipe = _get_pipeline()
    if pipe is None:
        return False
    text_a = _row_to_text(row_a)
    text_b = _row_to_text(row_b)
    prompt = (
        "<|system|>\n"
        "You are a data quality assistant. Decide if two dataset rows represent "
        "the SAME real-world entity (same hotel, place, train, etc.) even if "
        "they are worded slightly differently.\n"
        "Respond with ONLY a JSON object: {\"same\": true/false, \"score\": 0.0-1.0}\n"
        "<|user|>\n"
        f"Row A: {text_a}\n\n"
        f"Row B: {text_b}\n"
        "<|assistant|>\n"
    )
    try:
        output = pipe(prompt)[0]["generated_text"]
        reply  = output.split("<|assistant|>")[-1].strip()
        start  = reply.find("{")
        end    = reply.rfind("}") + 1
        if start == -1 or end == 0:
            return False
        data  = json.loads(reply[start:end])
        score = float(data.get("score", 0.0))
        same  = bool(data.get("same", False))
        logger.debug("[DupGuard] TinyLlama score=%.3f same=%s", score, same)
        return same and score >= SEMANTIC_THRESHOLD
    except Exception as exc:
        logger.debug("[DupGuard] TinyLlama parse error: %s", exc)
        return False


def _row_to_text(row: dict[str, Any]) -> str:
    parts = [f"{k}: {v}" for k, v in row.items() if v is not None and str(v).strip()]
    return ", ".join(parts)[:_MAX_ROW_CHARS]


# ══════════════════════════════════════════════════════════════════════════════
# SQL / hashing helpers
# ══════════════════════════════════════════════════════════════════════════════

def _row_hash(row: dict[str, Any]) -> str:
    canonical = "|".join(f"{k}={v}" for k, v in sorted(row.items()))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
    return [r[1] for r in rows]


def _exact_key_match(
    conn: sqlite3.Connection,
    table: str,
    row: dict[str, Any],
    key_cols: list[str] | None,
) -> bool:
    if not key_cols:
        return False
    available = [c for c in key_cols if c in row]
    if not available:
        return False
    where = " AND ".join(f"[{c}] = ?" for c in available)
    vals  = [row[c] for c in available]
    try:
        cur = conn.execute(f"SELECT 1 FROM [{table}] WHERE {where} LIMIT 1", vals)
        return cur.fetchone() is not None
    except sqlite3.OperationalError:
        return False


def _hash_match(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> bool:
    h = _row_hash(row)
    try:
        cur = conn.execute(
            f"SELECT 1 FROM [{table}] WHERE _row_hash = ? LIMIT 1", (h,)
        )
        return cur.fetchone() is not None
    except sqlite3.OperationalError:
        return False


def _fetch_best_candidate(
    conn: sqlite3.Connection,
    table: str,
    row: dict[str, Any],
    key_cols: list[str] | None,
) -> dict[str, Any] | None:
    try:
        if key_cols:
            for col in key_cols:
                if col in row and row[col]:
                    val = str(row[col])[:60]
                    cur = conn.execute(
                        f"SELECT * FROM [{table}] WHERE [{col}] LIKE ? LIMIT 1",
                        (f"%{val[:20]}%",),
                    )
                    candidate = cur.fetchone()
                    if candidate:
                        return dict(candidate)
        cur = conn.execute(f"SELECT * FROM [{table}] ORDER BY rowid DESC LIMIT 1")
        r = cur.fetchone()
        return dict(r) if r else None
    except sqlite3.OperationalError:
        return None


def _count_exact_duplicates(conn: sqlite3.Connection, table: str) -> int:
    cols = _get_columns(conn, table)
    if not cols:
        return 0
    col_list = ", ".join(f"[{c}]" for c in cols)
    try:
        sql = (
            f"SELECT COUNT(*) FROM ("
            f"  SELECT {col_list}, COUNT(*) AS cnt"
            f"  FROM [{table}]"
            f"  GROUP BY {col_list}"
            f"  HAVING cnt > 1"
            f")"
        )
        row = conn.execute(sql).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _count_semantic_duplicates(conn: sqlite3.Connection, table: str) -> int:
    pipe = _get_pipeline()
    if pipe is None:
        return 0
    try:
        rows = conn.execute(f"SELECT * FROM [{table}] LIMIT 200").fetchall()
    except sqlite3.OperationalError:
        return 0
    if len(rows) < 2:
        return 0
    dicts   = [dict(r) for r in rows]
    sem_dups = 0
    for i in range(len(dicts) - 1):
        a, b = dicts[i], dicts[i + 1]
        if _row_hash(a) == _row_hash(b):
            continue
        if _semantic_duplicate(a, b):
            sem_dups += 1
    return sem_dups


def _remove_exact_dups(conn: sqlite3.Connection, table: str) -> int:
    cols = _get_columns(conn, table)
    if not cols:
        return 0
    col_list = ", ".join(f"[{c}]" for c in cols)
    try:
        before = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        conn.execute(
            f"DELETE FROM [{table}] WHERE rowid NOT IN ("
            f"  SELECT MIN(rowid) FROM [{table}] GROUP BY {col_list}"
            f")"
        )
        after = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        return before - after
    except sqlite3.OperationalError:
        return 0