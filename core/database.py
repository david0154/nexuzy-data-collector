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
                check_in_time    TEXT,
                check_out_time   TEXT,
                peak_season      TEXT,
                off_season       TEXT,
                visit_months     TEXT,
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
                timings              TEXT,
                best_time_to_visit   TEXT,
                latitude             REAL,
                longitude            REAL,
                rating               REAL,
                source_url           TEXT,
                visit_duration       TEXT,
                open_days            TEXT,
                peak_season          TEXT,
                off_season           TEXT,
                visit_tips           TEXT,
                crowd_level          TEXT,
                visit_months         TEXT,
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
                timings      TEXT,
                latitude     REAL,
                longitude    REAL,
                rating       REAL,
                source_url   TEXT,
                open_days    TEXT,
                peak_hours   TEXT,
                visit_tips   TEXT,
                verified     INTEGER DEFAULT 0,
                confidence   INTEGER DEFAULT 0,
                sources      TEXT,
                created_at   TEXT,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS cities (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                name               TEXT NOT NULL,
                district           TEXT,
                state              TEXT,
                description        TEXT,
                best_time_to_visit TEXT,
                how_to_reach       TEXT,
                latitude           REAL,
                longitude          REAL,
                peak_season        TEXT,
                off_season         TEXT,
                visit_months       TEXT,
                avg_visit_days     TEXT,
                created_at         TEXT
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

            CREATE TABLE IF NOT EXISTS flights (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT,
                airline         TEXT,
                origin          TEXT,
                destination     TEXT,
                route_name      TEXT,
                departure_time  TEXT,
                arrival_time    TEXT,
                duration        TEXT,
                fare            TEXT,
                description     TEXT,
                latitude        REAL,
                longitude       REAL,
                source_url      TEXT,
                source_type     TEXT DEFAULT 'scraped',
                sources         TEXT,
                created_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS trains (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                train_name      TEXT,
                train_no        TEXT,
                origin          TEXT,
                destination     TEXT,
                departure_time  TEXT,
                arrival_time    TEXT,
                duration        TEXT,
                distance_km     TEXT,
                train_type      TEXT,
                zone            TEXT,
                state           TEXT,
                fare            TEXT,
                availability    TEXT,
                schedule        TEXT,
                station_code    TEXT,
                platforms       TEXT,
                wifi            TEXT,
                description     TEXT,
                latitude        REAL,
                longitude       REAL,
                source_url      TEXT,
                source_type     TEXT DEFAULT 'kaggle',
                sources         TEXT,
                created_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS buses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                route_name      TEXT,
                operator        TEXT,
                origin          TEXT,
                destination     TEXT,
                departure_time  TEXT,
                arrival_time    TEXT,
                duration        TEXT,
                distance_km     TEXT,
                bus_type        TEXT,
                fare            TEXT,
                city            TEXT,
                state           TEXT,
                description     TEXT,
                source_url      TEXT,
                source_type     TEXT DEFAULT 'kaggle',
                sources         TEXT,
                created_at      TEXT
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
                start_date     TEXT,
                end_date       TEXT,
                visit_duration TEXT,
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
    # Safe migration
    # ------------------------------------------------------------------
    def _migrate(self):
        migrations = [
            # original columns
            ('restaurants',    'source_url',        'TEXT'),
            ('hotels',         'source_url',         'TEXT'),
            ('hotels',         'price_per_night',    'TEXT'),
            ('hotels',         'stars',              'TEXT'),
            ('tourist_places', 'source_url',         'TEXT'),
            # visit-time — tourist_places
            ('tourist_places', 'visit_duration',     'TEXT'),
            ('tourist_places', 'open_days',          'TEXT'),
            ('tourist_places', 'peak_season',        'TEXT'),
            ('tourist_places', 'off_season',         'TEXT'),
            ('tourist_places', 'visit_tips',         'TEXT'),
            ('tourist_places', 'crowd_level',        'TEXT'),
            ('tourist_places', 'visit_months',       'TEXT'),
            # visit-time — hotels
            ('hotels',         'check_in_time',      'TEXT'),
            ('hotels',         'check_out_time',     'TEXT'),
            ('hotels',         'peak_season',        'TEXT'),
            ('hotels',         'off_season',         'TEXT'),
            ('hotels',         'visit_months',       'TEXT'),
            # visit-time — restaurants
            ('restaurants',    'open_days',          'TEXT'),
            ('restaurants',    'peak_hours',         'TEXT'),
            ('restaurants',    'visit_tips',         'TEXT'),
            # visit-time — events
            ('events',         'start_date',         'TEXT'),
            ('events',         'end_date',           'TEXT'),
            ('events',         'visit_duration',     'TEXT'),
            # visit-time — cities
            ('cities',         'peak_season',        'TEXT'),
            ('cities',         'off_season',         'TEXT'),
            ('cities',         'visit_months',       'TEXT'),
            ('cities',         'avg_visit_days',     'TEXT'),
            # flights
            ('flights',        'name',               'TEXT'),
            ('flights',        'airline',            'TEXT'),
            ('flights',        'origin',             'TEXT'),
            ('flights',        'destination',        'TEXT'),
            ('flights',        'route_name',         'TEXT'),
            ('flights',        'departure_time',     'TEXT'),
            ('flights',        'arrival_time',       'TEXT'),
            ('flights',        'duration',           'TEXT'),
            ('flights',        'fare',               'TEXT'),
            ('flights',        'description',        'TEXT'),
            ('flights',        'latitude',           'REAL'),
            ('flights',        'longitude',          'REAL'),
            ('flights',        'source_url',         'TEXT'),
            ('flights',        'source_type',        "TEXT DEFAULT 'scraped'"),
            ('flights',        'sources',            'TEXT'),
            # trains
            ('trains',         'train_name',         'TEXT'),
            ('trains',         'train_no',           'TEXT'),
            ('trains',         'origin',             'TEXT'),
            ('trains',         'destination',        'TEXT'),
            ('trains',         'departure_time',     'TEXT'),
            ('trains',         'arrival_time',       'TEXT'),
            ('trains',         'duration',           'TEXT'),
            ('trains',         'distance_km',        'TEXT'),
            ('trains',         'train_type',         'TEXT'),
            ('trains',         'zone',               'TEXT'),
            ('trains',         'state',              'TEXT'),
            ('trains',         'fare',               'TEXT'),
            ('trains',         'availability',       'TEXT'),
            ('trains',         'schedule',           'TEXT'),
            ('trains',         'station_code',       'TEXT'),
            ('trains',         'platforms',          'TEXT'),
            ('trains',         'wifi',               'TEXT'),
            ('trains',         'description',        'TEXT'),
            ('trains',         'latitude',           'REAL'),
            ('trains',         'longitude',          'REAL'),
            ('trains',         'source_url',         'TEXT'),
            ('trains',         'source_type',        "TEXT DEFAULT 'kaggle'"),
            ('trains',         'sources',            'TEXT'),
            # buses
            ('buses',          'route_name',         'TEXT'),
            ('buses',          'operator',           'TEXT'),
            ('buses',          'origin',             'TEXT'),
            ('buses',          'destination',        'TEXT'),
            ('buses',          'departure_time',     'TEXT'),
            ('buses',          'arrival_time',       'TEXT'),
            ('buses',          'duration',           'TEXT'),
            ('buses',          'distance_km',        'TEXT'),
            ('buses',          'bus_type',           'TEXT'),
            ('buses',          'fare',               'TEXT'),
            ('buses',          'city',               'TEXT'),
            ('buses',          'state',              'TEXT'),
            ('buses',          'description',        'TEXT'),
            ('buses',          'source_url',         'TEXT'),
            ('buses',          'source_type',        "TEXT DEFAULT 'kaggle'"),
            ('buses',          'sources',            'TEXT'),
        ]
        for table, col, defn in migrations:
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
                self.conn.commit()
                logger.info(f"DB migration: added {table}.{col}")
            except sqlite3.OperationalError:
                pass


    # ------------------------------------------------------------------
    # Safe insert
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
        if isinstance(data.get('visit_months'), list):
            data['visit_months'] = json.dumps(data['visit_months'])

        real_cols = {
            row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        filtered = {k: v for k, v in data.items() if k in real_cols}
        if not filtered:
            raise ValueError(f"insert_safe: no valid keys for table '{table}'")

        # Guard NOT NULL name — skip nameless rows for name-keyed tables
        _NOT_NULL_NAME_TABLES = {
            'hotels', 'tourist_places', 'restaurants', 'events', 'cities', 'districts'
        }
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
    # Public insert methods
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

    def insert_flight(self, data: dict) -> int:
        return self._safe_insert('flights', data)

    def insert_train(self, data: dict) -> int:
        return self._safe_insert('trains', data)

    def insert_bus(self, data: dict) -> int:
        return self._safe_insert('buses', data)


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
                elif table == 'flights':
                    self.insert_flight(record)
                elif table == 'trains':
                    self.insert_train(record)
                elif table == 'buses':
                    self.insert_bus(record)
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
        tables = ['hotels', 'tourist_places', 'restaurants', 'routes',
                  'flights', 'trains', 'buses', 'events', 'guides', 'crawl_log']
        stats = {}
        for t in tables:
            try:
                row = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
                stats[t] = row['cnt']
            except Exception:
                stats[t] = 0
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
