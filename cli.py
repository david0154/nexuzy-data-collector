#!/usr/bin/env python3
"""
Nexuzy CLI — Command-line interface for data collection, cleaning, and export
"""

import sys
import argparse
from loguru import logger
from main import NexuzyApp

def setup_logging_cli():
    """Setup CLI logging"""
    import os
    os.makedirs('logs', exist_ok=True)
    logger.remove()
    logger.add(sys.stderr,
               format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
               level='DEBUG')
    logger.add('logs/nexuzy_cli_{time:YYYY-MM-DD_HH-mm-ss}.log',
               rotation='100 MB', retention='30 days',
               level='DEBUG', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(
        description='Nexuzy Data Collector CLI - Travel Data Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean database
  python cli.py clean

  # Export data
  python cli.py export --format jsonl json csv

  # Export for AI training
  python cli.py train

  # Full pipeline: clean + export AI training
  python cli.py pipeline

  # Check database stats
  python cli.py stats
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean database (remove duplicates, garbage, fix fields)')
    clean_parser.add_argument('--threshold', type=int, default=88, help='Fuzzy match threshold for duplicates (default: 88)')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export clean data')
    export_parser.add_argument('--format', nargs='+', default=['jsonl', 'json', 'csv'],
                              help='Export formats: csv, json, jsonl, excel, parquet (default: jsonl json csv)')
    export_parser.add_argument('--raw', action='store_true', help='Export raw data without cleaning')

    # Train command (AI training dataset)
    train_parser = subparsers.add_parser('train', help='Export data for AI training')
    train_parser.add_argument('--output', default='export/ai_training', help='Output directory for training data')

    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run full pipeline: clean -> export -> train')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')

    # UI command
    ui_parser = subparsers.add_parser('ui', help='Launch desktop UI')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize app
    setup_logging_cli()
    app = NexuzyApp()

    try:
        if args.command == 'clean':
            logger.info("Starting database cleaning...")
            report = app.clean_database()
            sys.exit(0 if report.summary() else 1)

        elif args.command == 'export':
            logger.info(f"Exporting data in formats: {', '.join(args.format)}")
            results = app.export_data(formats=args.format, clean=not args.raw)
            logger.info(f"✅ Export complete")
            for table, exports in results.items():
                logger.info(f"  {table}: {exports}")
            sys.exit(0)

        elif args.command == 'train':
            logger.info("Building AI training dataset...")
            results = app.export_ai_training()
            logger.info(f"✅ AI training export complete")
            for fmt, path in results.items():
                logger.info(f"  {fmt}: {path}")
            sys.exit(0)

        elif args.command == 'pipeline':
            logger.info("Running full pipeline...")
            app.run_full_pipeline()
            sys.exit(0)

        elif args.command == 'stats':
            from core.db_cleaner import DatabaseCleaner
            cleaner = DatabaseCleaner(app.db)
            counts = cleaner.table_counts()
            logger.info("📊 Database Statistics:")
            total = 0
            for table, count in counts.items():
                logger.info(f"  {table:<20}: {count:>8} rows")
                total += count
            logger.info(f"  {'TOTAL':<20}: {total:>8} rows")
            sys.exit(0)

        elif args.command == 'ui':
            logger.info("Launching desktop UI...")
            app.run()
            sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
