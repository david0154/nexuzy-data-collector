import json
import os
from loguru import logger
from core.database import Database


TRAINING_TEMPLATES = [
    {"instruction": "Best hotels in {city}", "table": "hotels", "filter": "city", "output_field": "description"},
    {"instruction": "Places to visit in {city}", "table": "tourist_places", "filter": "city", "output_field": "description"},
    {"instruction": "Best restaurants in {city}", "table": "restaurants", "filter": "city", "output_field": "description"},
    {"instruction": "What is {name}?", "table": "tourist_places", "filter": "name", "output_field": "description"},
    {"instruction": "Tell me about {name} hotel", "table": "hotels", "filter": "name", "output_field": "description"},
]


class DatasetBuilder:
    def __init__(self, db: Database, output_dir: str = "export"):
        self.db = db
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def build_training_dataset(self) -> list:
        dataset = []
        # Hotels
        hotels = self.db.get_all('hotels', limit=10000)
        for h in hotels:
            if h.get('city') and h.get('description'):
                dataset.append({
                    "instruction": f"Best hotels in {h['city']}",
                    "input": "",
                    "output": f"{h.get('name', '')} - {h.get('description', '')}. Price from ₹{h.get('price_min', 'N/A')}."
                })
            if h.get('name') and h.get('description'):
                dataset.append({
                    "instruction": f"Tell me about {h['name']}",
                    "input": "",
                    "output": h.get('description', '') + f" Located in {h.get('city', '')}."
                })

        # Tourist Places
        places = self.db.get_all('tourist_places', limit=10000)
        for p in places:
            if p.get('city') and p.get('description'):
                dataset.append({
                    "instruction": f"Places to visit in {p['city']}",
                    "input": "",
                    "output": f"{p.get('name', '')} - {p.get('description', '')}"
                })
            if p.get('name') and p.get('best_time_to_visit'):
                dataset.append({
                    "instruction": f"When is the best time to visit {p['name']}?",
                    "input": "",
                    "output": p['best_time_to_visit']
                })

        # Restaurants
        restaurants = self.db.get_all('restaurants', limit=10000)
        for r in restaurants:
            if r.get('city') and r.get('name'):
                dataset.append({
                    "instruction": f"Best restaurants in {r['city']}",
                    "input": "",
                    "output": f"{r['name']} - {r.get('cuisine', 'Indian')} cuisine. {r.get('description', '')}"
                })

        # Routes
        routes = self.db.get_all('routes', limit=5000)
        for rt in routes:
            if rt.get('from_city') and rt.get('to_city'):
                dataset.append({
                    "instruction": f"How to travel from {rt['from_city']} to {rt['to_city']}?",
                    "input": "",
                    "output": f"Distance: {rt.get('distance_km', 'N/A')} km. Travel time: {rt.get('travel_time', 'N/A')}. Modes: {rt.get('transport_modes', 'N/A')}. Cost: {rt.get('cost_estimate', 'N/A')}."
                })

        # Events
        events = self.db.get_all('events', limit=5000)
        for e in events:
            if e.get('name') and e.get('description'):
                dataset.append({
                    "instruction": f"Tell me about {e['name']} festival",
                    "input": "",
                    "output": e.get('description', '')
                })

        logger.info(f"Dataset built with {len(dataset)} training samples")
        return dataset

    def save_jsonl(self, dataset: list, filename: str = "training_data.jsonl") -> str:
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info(f"Saved {len(dataset)} samples to {path}")
        return path

    def build_and_save(self) -> str:
        dataset = self.build_training_dataset()
        return self.save_jsonl(dataset)
