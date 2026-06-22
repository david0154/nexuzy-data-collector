import schedule
import time
import threading
from loguru import logger


class CrawlerScheduler:
    def __init__(self, pipeline_factory, config: dict):
        self.pipeline_factory = pipeline_factory
        self.config = config
        self._thread = None
        self._running = False

    def schedule_daily(self, hour: int = 2, minute: int = 0):
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self._run_crawl)
        logger.info(f"Crawler scheduled daily at {hour:02d}:{minute:02d}")

    def schedule_hourly(self):
        schedule.every().hour.do(self._run_crawl)
        logger.info("Crawler scheduled every hour")

    def _run_crawl(self):
        logger.info("Scheduled crawl starting...")
        seed_urls = self.config.get('sources', {}).get('seed_urls', [])
        pipeline = self.pipeline_factory()
        pipeline.start(seed_urls)
        logger.info("Scheduled crawl finished")

    def start_background(self):
        self._running = True

        def loop():
            while self._running:
                schedule.run_pending()
                time.sleep(30)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler background thread started")

    def stop(self):
        self._running = False
        schedule.clear()
        logger.info("Scheduler stopped")
