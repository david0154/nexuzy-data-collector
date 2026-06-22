"""
Nexuzy Data Collector — Kaggle Dataset Importer
================================================
Downloads Kaggle datasets and imports ONLY the fields each table needs.
Extra / unknown columns are silently discarded.

How it works
------------
Each table has a TARGET_SCHEMA — a dict of  db_column → [list of CSV synonyms].
For every CSV, we do a case-insensitive fuzzy match against the synonyms and
build a clean record with only the wanted keys. Any CSV column that doesn't
match any synonym is thrown away.

Setup (one-time):
  pip install kaggle pandas
  Get kaggle.json from https://www.kaggle.com/settings -> API -> Create New Token
  Save to  C:\\Users\\<you>\\.kaggle\\kaggle.json
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False
    logger.warning("pandas not installed — run: pip install pandas")

try:
    import kaggle  # noqa: F401
    _KAGGLE_OK = True
except (ImportError, OSError):
    _KAGGLE_OK = False
    logger.warning(
        "Kaggle API not configured.\n"
        "  1. pip install kaggle\n"
        "  2. Go to https://www.kaggle.com/settings -> API -> Create New Token\n"
        "  3. Save kaggle.json to C:/Users/<you>/.kaggle/kaggle.json"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TARGET SCHEMAS
# Each entry: db_column → list of CSV column synonyms (case-insensitive).
# The importer picks the FIRST synonym that exists in the CSV.
# Only these fields are saved — everything else is discarded.
# ─────────────────────────────────────────────────────────────────────────────

TARGET_SCHEMAS: dict[str, dict[str, list[str]]] = {

    'tourist_places': {
        'name': [
            'name', 'place_name', 'place name', 'tourist_place', 'tourist place',
            'attraction', 'destination', 'title', 'spot', 'site',
            'place', 'location_name', 'tourist_spot',
        ],
        'city': ['city', 'town', 'municipality', 'urban_area'],
        'state': ['state', 'province', 'region', 'territory'],
        'district': ['district', 'zone', 'taluk', 'tehsil'],
        'address': ['address', 'location', 'locality', 'area', 'full_address'],
        'category': ['category', 'type', 'kind', 'classification', 'place_type', 'tag'],
        'description': [
            'description', 'about', 'overview', 'detail', 'info',
            'significance', 'highlight', 'summary', 'review',
        ],
        'entry_fee': ['entry_fee', 'entry fee', 'entrance_fee', 'entrance fee', 'ticket', 'fare', 'budget', 'cost'],
        'timings': ['timings', 'opening_hours', 'hours', 'timing', 'schedule', 'time', 'weekly_off'],
        'best_time_to_visit': [
            'best_time_to_visit', 'best time to visit', 'best_time', 'best time',
            'best_season', 'peak_season', 'ideal_time', 'visit_season',
        ],
        'rating': [
            'rating', 'google_rating', 'google rating', 'review_rating',
            'score', 'stars', 'avg_rating',
        ],
        'latitude': ['latitude', 'lat', 'geo_lat', 'y'],
        'longitude': ['longitude', 'lon', 'long', 'lng', 'geo_lon', 'x'],
        'visit_duration': ['visit_duration', 'time needed to visit in hrs', 'duration', 'time_needed'],
        'peak_season': ['peak_season', 'best_season', 'season'],
        'crowd_level': ['crowd_density', 'crowd_level', 'crowd'],
        'website': ['website', 'url', 'web', 'link', 'pageurl'],
    },

    'hotels': {
        'name': [
            'property_name', 'hotel_name', 'hotel name', 'name', 'hotel',
            'title', 'property', 'accommodation_name',
        ],
        'city': ['city', 'town', 'location_city'],
        'state': ['state', 'province', 'region'],
        'address': ['address', 'locality', 'location', 'full_address', 'area'],
        'description': ['hotel_description', 'description', 'about', 'overview', 'detail'],
        'amenities': ['hotel_facilities', 'amenities', 'facilities', 'features', 'services'],
        'stars': [
            'hotel_star_rating', 'star_rating', 'stars', 'star', 'star_class',
            'classification', 'hotel_class',
        ],
        'rating': [
            'site_review_rating', 'rating', 'review_rating', 'score',
            'guest_rating', 'overall_rating', 'avg_rating',
        ],
        'price_per_night': [
            'price_per_night', 'price', 'fare', 'rate', 'tariff',
            'cost_per_night', 'room_price', 'price_inr',
        ],
        'category': ['property_type', 'category', 'type', 'kind', 'hotel_type'],
        'contact': ['contact', 'phone', 'mobile', 'tel', 'telephone', 'phone_number'],
        'website': ['pageurl', 'website', 'url', 'web', 'link'],
        'latitude': ['latitude', 'lat'],
        'longitude': ['longitude', 'lon', 'long', 'lng'],
    },

    'flights': {
        'name': ['flight', 'flight_name', 'flight_no', 'flight no', 'flight_number', 'name'],
        'airline': ['airline', 'carrier', 'airline_name', 'operator'],
        'origin': ['source', 'from', 'origin', 'src_airport', 'source_airport', 'departure_city'],
        'destination': ['destination', 'to', 'dest', 'dst_airport', 'destination_airport', 'arrival_city'],
        'route_name': ['route', 'route_name', 'path'],
        'departure_time': ['dep_time', 'departure_time', 'departure', 'dep time', 'scheduled_departure'],
        'arrival_time': ['arrival_time', 'arrival', 'scheduled_arrival'],
        'duration': ['duration', 'total_time', 'flight_duration', 'travel_time'],
        'fare': ['price', 'fare', 'price_inr', 'ticket_price', 'cost'],
        'description': ['additional_info', 'info', 'stops', 'total_stops', 'equipment', 'codeshare', 'notes'],
    },

    'trains': {
        'train_name': [
            'train_name', 'train name', 'trainname', 'name',
            'station_name', 'station name',  # for station datasets
        ],
        'train_no': ['train_no', 'train no', 'trainno', 'number', 'train_number'],
        'station_code': ['station_code', 'code', 'stn_code'],
        'origin': ['source', 'from', 'origin', 'from_station', 'source_station', 'city'],
        'destination': ['destination', 'to', 'dest', 'to_station'],
        'train_type': ['type', 'train_type', 'category', 'class', 'travel_class'],
        'departure_time': ['departure_time', 'departure', 'dep_time', 'scheduled_departure'],
        'arrival_time': ['arrival_time', 'arrival', 'arr_time'],
        'duration': ['duration', 'travel_time', 'total_time'],
        'distance_km': ['distance_km', 'distance', 'km'],
        'fare': ['fare', 'price', 'ticket_price', 'cost'],
        'availability': ['availability', 'available_seats', 'seats'],
        'schedule': ['schedule', 'days', 'runs_on'],
        'zone': ['zone', 'railway_zone'],
        'state': ['state', 'province'],
        'latitude': ['latitude', 'lat'],
        'longitude': ['longitude', 'lon', 'long', 'lng'],
        'platforms': ['platforms', 'platform_count', 'num_platforms'],
        'wifi': ['wifi', 'wifi_available'],
        'description': ['description', 'food', 'accessibility', 'info', 'additional_info', 'equipment'],
    },

    'buses': {
        'route_name': [
            'route_name', 'route name', 'route', 'bus_name', 'name',
            'bus', 'service_name',
        ],
        'origin': ['source', 'from', 'origin', 'from_city', 'departure_city'],
        'destination': ['destination', 'to', 'dest', 'to_city', 'arrival_city'],
        'city': ['city', 'town'],
        'state': ['state', 'province'],
        'departure_time': ['departure_time', 'departure', 'dep_time'],
        'arrival_time': ['arrival_time', 'arrival', 'arr_time'],
        'duration': ['duration', 'travel_time'],
        'distance_km': ['distance_km', 'distance'],
        'fare': ['price', 'fare', 'ticket_price', 'cost'],
        'operator': ['operator', 'bus_operator', 'company', 'provider'],
        'bus_type': ['bus_type', 'type', 'category', 'class', 'vehicle_type'],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DATASETS REGISTRY  (slug + target_table only — no more col_map needed)
# ─────────────────────────────────────────────────────────────────────────────

DATASETS: list[dict] = [
    # ── Tourist Places ────────────────────────────────────────────────────────
    {'id': 'indian_tourism_54f',       'slug': 'sushanthnaidu24/indian-tourism-dataset',                              'description': 'Indian Tourism Dataset (100 destinations, 54 fields)',        'target_table': 'tourist_places'},
    {'id': 'explore_india_tourist',    'slug': 'kumarperiya/explore-india-a-tourist-destination-dataset',             'description': 'Explore India Tourist Destination Dataset',                    'target_table': 'tourist_places'},
    {'id': 'top_places',               'slug': 'dhrubangtalukdar/top-indian-places-to-visit-indian-tourism',         'description': 'Top Indian Places to Visit',                                 'target_table': 'tourist_places'},
    {'id': 'india_tourism_atlas',      'slug': 'anushkamandekar/indiatourismatlas',                                   'description': 'India Tourism Atlas',                                       'target_table': 'tourist_places'},
    {'id': 'india_must_see_places',    'slug': 'saketk511/travel-dataset-guide-to-indias-must-see-places',           'description': "Guide to India's Must-See Places (325 destinations)",        'target_table': 'tourist_places'},
    {'id': 'famous_indian_tourist_places', 'slug': 'naqibahmedkadri/famous-indian-tourist-places',                   'description': 'Famous Indian Tourist Places',                               'target_table': 'tourist_places'},
    {'id': 'most_traveled_cities',     'slug': 'kirtandwivedi02/most-traveled-cities-in-india',                      'description': 'Most Traveled Cities in India',                              'target_table': 'tourist_places'},
    {'id': 'india_places_reviews',     'slug': 'ritvik1909/indian-places-to-visit-reviews-data',                     'description': 'Indian Places Reviews Dataset',                              'target_table': 'tourist_places'},
    {'id': 'travel_recommendation',    'slug': 'amanmehra23/travel-recommendation-dataset',                          'description': 'Travel Recommendation Dataset',                              'target_table': 'tourist_places'},
    {'id': 'dynamic_tourism_routes',   'slug': 'ziya07/dynamic-tourism-route-dataset-dtrd',                          'description': 'Dynamic Tourism Route Dataset',                              'target_table': 'tourist_places'},
    {'id': 'road_tourism_sustainable', 'slug': 'ziya07/road-tourism-data-for-sustainable-route-prediction',          'description': 'Road Tourism Data for Sustainable Route Prediction',          'target_table': 'tourist_places'},
    {'id': 'tourist_attractions',      'slug': 'dakshineswarm/indian-tourist-attraction-dataset',                     'description': 'Indian Tourist Attractions (~500 places)',                   'target_table': 'tourist_places'},
    {'id': 'india_tourism_stats',      'slug': 'rajkumarl/india-tourism-statistics',                                  'description': 'India Tourism Statistics',                                  'target_table': 'tourist_places'},
    {'id': 'google_places_rating',     'slug': 'chetanborse/google-places-rating-for-indian-cities',                 'description': 'Google Places Rating for Indian Cities',                    'target_table': 'tourist_places'},
    {'id': 'india_tourism_datasets',   'slug': 'rakkeshcase/india-tourism-datasets',                                  'description': 'India Tourism Datasets (multi-file bundle)',                 'target_table': 'tourist_places'},

    # ── Hotels ────────────────────────────────────────────────────────────────
    {'id': 'goibibo_hotels',           'slug': 'PromptCloudHQ/hotels-on-goibibo',                                     'description': 'Indian Hotels on Goibibo (4,000 hotels)',                   'target_table': 'hotels'},
    {'id': 'makemytrip_hotels',        'slug': 'PromptCloudHQ/hotels-on-makemytrip',                                  'description': 'Hotels on MakeMyTrip (20,000 hotels)',                      'target_table': 'hotels'},
    {'id': 'booking_com_hotels',       'slug': 'PromptCloudHQ/indian-hotels-on-bookingcom',                           'description': 'Indian Hotels on Booking.com (6,000 hotels)',               'target_table': 'hotels'},
    {'id': 'cleartrip_hotels',         'slug': 'PromptCloudHQ/indian-hotels-on-cleartrip',                            'description': 'Indian Hotels on Cleartrip (5,000 hotels)',                 'target_table': 'hotels'},
    {'id': 'google_indian_hotels',     'slug': 'alvinmanojalex/google-indian-hotel-data',                             'description': 'Google Indian Hotel Data 2023',                             'target_table': 'hotels'},
    {'id': 'hotels_india_reviews',     'slug': 'aakashshinde1507/hotels-in-india',                                    'description': 'Hotels in India',                                          'target_table': 'hotels'},
    {'id': 'hotel_details',            'slug': 'nehaprabhakar/hotel-details-dataset-india',                           'description': 'Hotel Details Dataset — India',                            'target_table': 'hotels'},

    # ── Flights ───────────────────────────────────────────────────────────────
    {'id': 'flights_india',            'slug': 'dhairya903/flights-in-india',                                         'description': 'Flights in India Dataset',                                  'target_table': 'flights'},
    {'id': 'indian_airlines',          'slug': 'kabil007/indian-domestic-airline-dataset',                            'description': 'Indian Domestic Airline Dataset',                           'target_table': 'flights'},
    {'id': 'indian_flight_schedules',  'slug': 'nikhilkhetan/indian-flight-schedules',                                'description': 'Indian Flight Schedules',                                   'target_table': 'flights'},
    {'id': 'india_domestic_flights_6yr','slug': 'shraddha4ever20/indian-domestic-flights-dataset-20192025',           'description': 'Indian Domestic Flights 2019-2025',                         'target_table': 'flights'},
    {'id': 'global_airline_routes',    'slug': 'elmoallistair/airlines-airport-and-routes',                           'description': 'Airlines, Airports & Flight Routes (67,664 routes)',       'target_table': 'flights'},
    {'id': 'openflights_routes',       'slug': 'open-flights/flight-route-database',                                  'description': 'Flight Route Database (59,036 routes)',                     'target_table': 'flights'},
    {'id': 'airline_routes_92k',       'slug': 'moonnectar/airline-routes-92k-and-airports-10k-dataset',             'description': 'Airline Routes 92K+ & Airports 9K+',                        'target_table': 'flights'},

    # ── Railways ──────────────────────────────────────────────────────────────
    {'id': 'indian_railways_core',         'slug': 'sripaadsrinivasan/indian-railways-dataset',                          'description': 'Indian Railways Dataset',                                   'target_table': 'trains'},
    {'id': 'indian_railways_latest',       'slug': 'arihantjain09/indian-railways-latest',                               'description': 'Indian Railways Latest (11,114 trains)',                    'target_table': 'trains'},
    {'id': 'railway_stations',             'slug': 'flugeltomar/indian-railway-dataset',                                 'description': 'Indian Railway Stations Dataset',                           'target_table': 'trains'},
    {'id': 'railway_stations_facilities',  'slug': 'shraddha4ever20/indian-railway-stations-codes-and-facilities-data',  'description': 'Indian Railway Stations Codes & Facilities',                'target_table': 'trains'},
    {'id': 'railways_prices',              'slug': 'bhavyarajdev/indian-railways-schedule-prices-availability-data',     'description': 'Indian Railways Schedule, Prices & Availability',           'target_table': 'trains'},
    {'id': 'railways_timetable',           'slug': 'harsh16/indian-railways-time-table-for-trains-available',            'description': 'Indian Railways Time Table',                                 'target_table': 'trains'},

    # ── Bus Routes ────────────────────────────────────────────────────────────
    {'id': 'bus_routes_pan_india',     'slug': 'rohitgds/pan-india-bus-routes-35k-schedules-1000-cities',             'description': 'Pan India Bus Routes (35,667 schedules)',                   'target_table': 'buses'},
    {'id': 'bus_routes_cities',        'slug': 'ayushkhaire/indian-cities-buses-routes-and-prices',                   'description': 'Indian Cities Bus Routes & Prices',                         'target_table': 'buses'},
]


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-DETECT COLUMN MAPPER
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    """Lowercase, strip whitespace, collapse non-alphanumeric to underscore."""
    return re.sub(r'[^a-z0-9]+', '_', s.lower().strip()).strip('_')


def _build_column_map(csv_columns: list[str], schema: dict[str, list[str]]) -> dict[str, str]:
    """
    Returns {csv_column → db_column} for every CSV column that matches a synonym.
    A synonym is matched case-insensitively (and with spaces→underscore normalisation).
    The first synonym in each db_column list wins; later ones are fallbacks.
    Each CSV column is mapped to at most ONE db_column (first match wins).
    """
    # Build reverse lookup: normalised_synonym → db_column
    # Earlier synonyms in the list have higher priority (they're listed first)
    syn_to_db: dict[str, str] = {}
    for db_col, synonyms in schema.items():
        for syn in synonyms:
            norm = _normalise(syn)
            if norm not in syn_to_db:          # first synonym wins
                syn_to_db[norm] = db_col

    col_map: dict[str, str] = {}              # csv_col → db_col
    used_db_cols: set[str] = set()            # ensure 1-to-1 mapping

    for csv_col in csv_columns:
        norm = _normalise(csv_col)
        db_col = syn_to_db.get(norm)
        if db_col and db_col not in used_db_cols:
            col_map[csv_col] = db_col
            used_db_cols.add(db_col)

    return col_map


# ─────────────────────────────────────────────────────────────────────────────
# IMPORTER
# ─────────────────────────────────────────────────────────────────────────────

class KaggleImporter:
    """Download Kaggle datasets and import only the fields each table needs."""

    def __init__(self, db):
        self.db = db
        self.imported_count = 0
        self.failed_count = 0

    # ── public API ────────────────────────────────────────────────────────────

    def run_all(self):
        logger.info(f"Starting import of {len(DATASETS)} Kaggle datasets...")
        if not _KAGGLE_OK:
            logger.error("Kaggle API not configured. Cannot proceed."); return False
        if not _PANDAS_OK:
            logger.error("pandas not installed. Cannot proceed."); return False

        for ds in DATASETS:
            try:
                self.run(ds['id'])
            except Exception as e:
                logger.error(f"Failed to import {ds['id']}: {e}")
                self.failed_count += 1

        logger.info(f"Import complete: {self.imported_count} succeeded, {self.failed_count} failed")
        return self.failed_count == 0

    def run(self, dataset_id: str) -> bool:
        ds = next((d for d in DATASETS if d['id'] == dataset_id), None)
        if not ds:
            logger.error(f"Dataset '{dataset_id}' not found in registry"); return False
        if not _KAGGLE_OK or not _PANDAS_OK:
            logger.warning(f"Skipping {dataset_id}: missing dependencies"); return False

        logger.info(f"Importing {ds['description']} ({ds['slug']})...")
        schema = TARGET_SCHEMAS.get(ds['target_table'], {})

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)

                result = subprocess.run(
                    ['kaggle', 'datasets', 'download', '-d', ds['slug'], '-p', str(tmp)],
                    capture_output=True, timeout=300,
                )
                if result.returncode != 0:
                    logger.error(f"Kaggle download failed: {result.stderr.decode()}")
                    self.failed_count += 1; return False

                for zf in tmp.glob('*.zip'):
                    with zipfile.ZipFile(zf) as z:
                        z.extractall(tmp)

                csv_files = list(tmp.glob('*.csv'))
                if not csv_files:
                    # Try one level deep
                    csv_files = list(tmp.glob('**/*.csv'))
                if not csv_files:
                    logger.warning(f"No CSV files found in {ds['slug']}")
                    self.failed_count += 1; return False

                total_inserted = 0
                for csv_file in csv_files:
                    inserted = self._process_csv(csv_file, ds['target_table'], schema, dataset_id)
                    total_inserted += inserted

                if total_inserted == 0:
                    logger.warning(f"0 records inserted for {dataset_id} — no matching columns found.")
                    self.failed_count += 1; return False

                logger.info(f"Successfully imported {total_inserted} records from {dataset_id}")
                self.imported_count += 1; return True

        except Exception as e:
            logger.error(f"Error importing {dataset_id}: {e}")
            self.failed_count += 1; return False

    # ── internals ─────────────────────────────────────────────────────────────

    def _load_csv(self, path: Path) -> Optional['pd.DataFrame']:
        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                return pd.read_csv(path, encoding=enc, low_memory=False)
            except (UnicodeDecodeError, pd.errors.ParserError):
                try:
                    return pd.read_csv(path, encoding=enc, on_bad_lines='skip', low_memory=False)
                except Exception:
                    pass
        logger.error(f"Could not parse {path.name} with any encoding")
        return None

    def _process_csv(
        self,
        csv_file: Path,
        table: str,
        schema: dict[str, list[str]],
        dataset_id: str,
    ) -> int:
        df = self._load_csv(csv_file)
        if df is None or df.empty:
            return 0

        csv_cols = list(df.columns)
        col_map = _build_column_map(csv_cols, schema)   # csv_col → db_col

        # Log what we matched vs. what we discarded
        matched_db = sorted(set(col_map.values()))
        discarded  = [c for c in csv_cols if c not in col_map]
        logger.info(
            f"[{dataset_id}] {csv_file.name}: "
            f"kept {len(matched_db)} fields {matched_db} | "
            f"discarded {len(discarded)} cols"
        )

        if not col_map:
            logger.warning(
                f"[{dataset_id}] No columns matched schema for table '{table}'.\n"
                f"  CSV columns : {csv_cols}\n"
                f"  Schema keys : {list(schema.keys())}"
            )
            return 0

        # Build clean records — only matched columns, skip fully empty rows
        records: list[dict] = []
        for _, row in df.iterrows():
            record: dict = {}
            for csv_col, db_col in col_map.items():
                val = row[csv_col]
                if pd.notna(val) and str(val).strip() not in ('', 'nan', 'None', 'NaN', 'NULL'):
                    record[db_col] = str(val).strip() if isinstance(val, str) else val
            if record:
                records.append(record)

        if not records:
            return 0

        if self.db and hasattr(self.db, 'insert_batch'):
            self.db.insert_batch(table, records)

        return len(records)
