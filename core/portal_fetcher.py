"""
Nexuzy Data Collector — Travel Portal Fetcher
Scrapes hotel listings, prices, ratings, and addresses from:
  MakeMyTrip, Goibibo, Yatra, Booking.com, Agoda, OYO, Trivago

Uses requests + BeautifulSoup with rotating delays.
All portals are scraped respectfully (1-3s delay, real User-Agent).
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Optional


_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
]

_BASE_DELAY = 2.0   # seconds between requests


def _get(url: str, params: dict = None, extra_headers: dict = None) -> Optional[requests.Response]:
    headers = {
        'User-Agent': random.choice(_USER_AGENTS),
        'Accept-Language': 'en-IN,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
    }
    if extra_headers:
        headers.update(extra_headers)
    try:
        time.sleep(_BASE_DELAY + random.uniform(0.5, 1.5))
        resp = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.warning(f"Portal fetch failed [{url}]: {e}")
        return None


def _clean_price(text: str) -> str:
    """Extract first INR price from text."""
    m = re.search(r'(?:Rs\.?|INR|\u20b9)\s*([\d,]+)', text or '', re.IGNORECASE)
    return m.group(0).strip() if m else ''


def _clean_rating(text: str) -> Optional[float]:
    m = re.search(r'(\d+\.?\d*)\s*(?:/\s*10|/\s*5|out of)', text or '', re.IGNORECASE)
    if m:
        val = float(m.group(1))
        return round(val / 10 * 5, 1) if val > 5 else val
    m2 = re.search(r'(\d\.\d)', text or '')
    return float(m2.group(1)) if m2 else None


# ─────────────────────────────────────────────────────────────────────────
# MakeMyTrip
# ─────────────────────────────────────────────────────────────────────────
def fetch_makemytrip_hotels(city: str, limit: int = 30) -> List[Dict]:
    """
    Scrape hotel listings from MakeMyTrip for a given city.
    Returns list of dicts: name, address, rating, price_per_night, amenities, source.
    """
    city_slug = city.lower().replace(' ', '-')
    url = f"https://www.makemytrip.com/hotels/{city_slug}-hotels.html"
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    hotels = []

    # MMT hotel cards (class names may change; multiple selectors tried)
    cards = (
        soup.select('li.hotel-tile') or
        soup.select('div[class*="hotelCard"]') or
        soup.select('div[class*="listingCard"]') or
        soup.select('div.srpHotelCard')
    )

    for card in cards[:limit]:
        name_el = (
            card.select_one('[class*="hotelName"]') or
            card.select_one('p.hotel-name') or
            card.select_one('h3') or
            card.select_one('h2')
        )
        price_el = (
            card.select_one('[class*="priceVal"]') or
            card.select_one('[class*="price"]') or
            card.select_one('p.price')
        )
        rating_el = (
            card.select_one('[class*="rating"]') or
            card.select_one('[class*="score"]')
        )
        addr_el = (
            card.select_one('[class*="locality"]') or
            card.select_one('[class*="address"]') or
            card.select_one('p.address')
        )
        name = name_el.get_text(strip=True) if name_el else ''
        if not name or len(name) < 3:
            continue
        hotels.append({
            'name':            name,
            'city':            city,
            'address':         addr_el.get_text(strip=True) if addr_el else '',
            'price_per_night': _clean_price(price_el.get_text() if price_el else ''),
            'rating':          _clean_rating(rating_el.get_text() if rating_el else ''),
            'source':          'MakeMyTrip',
            'source_url':      url,
            'confidence':      85,
        })

    logger.info(f"MakeMyTrip: {len(hotels)} hotels found for {city}")
    return hotels


# ─────────────────────────────────────────────────────────────────────────
# Goibibo
# ─────────────────────────────────────────────────────────────────────────
def fetch_goibibo_hotels(city: str, limit: int = 30) -> List[Dict]:
    city_slug = city.lower().replace(' ', '_')
    url = f"https://www.goibibo.com/hotels/hotels-in-{city_slug}/"
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    hotels = []

    cards = (
        soup.select('li[class*="hotel"]') or
        soup.select('div[class*="HotelCard"]') or
        soup.select('div[class*="hotelCard"]') or
        soup.select('div[class*="listItem"]')
    )

    for card in cards[:limit]:
        name_el   = card.select_one('[class*="hotelName"]') or card.select_one('h3') or card.select_one('h2')
        price_el  = card.select_one('[class*="price"]') or card.select_one('[class*="Price"]')
        rating_el = card.select_one('[class*="rating"]') or card.select_one('[class*="Rating"]')
        addr_el   = card.select_one('[class*="locality"]') or card.select_one('[class*="address"]')
        name = name_el.get_text(strip=True) if name_el else ''
        if not name or len(name) < 3:
            continue
        hotels.append({
            'name':            name,
            'city':            city,
            'address':         addr_el.get_text(strip=True) if addr_el else '',
            'price_per_night': _clean_price(price_el.get_text() if price_el else ''),
            'rating':          _clean_rating(rating_el.get_text() if rating_el else ''),
            'source':          'Goibibo',
            'source_url':      url,
            'confidence':      85,
        })

    logger.info(f"Goibibo: {len(hotels)} hotels found for {city}")
    return hotels


# ─────────────────────────────────────────────────────────────────────────
# Yatra
# ─────────────────────────────────────────────────────────────────────────
def fetch_yatra_hotels(city: str, limit: int = 30) -> List[Dict]:
    city_slug = city.lower().replace(' ', '-')
    url = f"https://www.yatra.com/hotels/{city_slug}"
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    hotels = []

    cards = (
        soup.select('div[class*="hotel-card"]') or
        soup.select('div[class*="hotelCard"]') or
        soup.select('li.hotel-item') or
        soup.select('div.hotel-item')
    )

    for card in cards[:limit]:
        name_el   = card.select_one('[class*="hotel-name"]') or card.select_one('h3') or card.select_one('h2')
        price_el  = card.select_one('[class*="price"]')
        rating_el = card.select_one('[class*="rating"]')
        addr_el   = card.select_one('[class*="address"]') or card.select_one('[class*="locality"]')
        name = name_el.get_text(strip=True) if name_el else ''
        if not name or len(name) < 3:
            continue
        hotels.append({
            'name':            name,
            'city':            city,
            'address':         addr_el.get_text(strip=True) if addr_el else '',
            'price_per_night': _clean_price(price_el.get_text() if price_el else ''),
            'rating':          _clean_rating(rating_el.get_text() if rating_el else ''),
            'source':          'Yatra',
            'source_url':      url,
            'confidence':      85,
        })

    logger.info(f"Yatra: {len(hotels)} hotels found for {city}")
    return hotels


# ─────────────────────────────────────────────────────────────────────────
# Booking.com
# ─────────────────────────────────────────────────────────────────────────
def fetch_booking_hotels(city: str, limit: int = 30) -> List[Dict]:
    url = "https://www.booking.com/searchresults/in/in.html"
    params = {
        'ss': city,
        'lang': 'en-gb',
        'sb': 1,
        'src_elem': 'sb',
        'src': 'searchresults',
    }
    resp = _get(url, params=params, extra_headers={'Accept-Language': 'en-GB,en;q=0.9'})
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    hotels = []

    cards = (
        soup.select('div[data-testid="property-card"]') or
        soup.select('[data-testid="property-card-container"]') or
        soup.select('div.sr_item')
    )

    for card in cards[:limit]:
        name_el   = card.select_one('[data-testid="title"]') or card.select_one('span.sr-hotel__name')
        price_el  = card.select_one('[data-testid="price-and-discounted-price"]') or card.select_one('div.bui-price-display__value')
        rating_el = card.select_one('[data-testid="review-score"]') or card.select_one('div.bui-review-score__badge')
        addr_el   = card.select_one('[data-testid="address"]') or card.select_one('span.sr_card_address_line')
        name = name_el.get_text(strip=True) if name_el else ''
        if not name or len(name) < 3:
            continue
        hotels.append({
            'name':            name,
            'city':            city,
            'address':         addr_el.get_text(strip=True) if addr_el else '',
            'price_per_night': _clean_price(price_el.get_text() if price_el else ''),
            'rating':          _clean_rating(rating_el.get_text() if rating_el else ''),
            'source':          'Booking.com',
            'source_url':      resp.url,
            'confidence':      90,
        })

    logger.info(f"Booking.com: {len(hotels)} hotels found for {city}")
    return hotels


# ─────────────────────────────────────────────────────────────────────────
# OYO
# ─────────────────────────────────────────────────────────────────────────
def fetch_oyo_hotels(city: str, limit: int = 30) -> List[Dict]:
    city_slug = city.lower().replace(' ', '-')
    url = f"https://www.oyo.com/hotels/{city_slug}"
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, 'lxml')
    hotels = []

    cards = (
        soup.select('div[class*="PropertyCard"]') or
        soup.select('div[class*="hotel-card"]') or
        soup.select('li[class*="property"]')
    )

    for card in cards[:limit]:
        name_el   = card.select_one('[class*="propertyName"]') or card.select_one('h3') or card.select_one('h2')
        price_el  = card.select_one('[class*="price"]') or card.select_one('[class*="Price"]')
        rating_el = card.select_one('[class*="rating"]') or card.select_one('[class*="Rating"]')
        addr_el   = card.select_one('[class*="locality"]') or card.select_one('[class*="address"]')
        name = name_el.get_text(strip=True) if name_el else ''
        if not name or len(name) < 3:
            continue
        hotels.append({
            'name':            name,
            'city':            city,
            'address':         addr_el.get_text(strip=True) if addr_el else '',
            'price_per_night': _clean_price(price_el.get_text() if price_el else ''),
            'rating':          _clean_rating(rating_el.get_text() if rating_el else ''),
            'source':          'OYO',
            'source_url':      url,
            'confidence':      88,
        })

    logger.info(f"OYO: {len(hotels)} hotels found for {city}")
    return hotels


# ─────────────────────────────────────────────────────────────────────────
# Unified fetcher — calls all portals for a city and merges results
# ─────────────────────────────────────────────────────────────────────────
ACTIVE_PORTALS = [
    ('MakeMyTrip', fetch_makemytrip_hotels),
    ('Goibibo',    fetch_goibibo_hotels),
    ('Yatra',      fetch_yatra_hotels),
    ('Booking.com',fetch_booking_hotels),
    ('OYO',        fetch_oyo_hotels),
]


def fetch_all_portals(city: str, per_portal: int = 30) -> List[Dict]:
    """
    Fetch hotels for a city from ALL portals and return merged unique list.
    Deduplicates by normalised name.
    """
    all_hotels = []
    seen_names = set()

    for portal_name, fetcher in ACTIVE_PORTALS:
        try:
            hotels = fetcher(city, limit=per_portal)
            for h in hotels:
                key = re.sub(r'[^a-z0-9]', '', h['name'].lower())
                if key not in seen_names:
                    seen_names.add(key)
                    all_hotels.append(h)
        except Exception as e:
            logger.error(f"Portal {portal_name} failed for {city}: {e}")

    logger.info(f"Total portal hotels for {city}: {len(all_hotels)} (deduplicated)")
    return all_hotels
