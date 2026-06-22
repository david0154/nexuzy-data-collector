"""
db_cleaner.py
=============
AI-powered post-save database cleaner.

Run this AFTER all data has been collected and saved to nexuzy_travel.db.
It scans every table and:

  Step 1 ─ Garbage / junk row removal
           • name too short (< 3 chars)
           • name is purely numeric  (e.g. "123", "00")
           • name looks like a URL   (http://, www.)
           • name is a known test/placeholder string
           • name contains only special characters
           • description / address is a raw HTML fragment

  Step 2 ─ Field normalisation
           • Strip leading/trailing whitespace from all text fields
           • Fix rating > 5.0 (e.g. 45 → 4.5, 38 → 3.8)
           • Fix rating > 10 → set NULL (clearly wrong)
           • Capitalise name if it is ALL CAPS or all lowercase
           • Fill missing city from state when state is a city name
           • Remove HTML tags from description / address
           • Normalise latitude/longitude out-of-range values → NULL

  Step 3 ─ Duplicate detection + smart merge
           • Fuzzy name+city matching (token_sort_ratio ≥ 88)
           • Keeps the row with more data (more non-null fields)
           • Merges fields from the lesser row into the keeper
           • Deletes the lesser duplicate
           • Deduplicates across all pages of data (not just in-memory list)

  Step 4 ─ Low-confidence purge
           • Rows with confidence < 40 AND no city AND no address → deleted
           • (Strict threshold only for completely empty records)

  Step 5 ─ Final vacuum
           • SQLite VACUUM to reclaim space after deletions

Usage:
    from core.db_cleaner import DatabaseCleaner
    cleaner = DatabaseCleaner(db)
    report  = cleaner.run()
    print(report.summary())

    # Or run individual steps:
    cleaner.remove_garbage()
    cleaner.normalise_fields()
    cleaner.deduplicate()
    cleaner.purge_low_confidence()
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from loguru import logger

try:
    from thefuzz import fuzz
    _FUZZ_OK = True
except ImportError:
    _FUZZ_OK = False
    logger.warning("thefuzz not installed — install with: pip install thefuzz python-Levenshtein")


# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────

# Tables to clean (in this order)
TARGET_TABLES = ['hotels', 'tourist_places', 'restaurants']

# Fuzzy match threshold for duplicate detection (0-100)
DUPLICATE_THRESHOLD = 88

# Minimum confidence to keep a row that has NO city AND NO address
MIN_CONFIDENCE_BARE = 40

# Known junk/placeholder name patterns (case-insensitive)
GARBAGE_NAME_PATTERNS = [
    r'^test\b',
    r'^sample\b',
    r'^example\b',
    r'^demo\b',
    r'^placeholder',
    r'^n/a$',
    r'^na$',
    r'^none$',
    r'^null$',
    r'^unknown$',
    r'^no name',
    r'^unnamed',
    r'^untitled',
    r'^hotel\s*\d+$',           # "hotel 1", "hotel 23"
    r'^place\s*\d+$',
    r'^restaurant\s*\d+$',
    r'http[s]?://',
    r'^www\.',
    r'^<',                      # HTML fragment
    r'^\d+$',                   # purely numeric
    r'^[^\w\s]+$',              # only special chars
    r'^[a-z]$',                 # single letter
    r'^\s*$',                   # blank / whitespace only
]

_GARBAGE_RE = re.compile(
    '|'.join(GARBAGE_NAME_PATTERNS),
    re.IGNORECASE
)
_HTML_TAG_RE  = re.compile(r'<[^>]+>')
_MULTI_SPACE  = re.compile(r'\s{2,}')


# ─────────────────────────────────────────────────────────────────
# Audit report
# ─────────────────────────────────────────────────────────────────

@dataclass
class CleanReport:
    garbage_removed:     Dict[str, int] = field(default_factory=dict)
    fields_normalised:   Dict[str, int] = field(default_factory=dict)
    duplicates_merged:   Dict[str, int] = field(default_factory=dict)
    low_conf_removed:    Dict[str, int] = field(default_factory=dict)
    actions:             List[str]      = field(default_factory=list)

    def log(self, msg: str):
        self.actions.append(msg)
        logger.info(f'[DBCleaner] {msg}')

    def summary(self) -> str:
        total_removed = (
            sum(self.garbage_removed.values())
            + sum(self.duplicates_merged.values())
            + sum(self.low_conf_removed.values())
        )
        total_fixed = sum(self.fields_normalised.values())
        lines = [
            '\n╔══════════════════════════════════════════════════╗',
            '║  DATABASE CLEAN REPORT                         ║',
            '╚══════════════════════════════════════════════════╝',
            f'  Garbage rows deleted   : {sum(self.garbage_removed.values())}',
            f'  Fields normalised      : {total_fixed}',
            f'  Duplicates merged/del  : {sum(self.duplicates_merged.values())}',
            f'  Low-confidence deleted : {sum(self.low_conf_removed.values())}',
            f'  TOTAL rows removed     : {total_removed}',
            '',
            '  Per-table breakdown:',
        ]
        for tbl in TARGET_TABLES:
            g = self.garbage_removed.get(tbl, 0)
            d = self.duplicates_merged.get(tbl, 0)
            l = self.low_conf_removed.get(tbl, 0)
            f_ = self.fields_normalised.get(tbl, 0)
            lines.append(
                f'    {tbl:<20}  garbage={g}  dupes={d}  low-conf={l}  fixed={f_}'
            )
        return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    if not text:
        return text
    cleaned = _HTML_TAG_RE.sub(' ', text)
    cleaned = _MULTI_SPACE.sub(' ', cleaned).strip()
    return cleaned


def _is_garbage_name(name: str) -> bool:
    """Return True if the name is junk / placeholder."""
    if not name:
        return True
    name = name.strip()
    if len(name) < 3:
        return True
    return bool(_GARBAGE_RE.search(name))


def _fix_rating(rating) -> Optional[float]:
    """
    Normalise rating:
      - 0 – 5.0  → keep as-is
      - 5.1 – 9.9 → divide by 10 (e.g. 45 → 4.5)  only if result is in 0–5
      - > 10      → None (garbage)
    """
    if rating is None:
        return None
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return None
    if 0.0 <= r <= 5.0:
        return r
    if 5.0 < r < 100:
        fixed = round(r / 10, 1)
        if 0.0 <= fixed <= 5.0:
            return fixed
    return None   # > 100 or NaN → garbage


def _title_case_name(name: str) -> str:
    """
    Convert ALL-CAPS or all-lowercase names to Title Case.
    Leave mixed-case names alone.
    """
    if not name:
        return name
    if name.isupper() or name.islower():
        return name.title()
    return name


def _count_non_null(row: dict) -> int:
    """Count how many fields have a non-empty value."""
    return sum(
        1 for v in row.values()
        if v is not None and str(v).strip() not in ('', 'None', 'nan', 'NaN')
    )


# ─────────────────────────────────────────────────────────────────
# Main cleaner class
# ─────────────────────────────────────────────────────────────────

class DatabaseCleaner:
    """
    Post-save AI cleaner.  Pass in a core.database.Database instance.

    Example:
        cleaner = DatabaseCleaner(db)
        report  = cleaner.run()           # full pipeline
        print(report.summary())
    """

    def __init__(self, db, duplicate_threshold: int = DUPLICATE_THRESHOLD):
        self.db  = db
        self.con = db.conn
        self.threshold = duplicate_threshold

    # ───────────────────────────────────────────────────────────────
    # Full pipeline
    # ───────────────────────────────────────────────────────────────

    def run(self, on_progress=None) -> CleanReport:
        """
        Run the full cleaning pipeline in order:
          1. remove_garbage()
          2. normalise_fields()
          3. deduplicate()
          4. purge_low_confidence()
          5. vacuum()

        on_progress(step, table, done, total) called after each table per step.
        Returns a CleanReport with full audit details.
        """
        if not _FUZZ_OK:
            logger.error(
                'thefuzz is required for db_cleaner.  '
                'Run: pip install thefuzz python-Levenshtein'
            )
            return CleanReport()

        report = CleanReport()
        report.log('=== DatabaseCleaner.run() started ===')

        report.log('--- Step 1: Remove garbage rows ---')
        self.remove_garbage(report=report, on_progress=on_progress)

        report.log('--- Step 2: Normalise fields ---')
        self.normalise_fields(report=report, on_progress=on_progress)

        report.log('--- Step 3: Deduplicate ---')
        self.deduplicate(report=report, on_progress=on_progress)

        report.log('--- Step 4: Purge low-confidence bare rows ---')
        self.purge_low_confidence(report=report, on_progress=on_progress)

        report.log('--- Step 5: VACUUM ---')
        self.vacuum()

        report.log('=== DatabaseCleaner.run() complete ===')
        logger.info(report.summary())
        return report

    # ───────────────────────────────────────────────────────────────
    # Step 1 — Garbage removal
    # ───────────────────────────────────────────────────────────────

    def remove_garbage(self, report: CleanReport = None, on_progress=None):
        """Delete rows whose name is junk/garbage."""
        if report is None:
            report = CleanReport()

        for table in TARGET_TABLES:
            rows = self.con.execute(
                f'SELECT id, name FROM {table}'
            ).fetchall()
            to_delete = []

            for row in rows:
                rid, name = row['id'], row['name']
                if _is_garbage_name(name):
                    to_delete.append(rid)
                    report.log(f'[{table}] GARBAGE → delete id={rid} name="{name}"')

            if to_delete:
                placeholders = ','.join('?' * len(to_delete))
                self.con.execute(
                    f'DELETE FROM {table} WHERE id IN ({placeholders})',
                    to_delete
                )
                self.con.commit()

            report.garbage_removed[table] = len(to_delete)
            report.log(
                f'[{table}] Garbage removed: {len(to_delete)} / {len(rows)} rows'
            )
            if on_progress:
                on_progress('garbage', table, len(to_delete), len(rows))

        return report

    # ───────────────────────────────────────────────────────────────
    # Step 2 — Field normalisation
    # ───────────────────────────────────────────────────────────────

    def normalise_fields(self, report: CleanReport = None, on_progress=None):
        """Fix broken field values across all rows."""
        if report is None:
            report = CleanReport()

        for table in TARGET_TABLES:
            rows = self.con.execute(
                f'SELECT * FROM {table}'
            ).fetchall()
            fixed_count = 0

            for row in rows:
                row  = dict(row)
                rid  = row['id']
                updates: Dict = {}

                # — Clean name: HTML tags, extra spaces, case
                name = row.get('name', '') or ''
                clean_name = _strip_html(name).strip()
                clean_name = _title_case_name(clean_name)
                if clean_name != name:
                    updates['name'] = clean_name

                # — Clean description: HTML tags
                for field_name in ('description', 'address'):
                    val = row.get(field_name) or ''
                    if val:
                        cleaned = _strip_html(str(val))
                        if cleaned != val:
                            updates[field_name] = cleaned

                # — Fix rating
                raw_rating = row.get('rating')
                fixed_rating = _fix_rating(raw_rating)
                if raw_rating is not None and fixed_rating != raw_rating:
                    updates['rating'] = fixed_rating  # None means set to NULL

                # — Validate latitude (India: 8.0 – 37.0)
                lat = row.get('latitude')
                if lat is not None:
                    try:
                        lat = float(lat)
                        if not (6.0 <= lat <= 38.0):
                            updates['latitude'] = None
                    except (TypeError, ValueError):
                        updates['latitude'] = None

                # — Validate longitude (India: 68.0 – 98.0)
                lon = row.get('longitude')
                if lon is not None:
                    try:
                        lon = float(lon)
                        if not (67.0 <= lon <= 99.0):
                            updates['longitude'] = None
                    except (TypeError, ValueError):
                        updates['longitude'] = None

                # — Normalise sources: ensure it is valid JSON
                src = row.get('sources')
                if src and isinstance(src, str):
                    try:
                        json.loads(src)
                    except (json.JSONDecodeError, ValueError):
                        # Wrap plain string in a JSON list
                        updates['sources'] = json.dumps([src])

                if updates:
                    set_clause = ', '.join(f'{k} = ?' for k in updates)
                    values     = list(updates.values()) + [rid]
                    self.con.execute(
                        f'UPDATE {table} SET {set_clause} WHERE id = ?',
                        values
                    )
                    fixed_count += 1

            self.con.commit()
            report.fields_normalised[table] = fixed_count
            report.log(f'[{table}] Fields normalised: {fixed_count} rows updated')
            if on_progress:
                on_progress('normalise', table, fixed_count, len(rows))

        return report

    # ───────────────────────────────────────────────────────────────
    # Step 3 — Deduplication
    # ───────────────────────────────────────────────────────────────

    def deduplicate(self, report: CleanReport = None, on_progress=None):
        """
        Fuzzy-deduplicate every table.
        For each pair of rows where name+city are similar:
          • Keep the row with MORE non-null fields (the “richer” row)
          • Merge any extra fields from the lesser row into the keeper
          • Delete the lesser row
        """
        if report is None:
            report = CleanReport()

        for table in TARGET_TABLES:
            rows = self.con.execute(
                f'SELECT * FROM {table} ORDER BY id'
            ).fetchall()
            rows = [dict(r) for r in rows]
            total = len(rows)

            to_delete: set  = set()
            to_update: dict = {}   # id → {field: value}

            for i in range(len(rows)):
                if rows[i]['id'] in to_delete:
                    continue
                name_i = (rows[i].get('name') or '').strip().lower()
                city_i = (rows[i].get('city') or '').strip().lower()

                for j in range(i + 1, len(rows)):
                    if rows[j]['id'] in to_delete:
                        continue
                    name_j = (rows[j].get('name') or '').strip().lower()
                    city_j = (rows[j].get('city') or '').strip().lower()

                    # Name similarity
                    name_sim = fuzz.token_sort_ratio(name_i, name_j)
                    if name_sim < self.threshold:
                        continue

                    # City similarity (must match or both empty)
                    if city_i and city_j:
                        city_sim = fuzz.token_sort_ratio(city_i, city_j)
                        if city_sim < 80:
                            continue
                    elif city_i != city_j:  # one has city, other doesn't
                        continue

                    # They're duplicates — decide who to keep
                    score_i = _count_non_null(rows[i])
                    score_j = _count_non_null(rows[j])

                    if score_i >= score_j:
                        keeper, lesser = i, j
                    else:
                        keeper, lesser = j, i

                    # Merge fields from lesser into keeper
                    merged_fields = {}
                    for k, v in rows[lesser].items():
                        if k in ('id', 'created_at'):
                            continue
                        if v and not rows[keeper].get(k):
                            merged_fields[k] = v

                    # Merge source lists
                    s_k = rows[keeper].get('sources', '[]') or '[]'
                    s_l = rows[lesser].get('sources',  '[]') or '[]'
                    try:
                        s_k = json.loads(s_k) if isinstance(s_k, str) else s_k
                    except Exception:
                        s_k = [s_k]
                    try:
                        s_l = json.loads(s_l) if isinstance(s_l, str) else s_l
                    except Exception:
                        s_l = [s_l]
                    merged_sources = json.dumps(list(set((s_k or []) + (s_l or []))))
                    merged_fields['sources'] = merged_sources

                    # Keep the higher confidence
                    conf_k = rows[keeper].get('confidence', 0) or 0
                    conf_l = rows[lesser].get('confidence', 0) or 0
                    merged_fields['confidence'] = max(conf_k, conf_l)

                    keeper_id = rows[keeper]['id']
                    lesser_id = rows[lesser]['id']

                    if keeper_id not in to_update:
                        to_update[keeper_id] = {}
                    to_update[keeper_id].update(merged_fields)

                    to_delete.add(lesser_id)
                    rows[lesser]['_deleted'] = True

                    report.log(
                        f'[{table}] DUPLICATE: "{rows[lesser]["name"]}" (id={lesser_id}) '
                        f'→ merged into id={keeper_id}, deleted lesser'
                    )

            # Apply updates
            for rid, updates in to_update.items():
                if not updates:
                    continue
                set_clause = ', '.join(f'{k} = ?' for k in updates)
                values     = list(updates.values()) + [rid]
                self.con.execute(
                    f'UPDATE {table} SET {set_clause} WHERE id = ?',
                    values
                )

            # Apply deletions
            if to_delete:
                placeholders = ','.join('?' * len(to_delete))
                self.con.execute(
                    f'DELETE FROM {table} WHERE id IN ({placeholders})',
                    list(to_delete)
                )

            self.con.commit()
            report.duplicates_merged[table] = len(to_delete)
            report.log(
                f'[{table}] Deduplication: {len(to_delete)} duplicates removed '
                f'from {total} rows'
            )
            if on_progress:
                on_progress('deduplicate', table, len(to_delete), total)

        return report

    # ───────────────────────────────────────────────────────────────
    # Step 4 — Low-confidence purge
    # ───────────────────────────────────────────────────────────────

    def purge_low_confidence(
        self,
        threshold: int = MIN_CONFIDENCE_BARE,
        report: CleanReport = None,
        on_progress=None,
    ):
        """
        Delete rows that:
          - have confidence < threshold (default 40)
          - AND have no city
          - AND have no address
          - AND have no latitude
        These are completely empty skeleton records with low confidence.
        Rows with at least one location field are preserved.
        """
        if report is None:
            report = CleanReport()

        for table in TARGET_TABLES:
            result = self.con.execute(
                f"""
                DELETE FROM {table}
                WHERE (confidence IS NULL OR confidence < ?)
                  AND (city     IS NULL OR TRIM(city)    = '')
                  AND (address  IS NULL OR TRIM(address) = '')
                  AND (latitude IS NULL)
                """,
                (threshold,)
            )
            self.con.commit()
            deleted = result.rowcount
            report.low_conf_removed[table] = deleted
            report.log(f'[{table}] Low-confidence purge: {deleted} bare rows removed')
            if on_progress:
                on_progress('low_conf', table, deleted, 0)

        return report

    # ───────────────────────────────────────────────────────────────
    # Step 5 — Vacuum
    # ───────────────────────────────────────────────────────────────

    def vacuum(self):
        """Run SQLite VACUUM to reclaim disk space after deletions."""
        self.con.execute('VACUUM')
        logger.info('[DBCleaner] VACUUM complete — database compacted')

    # ───────────────────────────────────────────────────────────────
    # Utility: get a snapshot of table sizes before/after
    # ───────────────────────────────────────────────────────────────

    def table_counts(self) -> Dict[str, int]:
        """Return {table_name: row_count} for all target tables."""
        return {
            t: self.con.execute(
                f'SELECT COUNT(*) FROM {t}'
            ).fetchone()[0]
            for t in TARGET_TABLES
        }
