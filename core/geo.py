from geopy.geocoders import Nominatim
from loguru import logger
import time
from typing import Optional, Tuple


class GeoLocator:
    def __init__(self):
        self.geocoder = Nominatim(user_agent="NexuzyDataCollector/1.0")
        self._cache = {}

    def get_coordinates(self, location: str, country: str = 'India') -> Optional[Tuple[float, float]]:
        query = f"{location}, {country}"
        if query in self._cache:
            return self._cache[query]
        try:
            time.sleep(1)
            loc = self.geocoder.geocode(query, timeout=10)
            if loc:
                coords = (loc.latitude, loc.longitude)
                self._cache[query] = coords
                return coords
        except Exception as e:
            logger.warning(f"Geocoding failed for '{query}': {e}")
        return None

    def enrich_record(self, record: dict) -> dict:
        if record.get('latitude') and record.get('longitude'):
            return record
        city = record.get('city', '') or record.get('district', '')
        if city:
            coords = self.get_coordinates(city)
            if coords:
                record['latitude'], record['longitude'] = coords
        return record
