import sqlite3
import os
import json
from loguru import logger
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "data/nexuzy_travel.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate()           # safely adds missing columns to existing DB
        logger.info(f"Database initialized at {db_path}")

    # ------------------------------------------------------------------
    # Schema creation
    # ------------------------------------------------------------------
    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS hotels (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                city             TEXT,
                district         TEXT,
                state            TEXT DEFAULT 'West Bengal',
                address          TEXT,
                description      TEXT,
                price_min        REAL,
                price_max        REAL,
                price_per_night  TEXT,
                category         TEXT,
                amenities        TEXT,
                contact          TEXT,
                website          TEXT,
                stars            TEXT,
                latitude         REAL,
                longitude        REAL,
                rating           REAL,
                source_url       TEXT,
                -- ── Visit-time fields ──────────────────────────────
                check_in_time    TEXT,   -- e.g. "12:00 PM", "2:00 PM"
                check_out_time   TEXT,   -- e.g. "11:00 AM", "10:00 AM"
                peak_season      TEXT,   -- e.g. "October–March"
                off_season       TEXT,   -- e.g. "June–August"
                visit_months     TEXT,   -- JSON list e.g. ["Oct","Nov","Dec"]
                -- ──────────────────────────────────────────────────
                verified         INTEGER DEFAULT 0,
                confidence       INTEGER DEFAULT 0,
                sources          TEXT,
                created_at       TEXT,
                updated_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS tourist_places (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                name                 TEXT NOT NULL,
                city                 TEXT,
                district             TEXT,
                state                TEXT DEFAULT 'India',
                address              TEXT,
                description          TEXT,
                category             TEXT,
                entry_fee            TEXT,
                timings              TEXT,   -- existing: "9 AM – 5 PM"
                best_time_to_visit   TEXT,   -- existing: month range
                latitude             REAL,
                longitude            REAL,
                rating               REAL,
                source_url           TEXT,
                -- ── Visit-time fields ──────────────────────────────
                visit_duration       TEXT,   -- e.g. "2–3 hours", "Half day"
                open_days            TEXT,   -- e.g. "Mon–Sat", "All week"
                peak_season          TEXT,   -- e.g. "October–February"
                off_season           TEXT,   -- e.g. "June–August (monsoon)"
                visit_tips           TEXT,   -- e.g. "Arrive early to avoid crowds"
                crowd_level          TEXT,   -- "low" | "moderate" | "high"
                visit_months         TEXT,   -- JSON list ["Oct","Nov","Dec","Jan"]
                -- ──────────────────────────────────────────────────
                verified             INTEGER DEFAULT 0,
                confidence           INTEGER DEFAULT 0,
                sources              TEXT,
                created_at           TEXT,
                updated_at           TEXT
            );

            CREATE TABLE IF NOT EXISTS restaurants (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                city         TEXT,
                district     TEXT,
                state        TEXT,
                address      TEXT,
                description  TEXT,
                cuisine      TEXT,
                price_range  TEXT,
                contact      TEXT,
                timings      TEXT,   -- existing: "10 AM – 11 PM"
                latitude     REAL,
                longitude    REAL,
                rating       REAL,
                source_url   TEXT,
                -- ── Visit-time fields ──────────────────────────────
                open_days    TEXT,   -- e.g. "Mon–Sat", "All week"
                peak_hours   TEXT,   -- e.g. "12–2 PM, 7–10 PM"
                visit_tips   TEXT,   -- e.g. "Reserve table on weekends"
                -- ──────────────────────────────────────────────────
                verified     INTEGER DEFAULT 0,
                confidence   INTEGER DEFAULT 0,
                sources      TEXT,
                created_at   TEXT,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS cities (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                name              TEXT NOT NULL,
                district          TEXT,
                state             TEXT,
                description       TEXT,
                best_time_to_visit TEXT,
                how_to_reach      TEXT,
                latitude          REAL,
                longitude         REAL,
                -- ── Visit-time fields ──────────────────────────────
                peak_season       TEXT,   -- e.g. "October–March"
                off_season        TEXT,   -- e.g. "June–August"
                visit_months      TEXT,   -- JSON list
                avg_visit_days    TEXT,   -- e.g. "2–3 days"
                -- ──────────────────────────────────────────────────
                created_at        TEXT
            );

            CREATE TABLE IF NOT EXISTS districts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                state        TEXT,
                description  TEXT,
                tourist_info TEXT,
                headquarters TEXT,
                created_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS routes (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                from_city        TEXT,
                to_city          TEXT,
                distance_km      REAL,
                travel_time      TEXT,
                transport_modes  TEXT,
                cost_estimate    TEXT,
                description      TEXT,
                verified         INTEGER DEFAULT 0,
                created_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                city           TEXT,
                district       TEXT,
                state          TEXT,
                description    TEXT,
                category       TEXT,
                month          TEXT,
                season         TEXT,
                duration       TEXT,
                -- ── Visit-time fields ──────────────────────────────
                start_date     TEXT,   -- e.g. "2025-10-15" or "October 15"
                end_date       TEXT,   -- e.g. "2025-10-20" or "October 20"
                visit_duration TEXT,   -- e.g. "5 days", "1 week"
                -- ──────────────────────────────────────────────────
                created_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS guides (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                city        TEXT,
                district    TEXT,
                state       TEXT,
                content     TEXT,
                category    TEXT,
                source_url  TEXT,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS crawl_log (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                url               TEXT UNIQUE,
                status            TEXT,
                records_extracted INTEGER DEFAULT 0,
                crawled_at        TEXT
            );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Safe migration — adds new columns to EXISTING databases without
    # dropping any data.  Always safe to run; ALTER TABLE is a no-op if
    # the column already exists (caught and ignored).
    # ------------------------------------------------------------------
    def _migrate(self):
        migrations = [
            # (table, column, definition)
            # ── original columns (kept for older DBs) ──────────────
            ('restaurants',    'source_url',        'TEXT'),
            ('hotels',         'source_url',         'TEXT'),
            ('hotels',         'price_per_night',    'TEXT'),
            ('hotels',         'stars',              'TEXT'),
            ('tourist_places', 'source_url',         'TEXT'),

            # ── NEW: visit-time columns — tourist_places ───────────
            ('tourist_places', 'visit_duration',     'TEXT'),
            ('tourist_places', 'open_days',          'TEXT'),
            ('tourist_places', 'peak_season',        'TEXT'),
            ('tourist_places', 'off_season',         'TEXT'),
            ('tourist_places', 'visit_tips',         'TEXT'),
            ('tourist_places', 'crowd_level',        'TEXT'),
            ('tourist_places', 'visit_months',       'TEXT'),

            # ── NEW: visit-time columns — hotels ───────────────────
            ('hotels',         'check_in_time',      'TEXT'),
            ('hotels',         'check_out_time',     'TEXT'),
            ('hotels',         'peak_season',        'TEXT'),
            ('hotels',         'off_season',         'TEXT'),
            ('hotels',         'visit_months',       'TEXT'),

            # ── NEW: visit-time columns — restaurants ──────────────
            ('restaurants',    'open_days',          'TEXT'),
            ('restaurants',    'peak_hours',         'TEXT'),
            ('restaurants',    'visit_tips',         'TEXT'),

            # ── NEW: visit-time columns — events ───────────────────
            ('events',         'start_date',         'TEXT'),
            ('events',         'end_date',           'TEXT'),
            ('events',         'visit_duration',     'TEXT'),

            # ── NEW: visit-time columns — cities ───────────────────
            ('cities',         'peak_season',        'TEXT'),
            ('cities',         'off_season',         'TEXT'),
            ('cities',         'visit_months',       'TEXT'),
            ('cities',         'avg_visit_days',     'TEXT'),
        ]
        for table, col, defn in migrations:
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
                self.conn.commit()
                logger.info(f"DB migration: added {table}.{col}")
            except sqlite3.OperationalError:
                pass   # column already exists — that's fine

    # ------------------------------------------------------------------
    # Safe insert  — strips any key that is NOT a real column in the
    # target table so we never get 'no column named X' errors again,
    # even when portal_fetcher or future scrapers add extra fields.
    # ------------------------------------------------------------------
    def _safe_insert(self, table: str, data: dict) -> int:
        now = datetime.now().isoformat()
        data.setdefault('created_at', now)
        if table in ('hotels', 'tourist_places', 'restaurants'):
            data.setdefault('updated_at', now)
        if isinstance(data.get('sources'), list):
            data['sources'] = json.dumps(data['sources'])
        if isinstance(data.get('amenities'), list):
            data['amenities'] = json.dumps(data['amenities'])
        # visit_months is stored as JSON list
        if isinstance(data.get('visit_months'), list):
            data['visit_months'] = json.dumps(data['visit_months'])

        # Discover real columns from the live schema
        real_cols = {
            row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        # Remove keys that don't exist in the table
        filtered = {k: v for k, v in data.items() if k in real_cols}
        if not filtered:
            raise ValueError(f"insert_safe: no valid keys for table '{table}'")

        cols         = ', '.join(filtered.keys())
        placeholders = ', '.join(['?' for _ in filtered])
        sql          = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        cur          = self.conn.execute(sql, list(filtered.values()))
        self.conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------
    # Public insert methods (all delegate to _safe_insert)
    # ------------------------------------------------------------------
    def insert_hotel(self, data: dict) -> int:
        return self._safe_insert('hotels', data)

    def insert_tourist_place(self, data: dict) -> int:
        return self._safe_insert('tourist_places', data)

    def insert_restaurant(self, data: dict) -> int:
        return self._safe_insert('restaurants', data)

    def insert_route(self, data: dict) -> int:
        return self._safe_insert('routes', data)

    def insert_event(self, data: dict) -> int:
        return self._safe_insert('events', data)

    def insert_guide(self, data: dict) -> int:
        return self._safe_insert('guides', data)

    def insert_batch(self, table: str, records: list) -> int:
        """Insert multiple records into a table at once"""
        if not records:
            return 0
        
        inserted = 0
        for record in records:
            try:
                if table == 'hotels':
                    self.insert_hotel(record)
                elif table == 'tourist_places':
                    self.insert_tourist_place(record)
                elif table == 'restaurants':
                    self.insert_restaurant(record)
                elif table == 'routes':
                    self.insert_route(record)
                elif table == 'events':
                    self.insert_event(record)
                elif table == 'guides':
                    self.insert_guide(record)
                else:
                    self._safe_insert(table, record)
                inserted += 1
            except Exception as e:
                logger.warning(f"Failed to insert record into {table}: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Inserted {inserted}/{len(records)} records into {table}")
        return inserted

    # ------------------------------------------------------------------
    # URL / crawl helpers
    # ------------------------------------------------------------------
    def is_url_crawled(self, url: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM crawl_log WHERE url = ? AND status = 'success'",
            (url,)
        ).fetchone()
        return row is not None

    def get_crawled_urls(self) -> set:
        rows = self.conn.execute(
            "SELECT url FROM crawl_log WHERE status = 'success'"
        ).fetchall()
        return {r['url'] for r in rows}

    def get_existing_names(self, table: str, col: str = 'name') -> list:
        rows = self.conn.execute(
            f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL"
        ).fetchall()
        return [r[col] for r in rows]

    def log_crawl(self, url: str, status: str, records: int = 0):
        self.conn.execute(
            "INSERT OR REPLACE INTO crawl_log (url, status, records_extracted, crawled_at) "
            "VALUES (?, ?, ?, ?)",
            (url, status, records, datetime.now().isoformat())
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        tables = ['hotels', 'tourist_places', 'restaurants', 'routes', 'events', 'guides', 'crawl_log']
        stats = {}
        for t in tables:
            row = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
            stats[t] = row['cnt']
        return stats

    def search(self, table: str, keyword: str, limit: int = 50) -> list:
        query = (
            f"SELECT * FROM {table} "
            f"WHERE name LIKE ? OR description LIKE ? OR city LIKE ? "
            f"LIMIT {limit}"
        )
        rows = self.conn.execute(
            query, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all(self, table: str, limit: int = 1000, offset: int = 0) -> list:
        rows = self.conn.execute(
            f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()