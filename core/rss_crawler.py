import feedparser
from loguru import logger
from typing import List, Dict
from newspaper import Article


DEFAULT_RSS_FEEDS = [
    "https://www.holidify.com/feed",
    "https://www.thrillophilia.com/blog/feed",
    "https://traveltriangle.com/blog/feed",
    "https://www.goibibo.com/blog/feed",
]


class RSSCrawler:
    def __init__(self, feeds: List[str] = None):
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    def fetch_feed_entries(self, feed_url: str, limit: int = 20) -> List[Dict]:
        try:
            parsed = feedparser.parse(feed_url)
            items = []
            for entry in parsed.entries[:limit]:
                items.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'source_feed': feed_url,
                })
            return items
        except Exception as e:
            logger.error(f"RSS fetch failed for {feed_url}: {e}")
            return []

    def fetch_all_entries(self, limit_per_feed: int = 20) -> List[Dict]:
        all_items = []
        for feed in self.feeds:
            all_items.extend(self.fetch_feed_entries(feed, limit=limit_per_feed))
        logger.info(f"Fetched {len(all_items)} RSS entries from {len(self.feeds)} feeds")
        return all_items

    def extract_article(self, url: str) -> Dict:
        try:
            article = Article(url)
            article.download()
            article.parse()
            return {
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': str(article.publish_date) if article.publish_date else '',
                'top_image': article.top_image,
                'source_url': url,
            }
        except Exception as e:
            logger.error(f"Article extraction failed for {url}: {e}")
            return {
                'title': '',
                'text': '',
                'authors': [],
                'publish_date': '',
                'top_image': '',
                'source_url': url,
            }

    def fetch_and_extract_all(self, limit_per_feed: int = 10) -> List[Dict]:
        entries = self.fetch_all_entries(limit_per_feed=limit_per_feed)
        articles = []
        for item in entries:
            link = item.get('link')
            if not link:
                continue
            art = self.extract_article(link)
            art['rss_title'] = item.get('title', '')
            art['rss_published'] = item.get('published', '')
            art['rss_summary'] = item.get('summary', '')
            art['source_feed'] = item.get('source_feed', '')
            articles.append(art)
        logger.info(f"Extracted {len(articles)} articles from RSS feeds")
        return articles
