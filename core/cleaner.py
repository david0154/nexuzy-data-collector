import re
import html
from typing import Optional


class DataCleaner:
    def clean_text(self, text: str) -> str:
        if not text:
            return ''
        text = html.unescape(text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def clean_price(self, price_str: str) -> Optional[float]:
        if not price_str:
            return None
        cleaned = re.sub(r'[^\d.]', '', str(price_str))
        try:
            return float(cleaned)
        except ValueError:
            return None

    def clean_phone(self, phone: str) -> str:
        if not phone:
            return ''
        cleaned = re.sub(r'[^\d+\-\s()]', '', phone)
        return cleaned.strip()

    def clean_name(self, name: str) -> str:
        if not name:
            return ''
        name = self.clean_text(name)
        name = re.sub(r'\s{2,}', ' ', name)
        return name.strip().title()

    def clean_address(self, address: str) -> str:
        return self.clean_text(address)

    def clean_rating(self, rating_str: str) -> Optional[float]:
        if not rating_str:
            return None
        m = re.search(r'(\d+\.?\d*)', str(rating_str))
        if m:
            val = float(m.group(1))
            if val > 10:
                return None
            if val > 5:
                return round(val / 2, 1)
            return round(val, 1)
        return None

    def clean_hotel(self, data: dict) -> dict:
        return {
            'name': self.clean_name(data.get('hotel_name') or data.get('name', '')),
            'city': self.clean_text(data.get('city', '')),
            'district': self.clean_text(data.get('district', '')),
            'state': self.clean_text(data.get('state', 'India')),
            'address': self.clean_address(data.get('address', '')),
            'description': self.clean_text(data.get('description', ''))[:1000],
            'price_min': self.clean_price(data.get('price_min')),
            'price_max': self.clean_price(data.get('price_max')),
            'category': self.clean_text(data.get('category', '')),
            'amenities': self.clean_text(data.get('amenities', '')),
            'contact': self.clean_phone(data.get('contact', '')),
            'website': data.get('website', '') or data.get('sources', [''])[0] if data.get('sources') else '',
            'rating': self.clean_rating(data.get('rating')),
            'sources': data.get('sources', []),
            'verified': data.get('verified', 0),
            'confidence': data.get('confidence', 0),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude')
        }

    def clean_tourist_place(self, data: dict) -> dict:
        return {
            'name': self.clean_name(data.get('name', '')),
            'city': self.clean_text(data.get('city', '')),
            'district': self.clean_text(data.get('district', '')),
            'state': self.clean_text(data.get('state', 'India')),
            'address': self.clean_address(data.get('address', '')),
            'description': self.clean_text(data.get('description', ''))[:1000],
            'category': self.clean_text(data.get('category', '')),
            'entry_fee': self.clean_text(data.get('entry_fee', '')),
            'timings': self.clean_text(data.get('timings', '')),
            'best_time_to_visit': self.clean_text(data.get('best_time_to_visit', '')),
            'rating': self.clean_rating(data.get('rating')),
            'sources': data.get('sources', []),
            'verified': data.get('verified', 0),
            'confidence': data.get('confidence', 0),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude')
        }

    def clean_restaurant(self, data: dict) -> dict:
        return {
            'name': self.clean_name(data.get('name', '')),
            'city': self.clean_text(data.get('city', '')),
            'district': self.clean_text(data.get('district', '')),
            'state': self.clean_text(data.get('state', 'India')),
            'address': self.clean_address(data.get('address', '')),
            'description': self.clean_text(data.get('description', ''))[:800],
            'cuisine': self.clean_text(data.get('cuisine', '')),
            'price_range': self.clean_text(data.get('price_range', '')),
            'contact': self.clean_phone(data.get('contact', '')),
            'timings': self.clean_text(data.get('timings', '')),
            'rating': self.clean_rating(data.get('rating')),
            'sources': data.get('sources', []),
            'verified': data.get('verified', 0),
            'confidence': data.get('confidence', 0),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude')
        }
