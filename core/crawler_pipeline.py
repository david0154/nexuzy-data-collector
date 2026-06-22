import time
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from core.discovery import DiscoveryEngine
from core.scraper import ScraperEngine
from core.ai_extractor import AIExtractor
from core.verification import VerificationEngine, DuplicateDetector
from core.cleaner import DataCleaner
from core.database import Database
from core.geo import GeoLocator


MIN_TEXT_LEN = 80
IRRELEVANT_PAGE_SIGNALS = [
    'stock market', 'share price', 'nifty', 'sensex', 'mutual fund',
    'ipl cricket', 'match score', 'election result', 'breaking news',
    'weather forecast', 'astrology', 'horoscope',
    'e-commerce', 'online shopping', 'buy now', 'add to cart',
    'job vacancy', 'recruitment', 'syllabus', 'exam result',
    'movie review', 'bollywood', 'celebrity news',
]

# ── Per-state seed URLs  ────────────────────────────────────────────────────
# Each state gets direct, high-quality travel pages so we hit real content fast
STATE_SEEDS: dict[str, list[str]] = {
    'West Bengal': [
        'https://www.tourisminwb.gov.in/tourist-places',
        'https://en.wikipedia.org/wiki/Tourism_in_West_Bengal',
        'https://www.holidify.com/state/west-bengal/places-to-visit.html',
        'https://www.thrillophilia.com/states/west-bengal/tourist-places',
    ],
    'Rajasthan': [
        'https://www.rajasthantourism.gov.in/destinations.html',
        'https://en.wikipedia.org/wiki/Tourism_in_Rajasthan',
        'https://www.holidify.com/state/rajasthan/places-to-visit.html',
        'https://www.thrillophilia.com/states/rajasthan/tourist-places',
    ],
    'Kerala': [
        'https://www.keralatourism.org/destination/',
        'https://en.wikipedia.org/wiki/Tourism_in_Kerala',
        'https://www.holidify.com/state/kerala/places-to-visit.html',
        'https://www.thrillophilia.com/states/kerala/tourist-places',
    ],
    'Tamil Nadu': [
        'https://www.tamilnadutourism.tn.gov.in/destinations',
        'https://en.wikipedia.org/wiki/Tourism_in_Tamil_Nadu',
        'https://www.holidify.com/state/tamil-nadu/places-to-visit.html',
        'https://www.thrillophilia.com/states/tamil-nadu/tourist-places',
    ],
    'Goa': [
        'https://www.goatourism.gov.in/destinations',
        'https://en.wikipedia.org/wiki/Tourism_in_Goa',
        'https://www.holidify.com/state/goa/places-to-visit.html',
        'https://www.thrillophilia.com/states/goa/tourist-places',
    ],
    'Gujarat': [
        'https://www.gujarattourism.com/destination.html',
        'https://en.wikipedia.org/wiki/Tourism_in_Gujarat',
        'https://www.holidify.com/state/gujarat/places-to-visit.html',
        'https://www.thrillophilia.com/states/gujarat/tourist-places',
    ],
    'Maharashtra': [
        'https://www.maharashtratourism.gov.in/destination',
        'https://en.wikipedia.org/wiki/Tourism_in_Maharashtra',
        'https://www.holidify.com/state/maharashtra/places-to-visit.html',
        'https://www.thrillophilia.com/states/maharashtra/tourist-places',
    ],
    'Karnataka': [
        'https://www.karnatakatourism.org/tourism/tourist-places',
        'https://en.wikipedia.org/wiki/Tourism_in_Karnataka',
        'https://www.holidify.com/state/karnataka/places-to-visit.html',
        'https://www.thrillophilia.com/states/karnataka/tourist-places',
    ],
    'Himachal Pradesh': [
        'https://himachaltourism.gov.in/destination/',
        'https://en.wikipedia.org/wiki/Tourism_in_Himachal_Pradesh',
        'https://www.holidify.com/state/himachal-pradesh/places-to-visit.html',
        'https://www.thrillophilia.com/states/himachal-pradesh/tourist-places',
    ],
    'Uttarakhand': [
        'https://uttarakhandtourism.gov.in/destination',
        'https://en.wikipedia.org/wiki/Tourism_in_Uttarakhand',
        'https://www.holidify.com/state/uttarakhand/places-to-visit.html',
        'https://www.thrillophilia.com/states/uttarakhand/tourist-places',
    ],
    'Delhi': [
        'https://delhitourism.gov.in/delhitourism/tourist_place/index.jsp',
        'https://en.wikipedia.org/wiki/Tourism_in_Delhi',
        'https://www.holidify.com/state/delhi/places-to-visit.html',
    ],
    'Uttar Pradesh': [
        'https://uptourism.gov.in/page/desitnation',
        'https://en.wikipedia.org/wiki/Tourism_in_Uttar_Pradesh',
        'https://www.holidify.com/state/uttar-pradesh/places-to-visit.html',
    ],
    'Punjab': [
        'https://www.punjabtourism.punjab.gov.in/tour-places.aspx',
        'https://en.wikipedia.org/wiki/Tourism_in_Punjab,_India',
        'https://www.holidify.com/state/punjab/places-to-visit.html',
    ],
    'Madhya Pradesh': [
        'https://www.mptourism.com/destinations.html',
        'https://en.wikipedia.org/wiki/Tourism_in_Madhya_Pradesh',
        'https://www.holidify.com/state/madhya-pradesh/places-to-visit.html',
    ],
    'Odisha': [
        'https://odishatourism.gov.in/content/tourism/en/destination.html',
        'https://en.wikipedia.org/wiki/Tourism_in_Odisha',
        'https://www.holidify.com/state/odisha/places-to-visit.html',
    ],
    'Assam': [
        'https://assamtourism.gov.in/tourist-place',
        'https://en.wikipedia.org/wiki/Tourism_in_Assam',
        'https://www.holidify.com/state/assam/places-to-visit.html',
    ],
    'Andhra Pradesh': [
        'https://aptourism.gov.in/',
        'https://en.wikipedia.org/wiki/Tourism_in_Andhra_Pradesh',
        'https://www.holidify.com/state/andhra-pradesh/places-to-visit.html',
    ],
    'Telangana': [
        'https://www.telanganatourism.gov.in/partials/destinations/index.html',
        'https://en.wikipedia.org/wiki/Tourism_in_Telangana',
        'https://www.holidify.com/state/telangana/places-to-visit.html',
    ],
    'Jammu and Kashmir': [
        'https://www.jktourism.gov.in/destinations',
        'https://en.wikipedia.org/wiki/Tourism_in_Jammu_and_Kashmir',
        'https://www.holidify.com/state/jammu-kashmir/places-to-visit.html',
    ],
    'Bihar': [
        'https://bstdc.bih.nic.in/tourist_place.htm',
        'https://en.wikipedia.org/wiki/Tourism_in_Bihar',
        'https://www.holidify.com/state/bihar/places-to-visit.html',
    ],
}

# Fallback for any state not in the map above
DEFAULT_SEED_TEMPLATE = [
    'https://www.holidify.com/state/{slug}/places-to-visit.html',
    'https://www.thrillophilia.com/states/{slug}/tourist-places',
]


def _get_seeds_for_state(state: str) -> list[str]:
    if state in STATE_SEEDS:
        return STATE_SEEDS[state]
    slug = state.lower().replace(' ', '-').replace('&', 'and')
    return [t.replace('{slug}', slug) for t in DEFAULT_SEED_TEMPLATE]


def _is_irrelevant_page(text: str) -> bool:
    tl = text.lower()[:1000]
    hits = sum(1 for sig in IRRELEVANT_PAGE_SIGNALS if sig in tl)
    return hits >= 2


class CrawlerPipeline:
    """
    Parallel crawler pipeline.
    - PARALLEL_WORKERS threads scrape URLs concurrently
    - BATCH_SIZE URLs are dispatched at once before processing results
    - State-aware seeds: each Indian state has curated high-quality entry points
    """

    PARALLEL_WORKERS = 10   # scrape 10 URLs simultaneously
    BATCH_SIZE       = 20   # pull 20 URLs per dispatch round
    STATUS_EVERY     = 20   # log status every N pages

    def __init__(self, config: dict, db: Database, on_status=None):
        self.config     = config
        self.db         = db
        self.on_status  = on_status or (lambda msg: None)
        self.running    = False
        self._lock      = threading.Lock()   # protect shared counters + sets

        crawler_cfg = config.get('crawler', {})
        verify_cfg  = config.get('verification', {})

        self.discovery = DiscoveryEngine(crawler_cfg)
        self.scraper   = ScraperEngine(crawler_cfg)
        self.extractor = AIExtractor(config)
        self.verifier  = VerificationEngine(verify_cfg)
        self.dedup     = DuplicateDetector(threshold=85)
        self.cleaner   = DataCleaner()
        self.geo       = GeoLocator()

        self._hotel_names_seen      = self.db.get_existing_names('hotels',         'name')
        self._place_names_seen      = self.db.get_existing_names('tourist_places', 'name')
        self._restaurant_names_seen = self.db.get_existing_names('restaurants',    'name')
        self._crawled_urls          = self.db.get_crawled_urls()

        logger.info(
            f"Resume mode: skipping {len(self._crawled_urls)} already-crawled URLs — "
            f"{len(self._hotel_names_seen)} hotels, "
            f"{len(self._place_names_seen)} places, "
            f"{len(self._restaurant_names_seen)} restaurants in DB"
        )

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self, seed_urls: list, state: str = None):
        """
        Start crawling. If `state` is provided, automatically prepend
        curated high-quality seeds for that state BEFORE any custom seeds.
        """
        self.running = True

        # Inject state-wise seeds at the front of the queue
        all_seeds = []
        if state:
            state_seeds = _get_seeds_for_state(state)
            all_seeds.extend(state_seeds)
            self._status(f'📍 State mode: {state} — {len(state_seeds)} curated seed URLs injected')

        all_seeds.extend(seed_urls or [])

        # Remove already-crawled seeds immediately
        fresh_seeds = [u for u in all_seeds if u not in self._crawled_urls]
        self.discovery.seed(fresh_seeds)

        logger.info(f'Pipeline started | seeds={len(fresh_seeds)} | workers={self.PARALLEL_WORKERS}')
        self._status(f'🚀 Pipeline started — {len(fresh_seeds)} fresh seed URLs | {self.PARALLEL_WORKERS} parallel workers')

        pages_crawled  = 0
        pages_skipped  = 0
        pages_rejected = 0
        records_total  = 0

        with ThreadPoolExecutor(max_workers=self.PARALLEL_WORKERS) as pool:
            while self.running and self.discovery.queue_size > 0:
                # Pull a batch of URLs
                batch = []
                for _ in range(self.BATCH_SIZE):
                    url = self.discovery.next_url()
                    if not url:
                        break
                    if url in self._crawled_urls:
                        pages_skipped += 1
                        continue
                    batch.append(url)

                if not batch:
                    break

                # ── Parallel scrape ─────────────────────────────────────
                self._status(f'⚡ Scraping {len(batch)} URLs in parallel...')
                future_map = {pool.submit(self.scraper.scrape_static, u): u for u in batch}

                for future in as_completed(future_map):
                    if not self.running:
                        break
                    url = future_map[future]
                    try:
                        page_data = future.result()
                    except Exception as e:
                        logger.warning(f'Worker error {url}: {e}')
                        page_data = None

                    with self._lock:
                        self._crawled_urls.add(url)

                    if not page_data:
                        self.db.log_crawl(url, 'failed')
                        continue

                    text = (page_data.get('text') or '').strip()

                    if len(text) < MIN_TEXT_LEN or _is_irrelevant_page(text):
                        pages_rejected += 1
                        self.db.log_crawl(url, 'rejected_irrelevant')
                        continue

                    category = self.extractor.categorize_url(url, text)

                    if category != 'unknown':
                        new_links = self.scraper.extract_links(page_data.get('html', ''), url)
                        self.discovery.add_urls(new_links, source_url=url)

                    records_saved = 0
                    if category == 'hotel':
                        records_saved = self._process_hotel(text, url)
                    elif category == 'tourist_place':
                        records_saved = self._process_place(text, url)
                    elif category == 'restaurant':
                        records_saved = self._process_restaurant(text, url)
                    elif category == 'guide':
                        records_saved = self._process_guide(page_data, url)

                    self.db.log_crawl(url, 'success', records_saved)
                    pages_crawled  += 1
                    records_total  += records_saved

                if pages_crawled % self.STATUS_EVERY == 0 and pages_crawled > 0:
                    self._status(
                        f'📊 Crawled {pages_crawled} | Saved {records_total} records | '
                        f'Rejected {pages_rejected} | Queue {self.discovery.queue_size}'
                    )

        self.running = False
        self._status(
            f'✅ Done — {pages_crawled} pages crawled, {records_total} records saved, '
            f'{pages_rejected} irrelevant pages dropped'
        )
        logger.info('Crawler pipeline finished')

    def start_all_states(self, workers_per_state: int = 3):
        """
        Crawl ALL Indian states in parallel — one thread per state group.
        Each state thread uses its own curated seeds.
        """
        all_states = list(STATE_SEEDS.keys())
        self.running = True
        self._status(f'🇮🇳 Starting ALL-STATES crawl — {len(all_states)} states × {workers_per_state} workers')

        def _crawl_state(state_name: str):
            seeds = _get_seeds_for_state(state_name)
            fresh = [u for u in seeds if u not in self._crawled_urls]
            if not fresh:
                return
            for url in fresh:
                if not self.running:
                    return
                page_data = self.scraper.scrape_static(url)
                if not page_data:
                    continue
                text = (page_data.get('text') or '').strip()
                if len(text) < MIN_TEXT_LEN or _is_irrelevant_page(text):
                    continue
                category = self.extractor.categorize_url(url, text)
                if category == 'tourist_place':
                    self._process_place(text, url)
                elif category == 'hotel':
                    self._process_hotel(text, url)
                elif category == 'guide':
                    self._process_guide(page_data, url)
                with self._lock:
                    self._crawled_urls.add(url)

        with ThreadPoolExecutor(max_workers=workers_per_state * len(all_states)) as pool:
            futures = {pool.submit(_crawl_state, s): s for s in all_states}
            for future in as_completed(futures):
                state_name = futures[future]
                try:
                    future.result()
                    self._status(f'  ✅ {state_name} done')
                except Exception as e:
                    self._status(f'  ❌ {state_name} error: {e}')

        self._status('🏁 All-states crawl complete!')

    def stop(self):
        self.running = False
        self._status('Pipeline stopped by user')

    def _status(self, msg: str):
        self.on_status(msg)
        logger.info(msg)

    # ── PROCESSORS ─────────────────────────────────────────────────────────

    def _process_hotel(self, text: str, url: str) -> int:
        data = self.extractor.extract(text, 'hotel')
        if not data:
            return 0
        name = (data.get('hotel_name') or data.get('name', '')).strip()
        if len(name) < 3 or name.lower() in ('hotel', 'resort', 'inn', 'stay'):
            return 0
        with self._lock:
            if self.dedup.find_duplicate(name, self._hotel_names_seen) is not None:
                return 0
            if not data.get('city') and not data.get('address'):
                return 0
            cleaned = self.cleaner.clean_hotel(data)
            cleaned['source_url'] = url
            cleaned = self.geo.enrich_record(cleaned)
            self.db.insert_hotel(cleaned)
            self._hotel_names_seen.append(name)
        logger.info(f"Hotel saved: {name} | city={data.get('city','?')}")
        return 1

    def _process_place(self, text: str, url: str) -> int:
        data = self.extractor.extract(text, 'place')
        if not data:
            return 0
        name = data.get('name', '').strip()
        if len(name) < 3:
            return 0
        with self._lock:
            if self.dedup.find_duplicate(name, self._place_names_seen) is not None:
                return 0
            if not data.get('city') and not data.get('address'):
                return 0
            cleaned = self.cleaner.clean_tourist_place(data)
            cleaned['source_url'] = url
            cleaned = self.geo.enrich_record(cleaned)
            self.db.insert_tourist_place(cleaned)
            self._place_names_seen.append(name)
        logger.info(f"Place saved: {name} | city={data.get('city','?')}")
        return 1

    def _process_restaurant(self, text: str, url: str) -> int:
        data = self.extractor.extract(text, 'restaurant')
        if not data:
            return 0
        name = data.get('name', '').strip()
        if len(name) < 3 or name.lower() in ('restaurant', 'cafe', 'dhaba', 'food'):
            return 0
        with self._lock:
            if self.dedup.find_duplicate(name, self._restaurant_names_seen) is not None:
                return 0
            if not data.get('city') and not data.get('address'):
                return 0
            cleaned = self.cleaner.clean_restaurant(data)
            cleaned['source_url'] = url
            cleaned = self.geo.enrich_record(cleaned)
            self.db.insert_restaurant(cleaned)
            self._restaurant_names_seen.append(name)
        logger.info(f"Restaurant saved: {name} | city={data.get('city','?')}")
        return 1

    def _process_guide(self, page_data: dict, url: str) -> int:
        title = (page_data.get('title') or '').strip()
        text  = (page_data.get('text')  or '').strip()
        if len(title) < 5 or len(text) < 100:
            return 0
        city = self.extractor._extract_city(text)
        if not city:
            return 0
        with self._lock:
            self.db.insert_guide({
                'title':      title,
                'city':       city,
                'content':    text[:3000],
                'source_url': url,
                'category':   'travel_guide',
            })
        logger.info(f"Guide saved: {title[:60]} | city={city}")
        return 1