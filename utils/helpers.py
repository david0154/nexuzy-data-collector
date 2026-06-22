import re
import os
from urllib.parse import urlparse
from typing import Optional


def normalize_url(url: str) -> str:
    url = url.strip().rstrip('/')
    if not url.startswith('http'):
        url = 'https://' + url
    return url


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ''


def truncate(text: str, max_len: int = 200) -> str:
    if not text:
        return ''
    return text[:max_len] + ('...' if len(text) > max_len else '')


def safe_float(val) -> Optional[float]:
    try:
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return None


def safe_int(val) -> Optional[int]:
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def extract_price_inr(text: str) -> Optional[float]:
    patterns = [
        r'₹\s*(\d[\d,]*)',
        r'Rs\.?\s*(\d[\d,]*)',
        r'INR\s*(\d[\d,]*)',
        r'(\d[\d,]*)\s*/\s*night',
        r'(\d[\d,]*)\s*/\s*person',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).replace(',', '')
            try:
                return float(val)
            except ValueError:
                continue
    return None


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path
