import requests
from loguru import logger
from typing import Optional, Dict, List


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API  = "https://www.wikidata.org/w/api.php"

_HEADERS = {
    'User-Agent': 'NexuzyDataCollector/1.2 (travel data research; contact@nexuzy.in)',
    'Accept': 'application/json',
}


class WikipediaFetcher:
    def __init__(self, language: str = 'en'):
        self.language = language
        self.api = f"https://{language}.wikipedia.org/w/api.php"

    def search(self, query: str, limit: int = 5) -> List[str]:
        try:
            params = {
                'action':   'query',
                'list':     'search',
                'srsearch': query,
                'format':   'json',
                'srlimit':  limit,
            }
            res = requests.get(self.api, params=params, headers=_HEADERS, timeout=25)
            res.raise_for_status()
            data = res.json()
            return [item['title'] for item in data.get('query', {}).get('search', [])]
        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")
            return []

    def get_summary(self, title: str) -> Optional[Dict]:
        try:
            params = {
                'action':     'query',
                'prop':       'extracts|pageimages|coordinates|info|categories',
                'exintro':    True,
                'explaintext':True,
                'piprop':     'original',
                'inprop':     'url',
                'cllimit':    50,
                'titles':     title,
                'format':     'json',
                'redirects':  1,
            }
            res = requests.get(self.api, params=params, headers=_HEADERS, timeout=25)
            res.raise_for_status()
            pages = res.json().get('query', {}).get('pages', {})
            if not pages:
                return None
            page = next(iter(pages.values()))
            if 'missing' in page:
                return None
            coords     = page.get('coordinates', [{}])[0]
            categories = [c['title'].replace('Category:', '') for c in page.get('categories', [])]
            return {
                'title':     page.get('title', title),
                'summary':   page.get('extract', ''),
                'url':       page.get('fullurl', f'https://{self.language}.wikipedia.org/wiki/{title.replace(" ", "_")}'),
                'latitude':  coords.get('lat'),
                'longitude': coords.get('lon'),
                'image':     page.get('original', {}).get('source', ''),
                'categories':categories,
                'source':    'Wikipedia',
            }
        except Exception as e:
            logger.error(f"Wikipedia summary fetch failed for {title}: {e}")
            return None

    def get_travel_entity(self, name: str, area_hint: str = 'India') -> Optional[Dict]:
        titles = self.search(f"{name} {area_hint}", limit=5)
        for title in titles:
            data = self.get_summary(title)
            if not data:
                continue
            cat_text = ' '.join(data.get('categories', [])).lower()
            if any(k in cat_text for k in [
                'tourist', 'hotel', 'restaurant', 'museum', 'temple', 'fort', 'city',
                'village', 'beach', 'hill station', 'district', 'monument', 'heritage'
            ]):
                return data
        return self.get_summary(titles[0]) if titles else None
