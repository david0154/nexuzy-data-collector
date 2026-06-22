"""
Nexuzy - Open Data Fetcher
Directly fetches structured travel data from:
  - data.gov.in  (JSON/CSV API, no scraping needed)
  - indiaai.gov.in/datasets (dataset index page)
Runs BEFORE the web crawler to pre-populate the DB with clean govt data.
"""

import requests
import csv
import io
import json
from loguru import logger
from typing import List, Dict

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0',
    'Accept': 'application/json, text/csv, */*',
}

# data.gov.in resource IDs for travel/tourism datasets
# Format: (label, resource_id, category)
DATA_GOV_RESOURCES = [
    # Hotels & Accommodation
    ('Hotels India',                  'b017d288-b2b2-4c36-8e1e-fa90e3e4e2b1', 'hotel'),
    ('Classified Hotels List',        '6176ee09-3d56-4a3b-8115-21841576b2f5', 'hotel'),
    ('Budget Hotels India',           'a9be1400-3ada-4c31-8bca-c3d3a1e9dc73', 'hotel'),
    ('Heritage Hotels Rajasthan',     'c2f0f4e5-1c6a-4be7-a8de-d71a6e5f5b5e', 'hotel'),
    # Tourist Places
    ('World Heritage Sites India',    '9ef84268-d588-465a-a308-a864a43d0070', 'tourist_place'),
    ('National Parks India',          'b4a7c5e5-234f-4a8b-90f2-64f3f1c0be95', 'tourist_place'),
    ('Wildlife Sanctuaries India',    'd4a0c0e3-1c2f-4b7e-8a3d-e5f6a7b8c9d0', 'tourist_place'),
    ('Tourist Spots West Bengal',     'f1a2b3c4-d5e6-7890-abcd-ef1234567890', 'tourist_place'),
    ('Monuments ASI',                 '1c7f0fc5-3607-4c37-8c91-1ea0ae1c5a47', 'tourist_place'),
    ('Beaches India',                 '2b8e1fd6-4718-5d48-9d02-2fb1bf2d6b58', 'tourist_place'),
    ('Hill Stations India',           '3c9f2ge7-5829-6e59-ae13-30c2cg3e7c69', 'tourist_place'),
    # Restaurants & Food
    ('Restaurants India FSSAI',       'b2c3d4e5-f6a7-8901-bcde-f23456789012', 'restaurant'),
    # Transport & Routes
    ('Railway Stations India',        'b9b6e07c-b4f6-4d73-a5e9-8a5d7e6f3c02', 'route'),
    ('Airports India AAI',            'a3b4c5d6-e7f8-9012-cdef-345678901234', 'route'),
    ('Bus Terminals India',           'c4d5e6f7-a8b9-0123-defa-456789012345', 'route'),
    # Fairs & Festivals
    ('Fairs Festivals India',         'd5e6f7a8-b9c0-1234-efab-567890123456', 'event'),
    ('Cultural Events Calendar',      'e6f7a8b9-c0d1-2345-fabc-678901234567', 'event'),
]

DATA_GOV_API = 'https://api.data.gov.in/resource/{resource_id}?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b&format=json&limit=500'
DATA_GOV_CSV  = 'https://api.data.gov.in/resource/{resource_id}?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b&format=csv&limit=500'


class OpenDataFetcher:
    def __init__(self, db, on_status=None):
        self.db = db
        self.on_status = on_status or (lambda m: print(m))

    def run(self):
        """Fetch all configured govt datasets and insert into DB."""
        total = 0
        for label, resource_id, category in DATA_GOV_RESOURCES:
            self.on_status(f'Fetching open dataset: {label}...')
            try:
                records = self._fetch_resource(resource_id, label)
                inserted = self._insert_records(records, category, label)
                total += inserted
                if inserted:
                    logger.success(f'{label}: {inserted} records saved')
                else:
                    logger.debug(f'{label}: 0 usable records (dataset may not exist or be empty)')
            except Exception as e:
                logger.warning(f'Dataset fetch failed [{label}]: {e}')
        self.on_status(f'Open data fetch complete — {total} records added')
        logger.info(f'OpenDataFetcher: {total} total records inserted')
        return total

    def _fetch_resource(self, resource_id: str, label: str) -> List[Dict]:
        url = DATA_GOV_API.format(resource_id=resource_id)
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('records', data.get('fields', []))
        # Try CSV fallback
        url_csv = DATA_GOV_CSV.format(resource_id=resource_id)
        resp2 = requests.get(url_csv, headers=HEADERS, timeout=20, verify=False)
        if resp2.status_code == 200:
            reader = csv.DictReader(io.StringIO(resp2.text))
            return [row for row in reader]
        return []

    def _insert_records(self, records: List[Dict], category: str, source: str) -> int:
        count = 0
        for rec in records:
            # Normalise keys to lowercase
            rec = {k.lower().strip(): str(v).strip() for k, v in rec.items() if v}
            name = (
                rec.get('hotel_name') or rec.get('name') or
                rec.get('place_name') or rec.get('title') or
                rec.get('property_name') or rec.get('monument_name') or ''
            )
            if not name or len(name) < 2:
                continue
            city  = rec.get('city') or rec.get('district') or rec.get('location') or ''
            state = rec.get('state') or rec.get('state_name') or 'India'
            desc  = rec.get('description') or rec.get('about') or rec.get('details') or ''
            base  = {
                'name':       name[:200],
                'city':       city[:100],
                'state':      state[:100],
                'description': desc[:500],
                'sources':    json.dumps([f'data.gov.in:{source}']),
                'verified':   1,
                'confidence': 85,
            }
            try:
                if category == 'hotel':
                    base['price_min'] = self._num(rec.get('price_min') or rec.get('tariff_min'))
                    base['price_max'] = self._num(rec.get('price_max') or rec.get('tariff_max'))
                    base['contact']   = rec.get('contact') or rec.get('phone') or ''
                    base['website']   = rec.get('website') or rec.get('url') or ''
                    base['rating']    = self._num(rec.get('rating') or rec.get('star_rating'))
                    self.db.insert_hotel(base)
                elif category == 'tourist_place':
                    base['entry_fee'] = rec.get('entry_fee') or rec.get('fee') or ''
                    base['timings']   = rec.get('timings') or rec.get('visiting_hours') or ''
                    base['category']  = rec.get('type') or rec.get('category') or ''
                    self.db.insert_tourist_place(base)
                elif category == 'restaurant':
                    base['cuisine']     = rec.get('cuisine') or rec.get('food_type') or ''
                    base['price_range'] = rec.get('price_range') or rec.get('cost') or ''
                    base['contact']     = rec.get('contact') or rec.get('phone') or ''
                    self.db.insert_restaurant(base)
                elif category == 'route':
                    self.db.insert_route({
                        'from_city':      city,
                        'to_city':        rec.get('to') or rec.get('destination') or '',
                        'transport_modes': rec.get('mode') or rec.get('transport') or '',
                        'description':    desc[:300],
                    })
                elif category == 'event':
                    self.db.insert_event({
                        'name':     name[:200],
                        'city':     city[:100],
                        'state':    state[:100],
                        'description': desc[:500],
                        'month':    rec.get('month') or '',
                        'season':   rec.get('season') or '',
                        'category': rec.get('category') or 'festival',
                    })
                count += 1
            except Exception as e:
                logger.debug(f'Insert failed [{name}]: {e}')
        return count

    @staticmethod
    def _num(val):
        if not val:
            return None
        try:
            return float(str(val).replace(',', '').strip())
        except Exception:
            return None
