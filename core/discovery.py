import re
from urllib.parse import urljoin, urlparse
from loguru import logger
from typing import Set, List


# ── URL must contain at least one of these to be queued ───────────────────────
URL_WHITELIST = [
    # Entity types
    'hotel', 'resort', 'homestay', 'hostel', 'lodge', 'inn', 'guesthouse',
    'guest-house', 'accommodation', 'stay',
    'restaurant', 'cafe', 'dhaba', 'eatery', 'dining', 'food',
    'temple', 'mandir', 'masjid', 'church', 'gurudwara',
    'fort', 'palace', 'mahal', 'monument', 'heritage', 'museum',
    'beach', 'waterfall', 'lake', 'hill', 'valley', 'trek', 'wildlife',
    'sanctuary', 'national-park', 'reserve',
    # Action types
    'tourism', 'tourist', 'travel', 'destination', 'attraction',
    'places-to-visit', 'things-to-do', 'sightseeing', 'tour', 'guide',
    'itinerary', 'trip', 'visit', 'explore',
    # India locations
    'india', 'west-bengal', 'kolkata', 'darjeeling', 'sikkim', 'assam',
    'rajasthan', 'jaipur', 'jodhpur', 'udaipur', 'jaisalmer',
    'kerala', 'munnar', 'alleppey', 'kochi', 'goa',
    'himachal', 'shimla', 'manali', 'uttarakhand', 'rishikesh', 'haridwar',
    'tamil-nadu', 'ooty', 'kodaikanal', 'gujarat', 'ahmedabad',
    'maharashtra', 'mumbai', 'pune', 'aurangabad',
    'karnataka', 'bangalore', 'mysore', 'hampi', 'coorg',
    'odisha', 'puri', 'bhubaneswar', 'andaman', 'lakshadweep',
    'varanasi', 'agra', 'delhi', 'amritsar', 'leh', 'ladakh',
    'gangtok', 'shillong', 'kaziranga', 'sundarbans',
]

# ── Domains / path patterns that are NEVER travel-related ──────────────────
BLACKLIST_DOMAINS = [
    'facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com',
    'linkedin.com', 'pinterest.com', 'reddit.com', 'amazon.com', 'flipkart.com',
    'snapdeal.com', 'meesho.com', 'myntra.com', 'nykaa.com',
    'google.com', 'google.co.in', 'bing.com', 'yahoo.com',
    'whatsapp.com', 'telegram.org', 'quora.com', 'medium.com',
    'github.com', 'stackoverflow.com', 'wikipedia.org',   # handled separately
    'news18.com', 'ndtv.com', 'timesofindia.com', 'hindustantimes.com',
    'economictimes.com', 'moneycontrol.com', 'livemint.com',
    'cricbuzz.com', 'espncricinfo.com', 'ipl.bcci.tv',
    'zomato.com/order', 'swiggy.com/order',
]

BLACKLIST_PATH_PATTERNS = [
    '/login', '/signup', '/register', '/cart', '/checkout', '/payment',
    '/terms', '/privacy', '/cookie', '/sitemap', '/rss', '/feed',
    '/cdn-cgi', '/wp-admin', '/wp-login', '/admin', '/dashboard',
    '/jobs', '/careers', '/about-us', '/contact-us', '/advertise',
    '/press', '/media', '/investor', '/partner', '/affiliate',
    '/app-download', '/download-app', '/play-store', '/app-store',
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
    '.css', '.js', '.xml', '.json', '.txt',
    '/tag/', '/author/', '/page/', '/category/news',
]

# Maximum URL depth to crawl (slashes after domain)
MAX_URL_DEPTH = 5


def _url_depth(url: str) -> int:
    path = urlparse(url).path
    return len([p for p in path.split('/') if p])


class DiscoveryEngine:
    def __init__(self, config: dict):
        self.config = config
        self.visited: Set[str] = set()
        self.queue: List[str] = []
        self.headers = {
            'User-Agent': config.get(
                'user_agent',
                'NexuzyDataCollector/1.2 (Educational; India Tourism Research)'
            )
        }
        self._max_per_domain: int = config.get('max_pages_per_domain', 100)
        self._domain_counts: dict = {}

    def seed(self, urls: List[str]):
        for url in urls:
            if url not in self.visited:
                self.queue.append(url)
        logger.info(f"Seeded {len(urls)} URLs into discovery engine")

    def is_relevant(self, url: str, anchor_text: str = '') -> bool:
        """Return True only if the URL is clearly travel/tourism related."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Hard block
        if any(b in domain for b in BLACKLIST_DOMAINS):
            return False

        # Block bad path patterns
        path_lower = parsed.path.lower()
        if any(pat in path_lower for pat in BLACKLIST_PATH_PATTERNS):
            return False

        # Depth guard
        if _url_depth(url) > MAX_URL_DEPTH:
            return False

        # Domain cap guard
        if self._domain_counts.get(domain, 0) >= self._max_per_domain:
            return False

        # Must match at least one travel keyword in URL or anchor text
        combined = (url + ' ' + anchor_text).lower().replace('-', ' ').replace('_', ' ')
        return any(kw in combined for kw in URL_WHITELIST)

    def next_url(self) -> str | None:
        while self.queue:
            url = self.queue.pop(0)
            if url not in self.visited:
                self.visited.add(url)
                domain = urlparse(url).netloc.lower()
                self._domain_counts[domain] = self._domain_counts.get(domain, 0) + 1
                return url
        return None

    def add_urls(self, urls: List[str], source_url: str = ''):
        """Only queue URLs that pass the relevance filter."""
        added = 0
        for url in urls:
            if url not in self.visited and self.is_relevant(url):
                self.queue.append(url)
                added += 1
        if added:
            logger.debug(f"Added {added}/{len(urls)} relevant links from {source_url}")

    @property
    def queue_size(self) -> int:
        return len(self.queue)
