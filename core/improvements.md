# Nexuzy Data Collector - Improvements Roadmap

## v1.1 - Completed in this version
- [x] 120+ seed URLs across all categories
- [x] Categorized sources catalog (sources_catalog.py)
- [x] Priority-based crawling order
- [x] All 28 state tourism boards added

---

## v1.2 - Recommended Next Improvements

### 1. OpenStreetMap (OSM) Direct API Integration
- Query Overpass API for hotels, restaurants, tourist spots directly
- Zero scraping needed, structured geo-data, 100% free
- Example query: all hotels in West Bengal with coordinates

```python
# Add to core/osm_fetcher.py
import requests
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
query = """
[out:json];
area["name"="West Bengal"]->.wb;
(node["tourism"="hotel"](area.wb);
 way["tourism"="hotel"](area.wb););
out body;
"""
```

### 2. Wikipedia API for Places
- Wikipedia has structured data for every Indian city, temple, fort
- Free, no scraping, highly reliable
- Use MediaWiki API + DBpedia

```python
import wikipedia
wikipedia.set_lang("en")
page = wikipedia.page("Darjeeling")
text = page.content  # clean structured text
```

### 3. Google Places API (Optional Paid)
- If budget allows: structured data for hotels, restaurants
- Ratings, reviews, coordinates, photos, opening hours
- 200 USD/month free credit covers millions of lookups

### 4. Proxy Rotation System
- Add rotating proxies to avoid IP bans on heavy crawling
- Free: Tor network, public proxy lists
- Paid: BrightData, Oxylabs

```python
# Add to core/proxy_manager.py
ROTATING_PROXIES = [
    "socks5://127.0.0.1:9050",  # Tor
    ...
]
```

### 5. Rate Limiter with Domain Buckets
- Per-domain rate limiting (not global)
- Prevents getting blocked by specific sites
- Token bucket algorithm

### 6. Image Downloader
- Download hotel/place cover images
- Store as base64 or file path in DB
- Enrich training data with image captions

### 7. Multilingual Extraction
- Many Indian tourism sites are in Hindi, Bengali, Tamil
- Add language detection + translation pipeline
- Use googletrans or deep_translator (pure Python)

### 8. Auto-Scheduler UI Tab
- Schedule crawls: hourly / daily / weekly
- Show next run time in Dashboard
- Email/notification on completion

### 9. Duplicate Detection Improvements
- Current: FuzzyWuzzy token sort ratio
- Upgrade: sentence-transformers embeddings for semantic dedup
- SQLite FTS5 for fast full-text search

### 10. REST API Server
- Add FastAPI server alongside Tkinter UI
- Expose /hotels, /places, /routes endpoints
- Let Atithi AI query the DB directly via HTTP

### 11. Price Trend Tracker
- Re-crawl hotel pages weekly
- Track price changes over time
- Store historical prices in separate table

### 12. Training Data Quality Scorer
- Score each training sample 1-5 based on:
  - Description length
  - Has price
  - Has coordinates
  - Verified flag
  - Confidence score
- Filter low-quality samples before export

### 13. Maps Tab Improvement
- Add interactive map using tkintermapview
- Plot all hotels/places as pins on India map
- Color-coded by category

```bash
pip install tkintermapview
```

### 14. RSS Feed Crawler
- Add RSS feed parser for travel blogs and news
- Automatic new content discovery
- feedparser library (pure Python)

```python
import feedparser
feed = feedparser.parse("https://www.holidify.com/feed")
```

### 15. Data Export to Hugging Face
- Auto-push training_data.jsonl to HuggingFace datasets
- huggingface_hub Python library
- Enables Atithi AI to pull latest training data automatically

---

## Priority Order for David

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 1 | OSM Overpass API | Low | Very High |
| 2 | Wikipedia API | Low | Very High |
| 3 | RSS Feed Crawler | Low | High |
| 4 | Maps Tab (tkintermapview) | Medium | High |
| 5 | Multilingual Extraction | Medium | High |
| 6 | Rate Limiter per Domain | Medium | High |
| 7 | Training Data Quality Scorer | Low | High |
| 8 | REST API (FastAPI) | Medium | Medium |
| 9 | Proxy Rotation | Medium | Medium |
| 10 | HuggingFace Export | Low | Medium |
