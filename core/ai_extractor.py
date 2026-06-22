"""
Nexuzy Data Collector - AI Extractor
Auto-detects any cached HuggingFace model.
Falls back to rule-based extraction if no model available.
"""

import os
import re
import json
from loguru import logger
from typing import Dict, Any

MODEL_CACHE_DIR = 'models/hf_cache'

# Models ranked best-to-worst for extraction quality on CPU.
# The first one found in cache wins.
PREFERRED_MODELS = [
    'TinyLlama--TinyLlama-1.1B-Chat-v1.0',
    'Qwen--Qwen2-0.5B-Instruct',
    'Qwen--Qwen2-1.5B-Instruct',
    'microsoft--phi-2',
    'microsoft--Phi-3-mini-4k-instruct',
    'google--gemma-2-2b-it',   # last resort: heavy, slow on CPU
    'google--gemma-2-9b-it',
]


def detect_cached_model(cache_dir: str = MODEL_CACHE_DIR) -> str:
    """
    Scan the HF cache folder and return the best available model id.
    Prefers lightweight models (TinyLlama, Qwen) over heavy ones (Gemma).
    Returns '' if nothing found.
    """
    if not os.path.exists(cache_dir):
        return ''

    available = [
        d for d in os.listdir(cache_dir)
        if os.path.isdir(os.path.join(cache_dir, d))
        and len(os.listdir(os.path.join(cache_dir, d))) > 0
    ]
    if not available:
        return ''

    # Pick by preference order
    for preferred in PREFERRED_MODELS:
        if preferred in available:
            model_id = preferred.replace('--', '/', 1)
            logger.info(f'Auto-detected model (preferred): {model_id}')
            return model_id

    # Fall back to first found
    model_id = available[0].replace('--', '/', 1)
    logger.info(f'Auto-detected model (first found): {model_id}')
    return model_id


class AIExtractor:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.pipeline = None
        self.model_loaded = False
        self._try_load_model()

    def _try_load_model(self):
        model_cfg = self.config.get('model', {})
        cache_dir = model_cfg.get('cache_dir', MODEL_CACHE_DIR)

        # 1. Explicit model set in config (skip local/ GGUF refs)
        explicit = model_cfg.get('hf_model', '')
        if explicit.startswith('local/'):
            explicit = ''

        # 2. Auto-detect from cache if nothing explicit
        model_name = explicit or detect_cached_model(cache_dir)

        if not model_name:
            logger.info('No HF model found. Using rule-based extraction.')
            return

        try:
            from transformers import pipeline as hf_pipeline
            import torch
            device    = 0 if torch.cuda.is_available() else -1
            local_dir = os.path.join(cache_dir, model_name.replace('/', '--'))
            load_from = local_dir if os.path.exists(local_dir) else model_name
            logger.info(
                f'Loading model: {model_name} | '
                f'source: {load_from} | '
                f'device: {"GPU" if device == 0 else "CPU"}'
            )
            self.pipeline = hf_pipeline(
                'text-generation',
                model=load_from,
                device=device,
                max_new_tokens=512,
                do_sample=False,
            )
            self.model_loaded = True
            logger.success(f'AI model loaded: {model_name}')
        except ImportError:
            logger.warning('torch/transformers not installed. Using rule-based extraction.')
        except Exception as e:
            logger.warning(f'AI model not loaded ({e}). Using rule-based extraction.')

    # ------------------------------------------------------------------
    def categorize_url(self, url: str, text: str = '') -> str:
        url_lower  = url.lower()
        text_lower = (text or '').lower()[:500]
        combined   = url_lower + ' ' + text_lower
        scores = {
            'hotel':         sum(1 for k in ['hotel','resort','lodge','inn','hostel','homestay','accommodation','stay','rooms','booking'] if k in combined),
            'tourist_place': sum(1 for k in ['temple','fort','palace','museum','waterfall','park','beach','hill','trek','wildlife','sanctuary','monument','tourist','attraction','sightseeing','destination'] if k in combined),
            'restaurant':    sum(1 for k in ['restaurant','cafe','food','dining','eatery','cuisine','menu','diner','bistro','dhaba'] if k in combined),
            'guide':         sum(1 for k in ['guide','travel','itinerary','tips','blog','things-to-do','how-to-reach','best-time','tour','visit'] if k in combined),
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'unknown'

    def _extract_city(self, text: str) -> str:
        cities = [
            'Kolkata','Mumbai','Delhi','Bangalore','Chennai','Hyderabad','Pune',
            'Ahmedabad','Jaipur','Lucknow','Agra','Varanasi','Darjeeling','Goa',
            'Manali','Shimla','Ooty','Munnar','Udaipur','Jodhpur','Jaisalmer',
            'Kochi','Mysuru','Coorg','Rishikesh','Haridwar','Leh','Srinagar',
            'Gangtok','Puri','Siliguri','Durgapur','Asansol','Howrah','Bhubaneswar',
            'Patna','Ranchi','Guwahati','Shillong',
        ]
        tl = text.lower()
        for city in cities:
            if city.lower() in tl:
                return city
        return ''

    def extract(self, text: str, entity_type: str = 'hotel') -> Dict[str, Any]:
        if not text or len(text.strip()) < 20:
            return {}
        if self.model_loaded and self.pipeline:
            return self._ai_extract(text, entity_type)
        return self._rule_extract(text, entity_type)

    def _ai_extract(self, text: str, entity_type: str) -> Dict[str, Any]:
        prompt = self._build_prompt(text[:1200], entity_type)
        try:
            result = self.pipeline(prompt)[0]['generated_text']
            json_match = re.search(r'\{[^{}]+\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f'AI extraction failed: {e}')
        return self._rule_extract(text, entity_type)

    def _build_prompt(self, text: str, entity_type: str) -> str:
        fields = {
            'hotel':         'name, city, state, address, price_range, rating, contact, website, description',
            'place':         'name, city, state, address, category, description, entry_fee, timings',
            'tourist_place': 'name, city, state, address, category, description, entry_fee, timings',
            'restaurant':    'name, city, state, address, cuisine, price_range, rating, contact',
        }.get(entity_type, 'name, city, state, description')
        return (
            f'Extract travel info from this text, return only JSON with fields: {fields}.\n'
            f'Text: {text}\nJSON:'
        )

    def _rule_extract(self, text: str, entity_type: str) -> Dict[str, Any]:
        result = {}
        name_match = re.search(r'<h[1-3][^>]*>([^<]{3,80})</h[1-3]>', text)
        if not name_match:
            name_match = re.search(r'\*\*([^*]{3,80})\*\*', text)
        if not name_match:
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 4]
            result['name'] = lines[0][:80] if lines else ''
        else:
            result['name'] = name_match.group(1).strip()[:80]

        price = re.search(r'(?:Rs\.?|INR|\u20b9)\s*([\d,]+)', text, re.IGNORECASE)
        if price:
            result['price_range'] = price.group(0).strip()[:60]

        rating = re.search(r'(\d\.\d)\s*(?:/\s*5|stars?|rating)', text, re.IGNORECASE)
        if rating:
            result['rating'] = float(rating.group(1))

        phone = re.search(r'(?:\+91[\s-]?)?[6-9]\d{9}|\d{2,4}[\s-]\d{6,8}', text)
        if phone:
            result['contact'] = phone.group(0).strip()

        website = re.search(r'https?://[\w./\-]+', text)
        if website:
            result['website'] = website.group(0).strip()

        city = self._extract_city(text)
        if city:
            result['city'] = city

        for state in [
            'West Bengal','Rajasthan','Kerala','Goa','Himachal Pradesh',
            'Uttarakhand','Tamil Nadu','Gujarat','Maharashtra','Karnataka',
            'Odisha','Assam','Sikkim','Uttar Pradesh','Madhya Pradesh',
            'Bihar','Punjab','Haryana','Delhi','Ladakh'
        ]:
            if state.lower() in text.lower():
                result['state'] = state
                break

        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        paras = [p.strip() for p in clean.split('. ') if len(p.strip()) > 40]
        if paras:
            result['description'] = '. '.join(paras[:3])[:500]

        result['source_type'] = 'rule_based'
        result['confidence']  = 60
        return result

    def batch_extract(self, texts: list, entity_type: str = 'hotel') -> list:
        return [self.extract(t, entity_type) for t in texts if t]
