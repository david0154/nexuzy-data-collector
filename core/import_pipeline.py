"""
Nexuzy Data Collector - Import Pipeline
Handles OSM, Wikipedia, RSS, and Hotel Portal import into SQLite.
"""

import json
from loguru import logger
from typing import List, Dict, Callable, Optional
from core.database import Database
from core.cleaner import DataCleaner
from core.verification import DuplicateDetector
from core.osm_fetcher import OSMFetcher
from core.wikipedia_fetcher import WikipediaFetcher
from core.rss_crawler import RSSCrawler


class ImportPipeline:
    def __init__(self, db: Database, on_status: Callable = None):
        self.db = db
        self.on_status = on_status or (lambda msg: None)
        self.cleaner = DataCleaner()
        self.dedup = DuplicateDetector(threshold=85)
        self._ensure_extra_columns()

    def _ensure_extra_columns(self):
        """Add extra columns to tables if they don’t exist yet."""
        additions = [
            ('hotels', 'source_type',      'TEXT DEFAULT \'scraped\''),
            ('hotels', 'source_platform',  'TEXT'),
            ('hotels', 'review_count',     'INTEGER'),
            ('hotels', 'stars',            'INTEGER'),
            ('hotels', 'amenities',        'TEXT'),
            ('tourist_places', 'source_type', 'TEXT DEFAULT \'scraped\''),
            ('restaurants',    'source_type', 'TEXT DEFAULT \'scraped\''),
            ('guides',         'source_type', 'TEXT DEFAULT \'scraped\''),
        ]
        for table, col, col_def in additions:
            try:
                self.db.conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}')
                self.db.conn.commit()
            except Exception:
                pass  # column already exists

    def _get_existing_names(self, table: str, name_field: str = 'name') -> List[str]:
        rows = self.db.conn.execute(f'SELECT {name_field} FROM {table}').fetchall()
        return [r[0] for r in rows if r[0]]

    def _get_existing_cities(self, table: str) -> List[str]:
        rows = self.db.conn.execute(f'SELECT city FROM {table}').fetchall()
        return [r[0] or '' for r in rows]

    # ============================================================
    # HOTEL PORTAL IMPORT (NEW)
    # ============================================================
    def import_hotels_from_portals(
        self,
        city:      str,
        state:     str = '',
        platforms: list = None,
        pages:     int = 2,
    ) -> Dict[str, int]:
        """
        Scrape hotels from MakeMyTrip, Goibibo, Yatra, Booking.com,
        Agoda and/or Cleartrip for `city` and save to the hotels table.
        """
        self.on_status(f'[🏨 Hotels] Starting portal scrape for: {city}')

        from core.hotel_scraper import scrape_hotels_for_city

        platform_counts: Dict[str, int] = {}

        def _on_progress(platform, count):
            platform_counts[platform] = count
            self.on_status(f'  [{platform}] → {count} hotels found for {city}')

        hotels = scrape_hotels_for_city(
            city=city, state=state, platforms=platforms,
            pages=pages, workers=6, on_progress=_on_progress,
        )

        # Save to DB with dedup
        existing_names  = self._get_existing_names('hotels')
        existing_cities = self._get_existing_cities('hotels')
        saved = 0

        for h in hotels:
            name = self.cleaner.clean_name(h.get('name', ''))
            if not name:
                continue
            city_val = h.get('city', city)
            idx = self.dedup.find_duplicate(
                name, existing_names, city_val, existing_cities
            )
            if idx is not None:
                # Merge: fill empty fields in existing DB record
                existing_id_row = self.db.conn.execute(
                    'SELECT id FROM hotels WHERE name=? LIMIT 1',
                    (existing_names[idx],)
                ).fetchone()
                if existing_id_row:
                    self._merge_hotel_into_db(existing_id_row[0], h)
                continue

            data = {
                'name':            name,
                'city':            city_val,
                'state':           h.get('state', state),
                'address':         h.get('address', ''),
                'description':     h.get('description', ''),
                'contact':         h.get('contact', ''),
                'website':         h.get('website', ''),
                'latitude':        h.get('latitude'),
                'longitude':       h.get('longitude'),
                'price_min':       h.get('price_min'),
                'price_max':       h.get('price_max'),
                'rating':          h.get('rating'),
                'review_count':    h.get('review_count'),
                'stars':           h.get('stars'),
                'amenities':       json.dumps(h.get('amenities', [])),
                'source_url':      h.get('source_url', ''),
                'source_platform': h.get('source_platform', ''),
                'source_type':     'portal',
                'verified':        h.get('verified', 1),
                'confidence':      h.get('confidence', 80),
                'sources':         json.dumps(h.get('sources', [])),
            }
            self.db.insert_hotel(data)
            existing_names.append(name)
            existing_cities.append(city_val)
            saved += 1

        total_raw  = sum(platform_counts.values())
        msg = (
            f'[🏨 Hotels] Done — {total_raw} raw records from '
            f'{len(platform_counts)} platforms → {saved} new saved (deduped)'
        )
        self.on_status(msg)
        logger.info(msg)
        return {'hotels_saved': saved, 'hotels_raw': total_raw, **platform_counts}

    def _merge_hotel_into_db(self, hotel_id: int, new_data: dict):
        """Fill empty columns in an existing hotel row from new_data."""
        fill_cols = [
            'address', 'contact', 'website', 'latitude', 'longitude',
            'price_min', 'price_max', 'rating', 'review_count', 'stars',
            'amenities', 'description',
        ]
        for col in fill_cols:
            val = new_data.get(col)
            if val is None:
                continue
            try:
                self.db.conn.execute(
                    f'UPDATE hotels SET {col}=? WHERE id=? AND ({col} IS NULL OR {col}="")',
                    (val, hotel_id)
                )
            except Exception:
                pass
        # Always extend sources list
        try:
            row = self.db.conn.execute(
                'SELECT sources FROM hotels WHERE id=?', (hotel_id,)
            ).fetchone()
            old_src = json.loads(row[0]) if row and row[0] else []
            new_src = new_data.get('sources', [])
            merged_src = list(set(old_src + new_src))
            self.db.conn.execute(
                'UPDATE hotels SET sources=? WHERE id=?',
                (json.dumps(merged_src), hotel_id)
            )
        except Exception:
            pass
        self.db.conn.commit()

    # ============================================================
    # OSM IMPORT (unchanged)
    # ============================================================
    def import_osm(self, area_name: str, limit: int = 200) -> Dict[str, int]:
        self.on_status(f'[OSM] Starting import for: {area_name}')
        osm = OSMFetcher()
        bundle = osm.fetch_tourism_bundle(area_name, limit=limit)
        counts = {}
        hotel_records = (bundle.get('hotels', []) + bundle.get('guest_houses', []) + bundle.get('hostels', []))
        counts['hotels'] = self._save_osm_hotels(hotel_records, area_name)
        place_records = bundle.get('attractions', []) + bundle.get('museums', [])
        counts['tourist_places'] = self._save_osm_places(place_records, area_name)
        food_records = bundle.get('restaurants', []) + bundle.get('cafes', [])
        counts['restaurants'] = self._save_osm_restaurants(food_records, area_name)
        temple_records = bundle.get('temples', [])
        counts['temples'] = self._save_osm_places(temple_records, area_name)
        total = sum(counts.values())
        self.on_status(f'[OSM] Done: {total} records saved for {area_name}')
        logger.info(f'OSM import complete for {area_name}: {counts}')
        return counts

    def _save_osm_hotels(self, records, area_name):
        existing = self._get_existing_names('hotels')
        saved = 0
        for r in records:
            name = r.get('name', '')
            if not name or self.dedup.find_duplicate(name, existing) is not None:
                continue
            self.db.insert_hotel({
                'name': self.cleaner.clean_name(name),
                'city': r.get('city', '') or area_name,
                'district': r.get('district', ''),
                'state': r.get('state', 'India'),
                'address': r.get('address', ''),
                'description': r.get('description', ''),
                'contact': r.get('contact', ''),
                'website': r.get('website', ''),
                'latitude': r.get('latitude'),
                'longitude': r.get('longitude'),
                'verified': 1, 'confidence': 95,
                'sources': json.dumps(['OpenStreetMap']),
                'source_type': 'osm',
            })
            existing.append(name)
            saved += 1
        return saved

    def _save_osm_places(self, records, area_name):
        existing = self._get_existing_names('tourist_places')
        saved = 0
        for r in records:
            name = r.get('name', '')
            if not name or self.dedup.find_duplicate(name, existing) is not None:
                continue
            self.db.insert_tourist_place({
                'name': self.cleaner.clean_name(name),
                'city': r.get('city', '') or area_name,
                'district': r.get('district', ''),
                'state': r.get('state', 'India'),
                'address': r.get('address', ''),
                'description': r.get('description', ''),
                'category': r.get('category', ''),
                'latitude': r.get('latitude'),
                'longitude': r.get('longitude'),
                'verified': 1, 'confidence': 95,
                'sources': json.dumps(['OpenStreetMap']),
                'source_type': 'osm',
            })
            existing.append(name)
            saved += 1
        return saved

    def _save_osm_restaurants(self, records, area_name):
        existing = self._get_existing_names('restaurants')
        saved = 0
        for r in records:
            name = r.get('name', '')
            if not name or self.dedup.find_duplicate(name, existing) is not None:
                continue
            self.db.insert_restaurant({
                'name': self.cleaner.clean_name(name),
                'city': r.get('city', '') or area_name,
                'district': r.get('district', ''),
                'state': r.get('state', 'India'),
                'address': r.get('address', ''),
                'description': r.get('description', ''),
                'contact': r.get('contact', ''),
                'website': r.get('website', ''),
                'latitude': r.get('latitude'),
                'longitude': r.get('longitude'),
                'verified': 1, 'confidence': 95,
                'sources': json.dumps(['OpenStreetMap']),
                'source_type': 'osm',
            })
            existing.append(name)
            saved += 1
        return saved

    # ============================================================
    # WIKIPEDIA IMPORT (unchanged)
    # ============================================================
    def import_wikipedia(self, queries: List[str]) -> Dict[str, int]:
        self.on_status(f'[Wikipedia] Starting import for {len(queries)} queries...')
        wiki = WikipediaFetcher()
        existing_places = self._get_existing_names('tourist_places')
        existing_guides = self._get_existing_names('guides', 'title')
        places_saved = guides_saved = 0
        for query in queries:
            self.on_status(f'[Wikipedia] Fetching: {query}')
            data = wiki.get_travel_entity(query, area_hint='India')
            if not data or not data.get('summary'):
                continue
            title = data.get('title', query)
            summary = data.get('summary', '')
            lat = data.get('latitude')
            lon = data.get('longitude')
            url = data.get('url', '')
            cats = ' '.join(data.get('categories', [])).lower()
            is_place = any(k in cats for k in [
                'tourist', 'temple', 'fort', 'palace', 'museum', 'beach',
                'monument', 'heritage', 'waterfall', 'lake', 'national park'
            ])
            if is_place:
                if self.dedup.find_duplicate(title, existing_places) is None:
                    self.db.insert_tourist_place({
                        'name': self.cleaner.clean_name(title),
                        'description': summary[:1200],
                        'latitude': lat, 'longitude': lon,
                        'verified': 1, 'confidence': 90,
                        'sources': json.dumps([url]),
                        'source_type': 'wikipedia',
                    })
                    existing_places.append(title)
                    places_saved += 1
            else:
                if self.dedup.find_duplicate(title, existing_guides) is None:
                    self.db.insert_guide({
                        'title': title, 'content': summary[:2000],
                        'source_url': url, 'category': 'wikipedia',
                        'source_type': 'wikipedia',
                    })
                    existing_guides.append(title)
                    guides_saved += 1
        self.on_status(f'[Wikipedia] Done: {places_saved} places + {guides_saved} guides')
        return {'tourist_places': places_saved, 'guides': guides_saved}

    # ============================================================
    # RSS IMPORT (unchanged)
    # ============================================================
    def import_rss(self, feeds: List[str] = None, limit_per_feed: int = 10) -> Dict[str, int]:
        self.on_status('[RSS] Starting RSS feed import...')
        rss = RSSCrawler(feeds=feeds)
        articles = rss.fetch_and_extract_all(limit_per_feed=limit_per_feed)
        existing_guides = self._get_existing_names('guides', 'title')
        saved = 0
        for art in articles:
            title = art.get('title') or art.get('rss_title', '')
            text  = art.get('text') or art.get('rss_summary', '')
            if not title or not text:
                continue
            if self.dedup.find_duplicate(title, existing_guides) is not None:
                continue
            self.db.insert_guide({
                'title': self.cleaner.clean_text(title)[:255],
                'content': self.cleaner.clean_text(text)[:2500],
                'source_url': art.get('source_url', ''),
                'category': 'rss_blog', 'source_type': 'rss',
            })
            existing_guides.append(title)
            saved += 1
            self.on_status(f'[RSS] Saved: {title[:60]}')
        self.on_status(f'[RSS] Done: {saved} articles saved')
        return {'guides': saved}
