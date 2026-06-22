# Nexuzy Data Collector

## AI-Powered Travel Data Collection & Verification System

Nexuzy Data Collector is a Python-based desktop application that automatically discovers, crawls, extracts, verifies, organizes, and stores tourism-related information from publicly accessible websites across India.

## Main Objective

Build a continuously growing India travel knowledge database containing:
- Hotels, Resorts, Homestays
- Tourist Attractions & Historical Places
- Temples & Religious Sites
- Restaurants & Local Food
- Transport Information & Road Routes
- Travel Guides & District Information
- Festival & Seasonal Tourism Data
- Travel Costs & Local Business Information

## Architecture

```
Internet
    │
    ▼
Website Discovery Engine
    │
    ▼
Web Scraper Engine
    │
    ▼
AI Data Extractor (Gemma 4B GGUF)
    │
    ▼
Verification Engine
    │
    ▼
Data Cleaner
    │
    ▼
Knowledge Database (SQLite)
    │
    ▼
Dataset Generator
    │
    ▼
Atithi AI Training
```

## Installation

```bash
pip install -r requirements.txt
python main.py
```

## Requirements
- Python 3.10+
- No C++ build required
- All pure Python dependencies

## Features
- Static & Dynamic web scraping
- Local Gemma 4B AI extraction (GGUF via llama-cpp-python wheel)
- Multi-source verification with confidence scoring
- Duplicate detection
- Geographic data storage
- AI Training Dataset Builder
- Export: CSV, JSON, Excel, SQLite, Parquet, Markdown, JSONL

## Desktop UI
Built with Python Tkinter:
- Dashboard
- Crawler
- Verification
- Database Browser
- Maps
- Training Dataset
- Export
- Settings
- Logs

## License
MIT License - Nexuzy Tech
