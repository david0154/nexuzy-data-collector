import time
import requests
import urllib3
from bs4 import BeautifulSoup
import trafilatura
from loguru import logger
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

_SKIP_ERRORS = (
    '404', '410', 'Not Found',
    'getaddrinfo failed', 'Name or service not known', 'NameResolutionError',
)


def _is_dead_url_error(msg: str) -> bool:
    return any(k in str(msg) for k in _SKIP_ERRORS)


class ScraperEngine:
    """Fast parallel HTTP scraper — low delay, 8s timeout, connection pooling."""

    def __init__(self, config: dict):
        self.config  = config
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-IN,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }
        # ── Speed settings ─────────────────────────────────────────
        # delay=0.2s (was 1.5s), timeout=8s (was 30s), retries=1 (was 2)
        self.delay   = config.get('delay_between_requests', 0.2)
        self.timeout = config.get('timeout', 8)
        self.retries = config.get('max_retries', 1)
        self.session = self._make_session()

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.headers)
        # Connection pool: keep 20 connections alive for reuse
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=50,
            max_retries=0,
        )
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            try:
                ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
            except Exception:
                pass

            class _LegacyAdapter(requests.adapters.HTTPAdapter):
                def __init__(self, *a, **kw):
                    super().__init__(*a, **kw)
                def init_poolmanager(self, *a, **kw):
                    kw['ssl_context'] = ctx
                    super().init_poolmanager(*a, **kw)

            session.mount('https://', _LegacyAdapter(
                pool_connections=20, pool_maxsize=50, max_retries=0))
        except Exception as e:
            logger.debug(f'Legacy SSL adapter skipped: {e}')
            session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session

    def scrape_static(self, url: str) -> Optional[dict]:
        for attempt in range(self.retries):
            try:
                if self.delay > 0:
                    time.sleep(self.delay)
                resp = self.session.get(
                    url, timeout=self.timeout,
                    verify=False, allow_redirects=True,
                )
                resp.raise_for_status()
                html = resp.text
                soup  = BeautifulSoup(html, 'lxml')
                title = soup.title.string.strip() if soup.title else ''
                text  = trafilatura.extract(
                    html, include_links=False,
                    include_tables=True, no_fallback=False
                ) or ''
                meta_desc = ''
                meta = soup.find('meta', attrs={'name': 'description'})
                if meta:
                    meta_desc = meta.get('content', '')
                return {
                    'url': url, 'title': title, 'text': text,
                    'meta_description': meta_desc, 'html': html,
                }
            except Exception as e:
                err = str(e)
                if _is_dead_url_error(err):
                    logger.warning(f'Dead URL skipped: {url} | {err[:80]}')
                    return None
                logger.warning(f'Scrape attempt {attempt+1} failed: {url}: {err[:80]}')
        return None

    def scrape_dynamic(self, url: str) -> Optional[dict]:
        if not PLAYWRIGHT_AVAILABLE:
            return self.scrape_static(url)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers(self.headers)
                page.goto(url, timeout=self.timeout * 1000)
                page.wait_for_load_state('networkidle', timeout=10000)
                html  = page.content()
                title = page.title()
                browser.close()
            soup = BeautifulSoup(html, 'lxml')
            text = trafilatura.extract(
                html, include_links=False,
                include_tables=True, no_fallback=False
            ) or ''
            meta_desc = ''
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                meta_desc = meta.get('content', '')
            return {'url': url, 'title': title, 'text': text,
                    'meta_description': meta_desc, 'html': html}
        except Exception as e:
            logger.warning(f'Dynamic scrape failed for {url}: {e}')
            return self.scrape_static(url)

    def scrape(self, url: str, dynamic: bool = False) -> Optional[dict]:
        return self.scrape_dynamic(url) if dynamic else self.scrape_static(url)

    def scrape_batch(self, urls: list, workers: int = 10) -> dict:
        """Scrape multiple URLs in parallel. Returns {url: result_or_None}."""
        results = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(self.scrape_static, u): u for u in urls}
            for future in as_completed(future_map):
                url = future_map[future]
                try:
                    results[url] = future.result()
                except Exception as e:
                    logger.warning(f'Batch scrape error {url}: {e}')
                    results[url] = None
        return results

    def extract_links(self, html: str, base_url: str) -> list:
        from urllib.parse import urljoin, urlparse
        soup = BeautifulSoup(html, 'lxml')
        base_domain = urlparse(base_url).netloc
        links = []
        for a in soup.find_all('a', href=True):
            href = urljoin(base_url, a['href'])
            if href.startswith('http') and urlparse(href).netloc == base_domain:
                links.append(href)
        return list(set(links))