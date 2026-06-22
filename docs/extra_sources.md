# Structured Source Modules

This project now includes three extra source modules for better coverage without relying only on HTML scraping.

## Added Modules

### 1. `core/osm_fetcher.py`
Uses the Overpass API to fetch structured OpenStreetMap data.

Supported categories:
- Hotels
- Attractions
- Museums
- Guest houses
- Hostels
- Restaurants
- Cafes
- Temples / places of worship

Example:
```python
from core.osm_fetcher import OSMFetcher
osm = OSMFetcher()
data = osm.fetch_tourism_bundle("West Bengal")
print(data["hotels"][:3])
```

### 2. `core/wikipedia_fetcher.py`
Uses Wikipedia API for clean summaries, categories, URLs, and coordinates.

Example:
```python
from core.wikipedia_fetcher import WikipediaFetcher
wiki = WikipediaFetcher()
place = wiki.get_travel_entity("Darjeeling")
print(place)
```

### 3. `core/rss_crawler.py`
Uses RSS feeds + newspaper3k to fetch fresh travel blog content.

Example:
```python
from core.rss_crawler import RSSCrawler
rss = RSSCrawler()
articles = rss.fetch_and_extract_all(limit_per_feed=5)
print(articles[:2])
```

## Why these help

- **OSM** gives structured geo records with coordinates.
- **Wikipedia** gives reliable summaries and entity context.
- **RSS** gives fresh travel articles for new destinations and seasonal content.

## Recommended next integration

To fully use these in the app, next steps should be:
1. Add import buttons in the Tkinter UI.
2. Save OSM/Wikipedia records into SQLite tables automatically.
3. Merge RSS articles into the `guides` table.
4. Add deduplication between scraped and imported sources.
5. Add a source-type field in the database.
