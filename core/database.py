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
        self._migrate()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS hotels (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                city             TEXT,
                state            TEXT,
                address          TEXT,
                description      TEXT,
                stars            TEXT,
                rating           REAL,
                price_per_night  TEXT,
                amenities        TEXT,
                contact          TEXT,
                website          TEXT,
                latitude         REAL,
                longitude        REAL,
                category         TEXT,
                source_url       TEXT,
                sources          TEXT,
                source_type      TEXT DEFAULT 'scraped',
                source_platform  TEXT,
                review_count     INTEGER,
                created_at       TEXT,
                updated_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS tourist_places (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL,
                city                TEXT,
                state               TEXT,
                district            TEXT,
                address             TEXT,
                category            TEXT,
                description         TEXT,
                entry_fee           TEXT,
                timings             TEXT,
                best_time_to_visit  TEXT,
                rating              REAL,
                latitude            REAL,
                longitude           REAL,
                visit_duration      TEXT,
                peak_season         TEXT,
                crowd_level         TEXT,
                accessibility       TEXT,
                source_url          TEXT,
                sources             TEXT,
                source_type         TEXT DEFAULT 'scraped',
                created_at          TEXT,
                updated_at          TEXT
            );

            CREATE TABLE IF NOT EXISTS restaurants (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                city         TEXT,
                state        TEXT,
                address      TEXT,
                cuisine      TEXT,
                rating       REAL,
                price_range  TEXT,
                latitude     REAL,
                longitude    REAL,
                contact      TEXT,
                website      TEXT,
                source_url   TEXT,
                sources      TEXT,
                source_type  TEXT DEFAULT 'scraped',
                created_at   TEXT,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS routes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                route_type     TEXT,
                origin         TEXT,
                destination    TEXT,
                distance_km    REAL,
                duration_hrs   REAL,
                description    TEXT,
                source_url     TEXT,
                sources        TEXT,
                created_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS flights (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                airline         TEXT,
                name            TEXT NOT NULL,
                origin          TEXT,
                destination     TEXT,
                route_name      TEXT,
                departure_time  TEXT,
                arrival_time    TEXT,
                duration        TEXT,
                fare            TEXT,
                description     TEXT,
                source_url      TEXT,
                sources         TEXT,
                created_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                city         TEXT,
                state        TEXT,
                date         TEXT,
                venue        TEXT,
                description  TEXT,
                category     TEXT,
                source_url   TEXT,
                sources      TEXT,
                created_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS guides (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                city         TEXT,
                state        TEXT,
                content      TEXT,
                category     TEXT,
                source_url   TEXT,
                sources      TEXT,
                created_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS crawl_log (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                url                TEXT UNIQUE,
                status             TEXT,
                records_extracted  INTEGER DEFAULT 0,
                crawled_at         TEXT
            );
        """)
        self.conn.commit()

    def _migrate(self):
        """Add columns introduced after initial schema creation."""
        migrations = [
            ('hotels',         'source_url',         'TEXT'),
            ('hotels',         'price_per_night',    'TEXT'),
            ('hotels',         'stars',              'TEXT'),
            ('hotels',         'source_type',        'TEXT DEFAULT \'scraped\''),
            ('hotels',         'source_platform',    'TEXT'),
            ('hotels',         'review_count',       'INTEGER'),
            ('tourist_places', 'source_url',         'TEXT'),
            ('tourist_places', 'source_type',        'TEXT DEFAULT \'scraped\''),
            ('tourist_places', 'visit_duration',     'TEXT'),
            ('tourist_places', 'peak_season',        'TEXT'),
            ('tourist_places', 'crowd_level',        'TEXT'),
            ('tourist_places', 'accessibility',      'TEXT'),
            ('restaurants',    'source_url',         'TEXT'),
            ('restaurants',    'source_type',        'TEXT DEFAULT \'scraped\''),
            # ── NEW: visit-time columns — hotels ───────────────────────────────────
            ('hotels',         'check_in_time',      'TEXT'),
            ('hotels',         'check_out_time',     'TEXT'),
            ('hotels',         'peak_season',        'TEXT'),
            ('hotels',         'off_season',         'TEXT'),
            ('hotels',         'visit_months',       'TEXT'),
            # ── NEW: visit-time columns — tourist_places ───────────────────────────
            ('tourist_places', 'off_season',         'TEXT'),
            ('tourist_places', 'visit_months',       'TEXT'),
            # ── flights table extra columns ─────────────────────────────────────────────
            ('flights',        'source_url',         'TEXT'),
            ('flights',        'source_type',        'TEXT DEFAULT \'scraped\''),
        ]
        for table, col, col_type in migrations:
            try:
                self.conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
                self.conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists

    # ------------------------------------------------------------------
    # Core insert helper
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

        # Guard NOT NULL name — skip rows where name is missing/blank/NaN
        _NOT_NULL_NAME_TABLES = {'hotels', 'tourist_places', 'restaurants',
                                  'routes', 'events', 'flights'}
        if table in _NOT_NULL_NAME_TABLES:
            _name_val = filtered.get('name', None)
            if not _name_val or str(_name_val).strip() in ('', 'nan', 'NaN', 'None', 'null'):
                raise ValueError(
                    f"insert_safe: skipped row in '{table}' — name is empty/NULL"
                )

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

        return inserted

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        stats = {}
        tables = ['hotels', 'tourist_places', 'restaurants', 'routes', 'events', 'guides', 'crawl_log']
        for table in tables:
            try:
                row = self.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()
                stats[table] = row[0] if row else 0
            except Exception:
                stats[table] = 0
        return stats

    def search(self, query: str, table: str = 'tourist_places', limit: int = 20) -> list:
        try:
            rows = self.conn.execute(
                f"SELECT * FROM {table} "
                f"WHERE name LIKE ? OR description LIKE ? OR city LIKE ? "
                f"LIMIT ?",
                (f'%{query}%', f'%{query}%', f'%{query}%', limit)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f'Search failed: {e}')
            return []

    def log_crawl(self, url: str, status: str, records: int = 0):
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO crawl_log (url, status, records_extracted, crawled_at) "
                "VALUES (?, ?, ?, ?)",
                (url, status, records, datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f'log_crawl failed: {e}')

    def get_existing_names(self, table: str, col: str = 'name') -> list:
        try:
            rows = self.conn.execute(
                f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL"
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
