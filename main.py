#!/usr/bin/env python3
"""
Nexuzy Data Collector v1.2
AI-Powered Travel Data Collection & Verification System
Nexuzy Tech - David
"""

import os
import sys
import yaml
from loguru import logger


SEED_URLS = [
    # ── Incredible India (official) ──────────────────────────────────────
    'https://www.incredibleindia.gov.in',
    'https://www.incredibleindia.gov.in/destinations',
    'https://www.incredibleindia.gov.in/hotels',
    'https://www.incredibleindia.gov.in/experiences',
    # ── State Tourism Boards ─────────────────────────────────────────────
    'https://www.wbtourism.gov.in',
    'https://www.keralatourism.org',
    'https://www.goatourism.gov.in',
    'https://www.rajasthantourism.gov.in',
    'https://www.hptourism.in',
    'https://uttarakhandtourism.gov.in',
    'https://www.tamilnadutourism.tn.gov.in',
    'https://www.gujarattourism.com',
    'https://www.maharashtratourism.gov.in',
    'https://www.karnatakatourism.org',
    'https://odishatourism.gov.in',
    'https://assamtourism.gov.in',
    'https://sikkimtourism.gov.in',
    'https://www.meghalayatourism.in',
    'https://www.punjabtourism.in',
    'https://www.andhrapradesh-tourism.com',
    'https://www.telanganatourism.gov.in',
    'https://www.uttarpradeshindia.gov.in/tourism',
    # ── data.gov.in ──────────────────────────────────────────────────────
    'https://data.gov.in/search?title=hotel',
    'https://data.gov.in/search?title=tourism',
    'https://data.gov.in/search?title=tourist',
    'https://data.gov.in/search?title=heritage',
    'https://data.gov.in/search?title=monument',
    'https://data.gov.in/search?title=wildlife+sanctuary',
    'https://data.gov.in/search?title=national+park',
    'https://data.gov.in/search?title=restaurant',
    'https://data.gov.in/search?title=festival',
    'https://data.gov.in/search?title=beach',
    'https://data.gov.in/search?title=hill+station',
    'https://data.gov.in/search?title=pilgrimage',
    # ── indiaai.gov.in datasets ──────────────────────────────────────────
    'https://indiaai.gov.in/datasets',
    'https://indiaai.gov.in/datasets?category=tourism',
    'https://indiaai.gov.in/datasets?category=culture',
    'https://indiaai.gov.in/datasets?category=environment',
    # ── Travel aggregators ───────────────────────────────────────────────
    'https://www.holidify.com/places',
    'https://www.holidify.com/collections/best-places-to-visit-in-india',
    'https://www.thrillophilia.com/tours',
    'https://www.thrillophilia.com/blog/places-to-visit-in-india',
    'https://www.tripoto.com/trips',
    'https://www.tripoto.com/places',
    'https://www.lonelyplanet.com/india',
    'https://www.lonelyplanet.com/india/hotels',
    'https://www.makemytrip.com/holidays-india',
    'https://www.yatra.com/india-tourism',
    'https://www.easeindiatravel.com',
    # ── Hotel directories ────────────────────────────────────────────────
    'https://www.oyorooms.com/india',
    'https://www.treebo.com/hotels',
    'https://www.fabhotels.com',
    'https://www.goibibo.com/hotels/india-hotels',
    # ── Niche travel / adventure ─────────────────────────────────────────
    'https://www.indiahikes.com',
    'https://www.thrillophilia.com/adventure-sports-in-india',
    'https://www.wildlifeindia.org',
    'https://www.sanctuaryasia.com',
    # ── Food & Restaurant ────────────────────────────────────────────────
    'https://www.zomato.com/india',
    'https://www.eazydiner.com',
    'https://www.swiggy.com/city/kolkata/restaurants',
    # ── Heritage & Culture ───────────────────────────────────────────────
    'https://asi.nic.in/national-monuments',
    'https://asi.nic.in/world-heritage-sites',
    'https://www.culturalindia.net',
    'https://www.indiaculture.gov.in',
    # ── Transport / Routes ───────────────────────────────────────────────
    'https://www.irctctourism.com',
    'https://www.redbus.in/bus-routes',
    'https://www.airlineroute.net/category/india',
]


def load_config(path: str = 'config.yaml') -> dict:
    if not os.path.exists(path):
        return {
            'app': {'name': 'Nexuzy Data Collector', 'version': '1.2.0'},
            'database': {'path': 'data/nexuzy_travel.db'},
            'model': {
                'path': 'models/gemma-4b-it-q4_k_m.gguf',
                # hf_model intentionally left blank — auto-detected from models/hf_cache/
                'hf_model': '',
                'n_ctx': 4096, 'n_threads': 4, 'temperature': 0.1
            },
            'crawler': {
                'max_pages_per_domain': 50,
                'delay_between_requests': 1.5,
                'timeout': 30,
                'max_retries': 2,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0',
                'auto_start': False,
                'fetch_open_data': True,
            },
            'verification': {'min_sources': 2, 'confidence_threshold': 70},
            'export': {'output_dir': 'export'},
            'sources': {'seed_urls': SEED_URLS}
        }
    cfg = {}
    with open(path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
    existing = cfg.get('sources', {}).get('seed_urls', [])
    merged = list(dict.fromkeys(existing + SEED_URLS))
    cfg.setdefault('sources', {})['seed_urls'] = merged
    return cfg


class NexuzyApp:
    def __init__(self):
        self.config = load_config()
        self._setup_logging()
        self._init_db()
        self.pipeline = None
        self.log_widget = None
        self._auto_check_model()

    def _setup_logging(self):
        os.makedirs('logs', exist_ok=True)
        logger.remove()
        logger.add(sys.stderr,
                   format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
                   level='INFO')
        logger.add('logs/nexuzy_{time:YYYY-MM-DD}.log',
                   rotation='10 MB', retention='30 days',
                   level='DEBUG', encoding='utf-8')

        def tk_sink(message):
            try:
                if self.log_widget:
                    record = message.record
                    level = record['level'].name
                    text = f"[{record['time'].strftime('%H:%M:%S')}] {level}: {record['message']}"
                    self.log_widget.append(text, level)
            except Exception:
                pass

        logger.add(tk_sink, level='DEBUG')
        logger.info(f"Nexuzy Data Collector v1.2 started | {len(SEED_URLS)} seed sources loaded")

    def _init_db(self):
        from core.database import Database
        db_path = self.config.get('database', {}).get('path', 'data/nexuzy_travel.db')
        self.db = Database(db_path)
        logger.info(f"Database ready: {db_path}")

    def _auto_check_model(self):
        """
        Model priority:
          1. Gemma GGUF present on disk  → use it (local GGUF path)
          2. Any model in models/hf_cache/ → auto-detected by AIExtractor
          3. Nothing found              → rule-based extraction (no AI needed)
        """
        from core.ai_extractor import detect_cached_model, MODEL_CACHE_DIR

        gguf_path = self.config.get('model', {}).get('path', 'models/gemma-4b-it-q4_k_m.gguf')

        if os.path.exists(gguf_path):
            # Gemma GGUF is physically present — use it
            size_mb = os.path.getsize(gguf_path) / 1024 / 1024
            logger.info(f"GGUF model ready: {gguf_path} ({size_mb:.0f} MB)")
            self.config.setdefault('model', {})['hf_model'] = 'local/gemma-4b-it-q4_k_m'
            return

        # Gemma GGUF NOT found — check HF cache for any downloaded model
        cache_dir = self.config.get('model', {}).get('cache_dir', MODEL_CACHE_DIR)
        cached = detect_cached_model(cache_dir)
        if cached:
            # e.g. TinyLlama/TinyLlama-1.1B-Chat-v1.0
            logger.info(f"Using cached HF model: {cached}")
            self.config.setdefault('model', {})['hf_model'] = cached
        else:
            # Nothing at all — clear hf_model so AIExtractor uses rule-based
            self.config.setdefault('model', {})['hf_model'] = ''
            logger.warning(
                f"No AI model found (checked: {gguf_path} | {cache_dir}). "
                "Running in rule-based extraction mode. "
                "To add a model: place gemma-4b-it-q4_k_m.gguf in models/, or "
                "run: python -c \"from core.model_downloader import download; download()\""
            )

    def fetch_open_data(self):
        if not self.config.get('crawler', {}).get('fetch_open_data', True):
            return
        try:
            from core.open_data_fetcher import OpenDataFetcher
            logger.info("Fetching open government datasets (data.gov.in)...")
            fetcher = OpenDataFetcher(self.db)
            fetcher.run()
        except Exception as e:
            logger.warning(f"Open data fetch error: {e}")

    def clean_database(self):
        """Run database cleaning pipeline"""
        from core.db_cleaner import DatabaseCleaner
        logger.info("=== Starting Database Cleaning Pipeline ===")
        cleaner = DatabaseCleaner(self.db)
        report = cleaner.run()
        logger.info(report.summary())
        return report

    def export_data(self, formats: list = None, clean: bool = True):
        """Export data in multiple formats"""
        from core.exporter import Exporter
        if formats is None:
            formats = ['csv', 'json', 'jsonl']
        logger.info(f"=== Exporting Data ({', '.join(formats)}) ===")
        export_dir = self.config.get('export', {}).get('output_dir', 'export')
        exporter = Exporter(self.db, output_dir=export_dir)
        results = exporter.export_all(formats=formats, clean=clean)
        logger.info(f"Export complete: {export_dir}")
        return results

    def export_ai_training(self):
        """Export clean data for AI training"""
        from core.exporter import Exporter
        logger.info("=== Building AI Training Dataset ===")
        export_dir = self.config.get('export', {}).get('output_dir', 'export')
        exporter = Exporter(self.db, output_dir=export_dir)
        results = exporter.export_all_ai_training()
        logger.info("✅ AI training dataset exported to: export/ai_training/")
        return results

    def run_full_pipeline(self):
        """Run complete pipeline: import -> clean -> export AI training"""
        logger.info("╔════════════════════════════════════════════════════════════════╗")
        logger.info("║        NEXUZY FULL DATA PIPELINE                              ║")
        logger.info("║   Import → Clean → Export (AI Training Format)                 ║")
        logger.info("╚════════════════════════════════════════════════════════════════╝")
        
        # Step 1: Clean database
        logger.info("\n[STEP 1] Cleaning database...")
        clean_report = self.clean_database()
        
        # Step 2: Export clean data
        logger.info("\n[STEP 2] Exporting clean data...")
        exports = self.export_data(formats=['jsonl', 'json', 'csv'], clean=True)
        
        # Step 3: Export for AI training
        logger.info("\n[STEP 3] Building AI training dataset...")
        ai_exports = self.export_ai_training()
        
        logger.info("\n╔════════════════════════════════════════════════════════════════╗")
        logger.info("║        PIPELINE COMPLETE ✅                                    ║")
        logger.info("║                                                                ║")
        logger.info("║  📊 Clean Data: export/*.{json,jsonl,csv}                      ║")
        logger.info("║  🤖 AI Training: export/ai_training/training_data.{jsonl,json} ║")
        logger.info("║                                                                ║")
        logger.info(clean_report.summary())
        logger.info("╚════════════════════════════════════════════════════════════════╝")

    def run(self):
        from ui.main_window import MainWindow
        logger.info("Launching desktop UI...")
        window = MainWindow(self)
        window.run()


if __name__ == '__main__':
    app = NexuzyApp()
    app.run()
