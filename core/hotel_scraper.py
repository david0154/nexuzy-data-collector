"""
hotel_scraper.py
================
Collects hotel data for any Indian city using FREE, open sources only:
  1. OpenStreetMap Overpass API  (via OSMFetcher — POST, no key needed)
  2. WikiData SPARQL endpoint    (structured hotel records, no key needed)

NO private OTA APIs, NO MakeMyTrip, NO Goibibo, NO Yatra,
NO Booking.com, NO Agoda, NO Cleartrip scrapers.

Returns a list of standardised hotel dicts:
  {
    name, city, state, address, rating, stars,
    phone, website, latitude, longitude,
    review_count, description,
    source_platform, source_url, sources,
    verified, confidence
  }
"""

import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import requests
from loguru import logger

from core.osm_fetcher import OSMFetcher


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip())


def _to_float(text: str) -> Optional[float]:
    m = re.search(r'[\d]+(?:\.\d+)?', (text or '').replace(',', ''))
    return float(m.group()) if m else None


# ─────────────────────────────────────────────────────────────────
# SOURCE 1 — OpenStreetMap via OSMFetcher (POST, correct method)
# ─────────────────────────────────────────────────────────────────

def _fetch_osm_hotels(city: str, state: str = '') -> List[Dict]:
    """
    Uses OSMFetcher (which correctly POSTs to Overpass API).
    Fetches hotels, guest houses, and hostels for the given city.
    """
    osm = OSMFetcher(timeout=90)
    results = []

    for tourism_type in ['hotel', 'guest_house', 'hostel']:
        logger.info(f'[OSM] Fetching tourism={tourism_type} in {city}')
        records = osm.fetch_places(
            area_name=city,
            key='tourism',
            value=tourism_type,
            limit=300,
        )
        for r in records:
            r.setdefault('city', city)
            r.setdefault('state', state or 'India')
            r['source_platform'] = 'OpenStreetMap'
            r['source_url'] = 'https://www.openstreetmap.org'
            r.setdefault('sources', ['OpenStreetMap'])
            r.setdefault('verified', 1)
            r.setdefault('confidence', 95)
        results.extend(records)
        logger.info(f'[OSM] {city} tourism={tourism_type}: {len(records)} records')

    logger.info(f'[OSM] {city} total: {len(results)} hotels/guesthouses fetched')
    return results


# ─────────────────────────────────────────────────────────────────
# SOURCE 2 — WikiData SPARQL (free, structured, no key needed)
# ─────────────────────────────────────────────────────────────────

WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'
_WIKIDATA_HEADERS = {
    'Accept': 'application/sparql-results+json',
    'User-Agent': 'NexuzyDataCollector/1.2 (travel research; contact@nexuzy.in)',
}


def _fetch_wikidata_hotels(city: str, state: str = '') -> List[Dict]:
    """
    Queries WikiData SPARQL for hotels (Q27686) in a given city.
    Falls back to state-level query if city returns nothing.
    """
    def _run_query(location_label: str, is_state: bool = False) -> List[Dict]:
        location_filter = (
            f'?hotel wdt:P131+ ?loc . ?loc rdfs:label "{location_label}"@en .'
            if is_state else
            f'?hotel wdt:P131 ?loc . ?loc rdfs:label "{location_label}"@en .'
        )
        query = f"""
        SELECT DISTINCT ?hotel ?hotelLabel ?website ?stars ?address ?lat ?lon WHERE {{
          ?hotel wdt:P31 wd:Q27686 .
          {location_filter}
          OPTIONAL {{ ?hotel wdt:P856 ?website }}
          OPTIONAL {{ ?hotel wdt:P855 ?stars }}
          OPTIONAL {{ ?hotel wdt:P969 ?address }}
          OPTIONAL {{
            ?hotel p:P625 ?coord .
            ?coord psv:P625 ?coordNode .
            ?coordNode wikibase:geoLatitude  ?lat .
            ?coordNode wikibase:geoLongitude ?lon .
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 200
        """
        try:
            resp = requests.get(
                WIKIDATA_SPARQL,
                params={'query': query, 'format': 'json'},
                headers=_WIKIDATA_HEADERS,
                timeout=45,
            )
            resp.raise_for_status()
            bindings = resp.json().get('results', {}).get('bindings', [])
            records = []
            for row in bindings:
                name = row.get('hotelLabel', {}).get('value', '')
                if not name or name.startswith('Q'):   # skip bare QIDs
                    continue
                records.append({
                    'name':            _clean(name),
                    'city':            city,
                    'state':           state or 'India',
                    'address':         _clean(row.get('address', {}).get('value', '')),
                    'website':         row.get('website', {}).get('value', ''),
                    'stars':           row.get('stars', {}).get('value', ''),
                    'latitude':        _to_float(row.get('lat', {}).get('value', '')),
                    'longitude':       _to_float(row.get('lon', {}).get('value', '')),
                    'rating':          None,
                    'review_count':    None,
                    'description':     '',
                    'source_platform': 'WikiData',
                    'source_url':      'https://www.wikidata.org',
                    'sources':         ['WikiData'],
                    'verified':        1,
                    'confidence':      90,
                })
            return records
        except Exception as e:
            logger.warning(f'[WikiData] Query failed for {location_label}: {e}')
            return []

    records = _run_query(city, is_state=False)
    if not records and state:
        logger.info(f'[WikiData] No results for city "{city}", trying state "{state}"')
        records = _run_query(state, is_state=True)

    logger.info(f'[WikiData] {city}: {len(records)} hotels fetched')
    return records


# ─────────────────────────────────────────────────────────────────
# MASTER RUNNER
# ─────────────────────────────────────────────────────────────────

def scrape_hotels_for_city(
    city:        str,
    state:       str  = '',
    platforms:   list = None,   # kept for API compatibility; ignored
    pages:       int  = 2,      # kept for API compatibility; ignored
    workers:     int  = 2,
    on_progress=None,
) -> List[Dict]:
    """
    Collects hotels for a city from OSM + WikiData in parallel.
    Returns merged + deduplicated list of hotel dicts.

    `platforms`, `pages` params are kept for backward-compatibility
    but are no longer used (OTA scrapers removed).
    """
    from core.verification import DuplicateDetector
    dedup = DuplicateDetector(threshold=85)

    all_results: List[Dict] = []
    lock = threading.Lock()

    tasks = [
        ('OpenStreetMap', lambda: _fetch_osm_hotels(city, state)),
        ('WikiData',      lambda: _fetch_wikidata_hotels(city, state)),
    ]

    def _run(label, fn):
        try:
            records = fn()
            with lock:
                if on_progress:
                    on_progress(label, len(records))
            return records
        except Exception as e:
            logger.error(f'[{label}] error: {e}')
            return []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run, label, fn): label for label, fn in tasks}
        for future in as_completed(futures):
            try:
                all_results.extend(future.result())
            except Exception as e:
                logger.error(f'Hotel scrape future error: {e}')

    merged = dedup.deduplicate_list(all_results, name_field='name', city_field='city')
    logger.info(
        f'Hotel collection complete: {len(all_results)} raw '
        f'→ {len(merged)} after dedup  (sources: OSM + WikiData)'
    )
    return merged


# ─────────────────────────────────────────────────────────────────
# Convenience aliases (for any code that calls individual scrapers)
# ─────────────────────────────────────────────────────────────────

def scrape_makemytrip(*a, **kw):
    logger.warning('scrape_makemytrip() removed — use scrape_hotels_for_city() instead')
    return []

def scrape_goibibo(*a, **kw):
    logger.warning('scrape_goibibo() removed — use scrape_hotels_for_city() instead')
    return []

def scrape_yatra(*a, **kw):
    logger.warning('scrape_yatra() removed — use scrape_hotels_for_city() instead')
    return []

def scrape_booking(*a, **kw):
    logger.warning('scrape_booking() removed — use scrape_hotels_for_city() instead')
    return []

def scrape_agoda(*a, **kw):
    logger.warning('scrape_agoda() removed — use scrape_hotels_for_city() instead')
    return []

def scrape_cleartrip(*a, **kw):
    logger.warning('scrape_cleartrip() removed — use scrape_hotels_for_city() instead')
    return []
