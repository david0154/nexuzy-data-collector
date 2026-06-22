import time
import requests
from loguru import logger
from typing import List, Dict


# Mirrors tried in order. On 429, we wait then try next.
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

_HEADERS = {
    'User-Agent': 'NexuzyDataCollector/1.2 (travel data research; contact@nexuzy.in)',
    'Accept': 'application/json',
}

# Seconds to wait after a 429 before trying the next mirror
_RATE_LIMIT_WAIT = 65
# Seconds to wait between consecutive queries to the same mirror
_INTER_QUERY_WAIT = 10


class OSMFetcher:
    def __init__(self, timeout: int = 90):
        self.timeout = timeout
        self._last_query_time: float = 0.0
        self._mirror_banned_until: dict = {}   # mirror_url -> epoch time

    def _wait_if_needed(self):
        """Enforce minimum gap between queries."""
        elapsed = time.time() - self._last_query_time
        if elapsed < _INTER_QUERY_WAIT:
            time.sleep(_INTER_QUERY_WAIT - elapsed)

    def _query(self, overpass_query: str) -> dict:
        """Try each mirror; respect 429 bans with exponential backoff."""
        self._wait_if_needed()
        now = time.time()

        for url in OVERPASS_MIRRORS:
            # Skip mirrors that are still in their ban window
            banned_until = self._mirror_banned_until.get(url, 0)
            if now < banned_until:
                remaining = int(banned_until - now)
                logger.debug(f"OSM mirror {url} still banned for {remaining}s, skipping")
                continue

            try:
                resp = requests.post(
                    url,
                    data={'data': overpass_query},
                    headers=_HEADERS,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    # Rate limited — ban this mirror for _RATE_LIMIT_WAIT seconds
                    self._mirror_banned_until[url] = time.time() + _RATE_LIMIT_WAIT
                    logger.warning(
                        f"OSM 429 on {url} — banned for {_RATE_LIMIT_WAIT}s, trying next mirror"
                    )
                    continue

                resp.raise_for_status()
                self._last_query_time = time.time()
                return resp.json()

            except requests.exceptions.Timeout:
                logger.warning(f"OSM mirror {url} timed out after {self.timeout}s")
                continue
            except Exception as e:
                logger.warning(f"OSM mirror {url} failed: {e}")
                continue

        # All mirrors failed or banned — wait for the least-banned one
        soonest = min(
            (v for v in self._mirror_banned_until.values()),
            default=0
        )
        wait = max(0, soonest - time.time())
        if wait > 0:
            logger.info(f"All OSM mirrors rate-limited. Waiting {int(wait)}s...")
            time.sleep(wait + 2)
            return self._query(overpass_query)   # retry once after cooldown

        logger.error("All OSM Overpass mirrors failed – returning empty result.")
        return {"elements": []}

    def fetch_places(self, area_name: str, key: str, value: str, limit: int = 200) -> List[Dict]:
        query = f"""
        [out:json][timeout:60];
        area[\"name\"=\"{area_name}\"]->.searchArea;
        (
          node[\"{key}\"=\"{value}\"](area.searchArea);
          way[\"{key}\"=\"{value}\"](area.searchArea);
          relation[\"{key}\"=\"{value}\"](area.searchArea);
        );
        out center {limit};
        """
        data = self._query(query)
        return self._normalize(data.get('elements', []), category=value)

    def fetch_tourism_bundle(self, area_name: str, limit: int = 300) -> Dict[str, List[Dict]]:
        """Fetch all tourism categories for a region with per-query delays."""
        categories = [
            ('tourism', 'hotel'),
            ('tourism', 'attraction'),
            ('tourism', 'museum'),
            ('tourism', 'guest_house'),
            ('tourism', 'hostel'),
            ('amenity', 'restaurant'),
            ('amenity', 'cafe'),
            ('amenity', 'place_of_worship'),
        ]
        result = {}
        for key, value in categories:
            logger.info(f"OSM fetching {key}={value} in {area_name}")
            result[value.replace('_', 's') if value != 'place_of_worship' else 'temples'] = \
                self.fetch_places(area_name, key, value, limit)
        return result

    def _normalize(self, elements: List[Dict], category: str = '') -> List[Dict]:
        records = []
        for el in elements:
            tags = el.get('tags', {})
            lat  = el.get('lat') or el.get('center', {}).get('lat')
            lon  = el.get('lon') or el.get('center', {}).get('lon')
            name = tags.get('name') or tags.get('name:en', '')
            if not name:
                continue
            records.append({
                'name':        name,
                'category':    category,
                'address':     self._build_address(tags),
                'description': tags.get('description', ''),
                'city':        tags.get('addr:city', ''),
                'district':    tags.get('addr:district', ''),
                'state':       tags.get('addr:state', 'India'),
                'contact':     tags.get('phone', '') or tags.get('contact:phone', ''),
                'website':     tags.get('website', '') or tags.get('contact:website', ''),
                'stars':       tags.get('stars', ''),
                'latitude':    lat,
                'longitude':   lon,
                'rating':      None,
                'verified':    1,
                'confidence':  95,
                'sources':     ['OpenStreetMap'],
            })
        return records

    def _build_address(self, tags: Dict) -> str:
        parts = [
            tags.get('addr:housename',   ''),
            tags.get('addr:housenumber', ''),
            tags.get('addr:street',      ''),
            tags.get('addr:suburb',      ''),
            tags.get('addr:city',        ''),
            tags.get('addr:district',    ''),
            tags.get('addr:state',       ''),
            tags.get('addr:postcode',    ''),
        ]
        return ', '.join([p for p in parts if p]).strip(', ')
