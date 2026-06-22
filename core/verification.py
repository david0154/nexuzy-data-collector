"""
verification.py
===============
Two engines:

1. VerificationEngine
   - calculate_confidence()  — field-based score (unchanged)
   - merge_records()         — merge multi-source data (unchanged)
   - verify_place_online()   — NEW: DuckDuckGo search + HTTP liveness check
   - verify_batch()          — NEW: parallel verify a list of records

2. DuplicateDetector
   - find_duplicate()        — now city-aware (same name, different city = NOT duplicate)
   - deduplicate_list()      — smarter merge instead of drop
"""

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import requests
from thefuzz import fuzz
from loguru import logger

# ── Shared HTTP session for all online checks ────────────────────────
_SESSION = requests.Session()
_SESSION.headers.update({
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-IN,en;q=0.9',
})
_SESSION_LOCK = threading.Lock()

# DuckDuckGo Instant Answer API (no API key needed)
DDG_URL = 'https://api.duckduckgo.com/'
DDG_HTML_URL = 'https://html.duckduckgo.com/html/'

# Status labels
STATUS_ACTIVE   = 'active'
STATUS_INACTIVE = 'inactive'
STATUS_UNKNOWN  = 'unknown'

# How long to wait between DuckDuckGo calls (avoid rate-limit)
DDG_DELAY = 0.5   # seconds


def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo and return a list of result dicts:
      [{'title': ..., 'url': ..., 'snippet': ...}, ...]
    Uses the HTML endpoint (most reliable, no key needed).
    """
    try:
        time.sleep(DDG_DELAY)
        params = {'q': query, 'kl': 'in-en', 'kp': '-1'}
        with _SESSION_LOCK:
            resp = _SESSION.post(
                DDG_HTML_URL, data=params,
                timeout=10, allow_redirects=True
            )
        if resp.status_code != 200:
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'lxml')
        results = []
        for r in soup.select('.result')[:max_results]:
            title_el = r.select_one('.result__title a')
            snip_el  = r.select_one('.result__snippet')
            if not title_el:
                continue
            results.append({
                'title':   title_el.get_text(strip=True),
                'url':     title_el.get('href', ''),
                'snippet': snip_el.get_text(strip=True) if snip_el else '',
            })
        return results

    except Exception as e:
        logger.debug(f'DDG search error: {e}')
        return []


def _http_liveness(url: str, timeout: int = 8) -> bool:
    """
    Return True if `url` returns a 2xx/3xx status code (site is live).
    """
    if not url or not url.startswith('http'):
        return False
    try:
        with _SESSION_LOCK:
            resp = _SESSION.head(
                url, timeout=timeout,
                allow_redirects=True, verify=False
            )
        return resp.status_code < 400
    except Exception:
        try:
            with _SESSION_LOCK:
                resp = _SESSION.get(
                    url, timeout=timeout,
                    allow_redirects=True, verify=False,
                    stream=True
                )
            return resp.status_code < 400
        except Exception:
            return False


def _build_search_query(record: dict, record_type: str = 'place') -> str:
    name  = record.get('name') or record.get('hotel_name') or ''
    city  = record.get('city') or record.get('state') or ''
    state = record.get('state') or ''
    if record_type == 'hotel':
        return f'{name} hotel {city} {state} India official site'.strip()
    elif record_type == 'restaurant':
        return f'{name} restaurant {city} India'.strip()
    else:  # place
        return f'{name} tourist place {city} India'.strip()


def _score_ddg_results(results: list[dict], name: str, city: str) -> dict:
    """
    Analyse DDG results and return:
      {
        'found': bool,
        'status': 'active'|'inactive'|'unknown',
        'confidence_boost': int (0-20),
        'reason': str,
        'top_url': str,
      }
    """
    if not results:
        return {'found': False, 'status': STATUS_UNKNOWN,
                'confidence_boost': 0, 'reason': 'No DDG results',
                'top_url': ''}

    name_lc = name.lower()
    city_lc = city.lower() if city else ''

    CLOSED_SIGNALS  = [
        'permanently closed', 'closed down', 'demolished',
        'no longer exists', 'shut down', 'razed', 'abandoned',
        'being renovated', 'under renovation', 'closed for renovation',
    ]
    ACTIVE_SIGNALS  = [
        'open', 'visit', 'book now', 'timings', 'entry fee',
        'hours', 'open daily', 'open to public', 'open for visitors',
        'tours', 'attraction', 'must visit',
    ]

    top_url = results[0]['url'] if results else ''
    combined_text = ' '.join(
        (r.get('title', '') + ' ' + r.get('snippet', '')).lower()
        for r in results
    )

    # Name match in results?
    name_found = any(
        fuzz.partial_ratio(name_lc, r.get('title', '').lower()) > 70
        for r in results
    )
    city_found = city_lc in combined_text if city_lc else True

    closed_hits = sum(1 for sig in CLOSED_SIGNALS if sig in combined_text)
    active_hits = sum(1 for sig in ACTIVE_SIGNALS if sig in combined_text)

    if closed_hits >= 2:
        status = STATUS_INACTIVE
        boost  = 0
        reason = f'Closed signals found: {closed_hits}'
    elif name_found and city_found and active_hits >= 1:
        status = STATUS_ACTIVE
        boost  = 20
        reason = f'Active signals: {active_hits}, name+city confirmed'
    elif name_found:
        status = STATUS_ACTIVE
        boost  = 10
        reason = 'Name confirmed in DDG results'
    else:
        status = STATUS_UNKNOWN
        boost  = 0
        reason = 'Name not confirmed in DDG results'

    return {
        'found':            name_found,
        'status':           status,
        'confidence_boost': boost,
        'reason':           reason,
        'top_url':          top_url,
    }


class VerificationEngine:
    def __init__(self, config: dict):
        self.min_sources           = config.get('min_sources', 2)
        self.confidence_threshold  = config.get('confidence_threshold', 70)
        self.online_verify_enabled = config.get('online_verify', True)
        self.online_workers        = config.get('online_verify_workers', 6)

    # ── Existing helpers (unchanged) ────────────────────────────────

    def calculate_confidence(self, records: list) -> int:
        if not records:
            return 0
        base = min(len(records) * 25, 75)
        has_address = any(r.get('address') or r.get('city') for r in records)
        has_price   = any(r.get('price_min') or r.get('price_range') for r in records)
        has_desc    = any(r.get('description') for r in records)
        bonus = (10 if has_address else 0) + (10 if has_price else 0) + (5 if has_desc else 0)
        return min(base + bonus, 99)

    def merge_records(self, records: list) -> dict:
        if not records:
            return {}
        merged = {}
        for record in records:
            for k, v in record.items():
                if v and not merged.get(k):
                    merged[k] = v
        sources = []
        for r in records:
            src = r.get('sources', [])
            if isinstance(src, str):
                try:
                    src = json.loads(src)
                except Exception:
                    src = [src]
            sources.extend(src)
        merged['sources']    = list(set(sources))
        merged['verified']   = 1 if len(sources) >= self.min_sources else 0
        merged['confidence'] = self.calculate_confidence(records)
        return merged

    def is_verified(self, record: dict) -> bool:
        sources = record.get('sources', [])
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except Exception:
                sources = [sources]
        return (
            len(sources) >= self.min_sources
            and record.get('confidence', 0) >= self.confidence_threshold
        )

    # ── NEW: Online verification ────────────────────────────────────

    def verify_place_online(
        self,
        record: dict,
        record_type: str = 'place',
    ) -> dict:
        """
        Verify a single record against live internet data.

        Steps:
          1. Build a DuckDuckGo query from name + city
          2. Parse results for active/closed signals
          3. HTTP liveness check on source_url (if present)
          4. Return enriched record with extra fields:
             - online_status:   'active' | 'inactive' | 'unknown'
             - online_verified: 0 | 1
             - verification_reason: str
             - confidence: updated int
        """
        name       = (record.get('name') or record.get('hotel_name') or '').strip()
        city       = (record.get('city') or '').strip()
        source_url = (record.get('source_url') or '').strip()

        if not name:
            record.update({'online_status': STATUS_UNKNOWN,
                           'online_verified': 0,
                           'verification_reason': 'No name to verify'})
            return record

        # Step 1: DuckDuckGo search
        query   = _build_search_query(record, record_type)
        results = _ddg_search(query, max_results=5)
        scored  = _score_ddg_results(results, name, city)

        # Step 2: HTTP liveness on source_url
        url_live = None
        if source_url:
            url_live = _http_liveness(source_url)
            if not url_live and scored['status'] == STATUS_ACTIVE:
                # Source URL is dead but DDG says active — still active, just stale URL
                scored['reason'] += ' | source_url dead (stale link)'
            elif url_live:
                scored['confidence_boost'] = min(scored['confidence_boost'] + 5, 25)
                scored['reason'] += ' | source_url live'

        # Step 3: Compose final verdict
        base_confidence = record.get('confidence', 50)
        new_confidence  = min(base_confidence + scored['confidence_boost'], 99)

        online_verified = 1 if (
            scored['status'] == STATUS_ACTIVE
            and new_confidence >= self.confidence_threshold
        ) else 0

        record.update({
            'online_status':        scored['status'],
            'online_verified':      online_verified,
            'verification_reason':  scored['reason'],
            'confidence':           new_confidence,
            'ddg_top_url':          scored.get('top_url', ''),
            'source_url_live':      url_live,
        })

        logger.info(
            f'[Verify] {name} | {city} → {scored["status"]} '
            f'(conf={new_confidence}) | {scored["reason"]}'
        )
        return record

    def verify_batch(
        self,
        records:     list,
        record_type: str = 'place',
        on_progress = None,
    ) -> list:
        """
        Parallel internet verification for a list of records.
        on_progress(done, total, record) called after each record.
        Returns the same list with online_status fields filled in.
        """
        if not self.online_verify_enabled:
            return records

        total  = len(records)
        done   = 0
        lock   = threading.Lock()

        def _verify_one(rec):
            nonlocal done
            result = self.verify_place_online(rec, record_type)
            with lock:
                done += 1
                if on_progress:
                    on_progress(done, total, result)
            return result

        with ThreadPoolExecutor(max_workers=self.online_workers) as pool:
            futures  = {pool.submit(_verify_one, r): r for r in records}
            verified = []
            for future in as_completed(futures):
                try:
                    verified.append(future.result())
                except Exception as e:
                    original = futures[future]
                    original['online_status']       = STATUS_UNKNOWN
                    original['online_verified']     = 0
                    original['verification_reason'] = f'Error: {e}'
                    verified.append(original)

        # Preserve original order
        order = {id(r): i for i, r in enumerate(records)}
        verified.sort(key=lambda r: order.get(id(r), 9999))
        return verified


# ───────────────────────────────────────────────────────────────────

class DuplicateDetector:
    """
    Smart duplicate detection:
    - City-aware: same name in different cities = NOT duplicate
    - Fuzzy name match (token_sort_ratio)
    - On true duplicate, MERGES data instead of dropping
    """

    def __init__(self, threshold: int = 85):
        self.threshold = threshold

    def _names_similar(self, a: str, b: str) -> bool:
        if not a or not b:
            return False
        return fuzz.token_sort_ratio(a.lower(), b.lower()) >= self.threshold

    def _cities_same(self, city_a: str, city_b: str) -> bool:
        """
        Two records are city-matched if:
        - Both cities are empty (no city info on either)
        - OR fuzzy match >= 80
        """
        if not city_a and not city_b:
            return True   # no city data: assume same
        if not city_a or not city_b:
            return False  # one has city, other doesn't: different
        return fuzz.token_sort_ratio(city_a.lower(), city_b.lower()) >= 80

    def is_duplicate(
        self,
        name1:  str,
        name2:  str,
        city1:  str = '',
        city2:  str = '',
    ) -> bool:
        """
        Return True only if BOTH name AND city match.
        'Taj Mahal Agra' vs 'Taj Mahal Mumbai' = NOT duplicate.
        """
        return self._names_similar(name1, name2) and self._cities_same(city1, city2)

    def find_duplicate(
        self,
        new_name:       str,
        existing_names: list,
        new_city:       str = '',
        existing_cities: list = None,
    ) -> Optional[int]:
        """
        Find the index of an existing entry that matches new_name + new_city.
        existing_cities: parallel list of cities for existing_names.
        If existing_cities is None, city check is skipped (backward compat).
        """
        for i, name in enumerate(existing_names):
            city = existing_cities[i] if existing_cities else ''
            if self.is_duplicate(new_name, name, new_city, city):
                return i
        return None

    def deduplicate_list(
        self,
        records:    list,
        name_field: str = 'name',
        city_field: str = 'city',
    ) -> list:
        """
        Deduplicate a list of records.
        On duplicate: MERGE fields (prefer non-empty values) instead of dropping.
        Returns deduplicated list preserving insertion order.
        """
        seen_names  = []
        seen_cities = []
        unique      = []

        for record in records:
            name = record.get(name_field, '') or ''
            city = record.get(city_field, '') or ''

            idx = self.find_duplicate(
                name, seen_names, city, seen_cities
            )

            if idx is None:
                # New entry
                seen_names.append(name)
                seen_cities.append(city)
                unique.append(record)
            else:
                # Merge: fill empty fields in existing record from new record
                existing = unique[idx]
                merged   = dict(existing)
                for k, v in record.items():
                    if v and not merged.get(k):
                        merged[k] = v
                # Keep higher confidence
                merged['confidence'] = max(
                    existing.get('confidence', 0),
                    record.get('confidence', 0)
                )
                # Merge source lists
                s1 = existing.get('sources', [])
                s2 = record.get('sources', [])
                if isinstance(s1, str):
                    try: s1 = json.loads(s1)
                    except Exception: s1 = [s1]
                if isinstance(s2, str):
                    try: s2 = json.loads(s2)
                    except Exception: s2 = [s2]
                merged['sources'] = list(set(s1 + s2))
                unique[idx] = merged
                logger.debug(
                    f"Duplicate merged: '{name}' in '{city}' → enriched existing record"
                )

        return unique
