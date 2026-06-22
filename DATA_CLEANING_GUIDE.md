# Data Cleaning & AI Training Export Guide

## Overview

Nexuzy provides a complete data cleaning and export pipeline for preparing travel data for AI training:

1. **Data Collection** → Import from Kaggle, Wikipedia, RSS, hotel portals, etc.
2. **Data Cleaning** → Remove duplicates, fix fields, validate coordinates, etc.
3. **Data Export** → Export in multiple formats (JSON, JSONL, CSV)
4. **AI Training** → Export structured training data for fine-tuning LLMs

---

## Quick Start

### Option 1: Command-Line Interface (Recommended)

```bash
# 1. Clean the database
python cli.py clean

# 2. Export clean data
python cli.py export --format jsonl json csv

# 3. Export for AI training
python cli.py train

# Or run everything in one command
python cli.py pipeline
```

### Option 2: Python Script

```python
from main import NexuzyApp

app = NexuzyApp()

# Full pipeline
app.run_full_pipeline()

# Or individual steps
app.clean_database()
app.export_data(formats=['jsonl', 'json', 'csv'], clean=True)
app.export_ai_training()
```

### Option 3: Desktop UI

```bash
python main.py
# Click "Export" tab → "Clean & Export for AI Training"
```

---

## Data Cleaning Pipeline

### Step 1: Garbage Removal
Removes low-quality records:
- Placeholder names (e.g., "test", "sample", "N/A")
- Single-letter or too-short names
- Purely numeric names
- HTML fragments
- Spam/navigation text

### Step 2: Field Normalization
Fixes broken data:
- HTML tag removal from descriptions
- Extra whitespace cleanup
- Rating normalization (0-5 scale)
- Coordinate validation (India bounds)
- Name capitalization fix
- Source deduplication

### Step 3: Deduplication
Fuzzy-matches similar records:
- Name similarity: 88%+ match threshold
- City matching: 80%+ similarity or exact match
- Merges data from duplicate records
- Keeps richer record (more fields)
- Combines source attribution

### Step 4: Low-Confidence Purge
Removes skeleton records:
- Confidence < 40 AND
- No city + No address + No coordinates
- Preserves records with at least one location field

### Step 5: Database Vacuum
Reclaims disk space after deletions

---

## Export Formats

### 1. JSON (Clean)
Complete records as JSON objects:
```json
{
  "name": "Taj Mahal",
  "city": "Agra",
  "state": "Uttar Pradesh",
  "description": "...",
  "category": "Monument",
  "rating": 4.8,
  "latitude": 27.1751,
  "longitude": 78.0421,
  "sources": ["wikipedia", "kaggle"],
  "verified": 1,
  "confidence": 95
}
```

**Files:**
- `export/hotels_clean.json` (20,000+ records)
- `export/tourist_places_clean.json` (5,000+ records)
- `export/restaurants_clean.json` (10,000+ records)

### 2. JSONL (Clean) - Recommended for AI
One JSON per line (ideal for streaming, ML training):
```jsonl
{"name":"Taj Mahal","city":"Agra","state":"Uttar Pradesh",...}
{"name":"Hawa Mahal","city":"Jaipur","state":"Rajasthan",...}
```

**Files:**
- `export/hotels_clean.jsonl`
- `export/tourist_places_clean.jsonl`
- `export/restaurants_clean.jsonl`

### 3. CSV (Clean)
Tabular format for spreadsheets:
```csv
name,city,state,category,rating,latitude,longitude
Taj Mahal,Agra,Uttar Pradesh,Monument,4.8,27.1751,78.0421
```

**Files:**
- `export/hotels_clean.csv`
- `export/tourist_places_clean.csv`
- `export/restaurants_clean.csv`

### 4. AI Training Data (JSONL)
Instruction-tuned format for LLM fine-tuning:
```jsonl
{"type":"place_info","instruction":"Tell me about Taj Mahal","input":"","output":"Taj Mahal\nLocation: Agra, Uttar Pradesh\n..."}
{"type":"hotel_info","instruction":"Tell me about Radisson Blu","input":"","output":"Radisson Blu\nCity: Mumbai\nState: Maharashtra\n..."}
```

**Files:**
- `export/ai_training/training_data.jsonl` (10,000+ samples)
- `export/ai_training/training_data.json`
- `export/ai_training/training_data.csv`

**Training sample types:**
- `place_info` - Destination descriptions
- `place_city_query` - "Places to visit in X"
- `hotel_info` - Hotel details
- `hotel_city_query` - "Best hotels in X"
- `restaurant_info` - Restaurant recommendations

---

## Usage Examples

### Example 1: Full Pipeline

```bash
$ python cli.py pipeline

╔════════════════════════════════════════════════════════════════╗
║        NEXUZY FULL DATA PIPELINE                              ║
║   Import → Clean → Export (AI Training Format)                 ║
╚════════════════════════════════════════════════════════════════╝

[STEP 1] Cleaning database...
  [hotels] Garbage removed: 45 / 2340 rows
  [tourist_places] Garbage removed: 12 / 1850 rows
  Deduplication: 234 duplicates removed
  Fields normalised: 1250 rows updated
  Low-confidence purge: 78 bare rows removed

[STEP 2] Exporting clean data...
  hotels_clean.json: 2295 records
  hotels_clean.jsonl: 2295 records
  hotels_clean.csv: 2295 records

[STEP 3] Building AI training dataset...
  training_data.jsonl: 8750 samples

╔════════════════════════════════════════════════════════════════╗
║        PIPELINE COMPLETE ✅                                    ║
║                                                                ║
║  📊 Clean Data: export/*.{json,jsonl,csv}                      ║
║  🤖 AI Training: export/ai_training/training_data.{jsonl,json} ║
╚════════════════════════════════════════════════════════════════╝
```

### Example 2: Clean Only

```bash
$ python cli.py clean --threshold 88

[DBCleaner] [hotels] Garbage removed: 45 / 2340 rows
[DBCleaner] [tourist_places] Garbage removed: 12 / 1850 rows
[DBCleaner] [restaurants] Garbage removed: 8 / 950 rows
[DBCleaner] [hotels] Deduplication: 234 duplicates removed from 2295 rows
[DBCleaner] [tourist_places] Deduplication: 89 duplicates removed from 1838 rows
```

### Example 3: Export Only

```bash
$ python cli.py export --format jsonl json

Export complete:
  hotels: {'jsonl': 'export/hotels_clean.jsonl', 'json': 'export/hotels_clean.json'}
  tourist_places: {'jsonl': 'export/tourist_places_clean.jsonl', 'json': 'export/tourist_places_clean.json'}
```

### Example 4: Check Stats

```bash
$ python cli.py stats

📊 Database Statistics:
  hotels                :     2340 rows
  tourist_places        :     1850 rows
  restaurants           :      950 rows
  TOTAL                 :     5140 rows
```

---

## Python API

### Clean Database

```python
from main import NexuzyApp

app = NexuzyApp()
report = app.clean_database()

print(report.summary())
# Shows:
# - Garbage rows deleted
# - Fields normalised
# - Duplicates merged
# - Low-confidence removed
```

### Export Data

```python
# Export clean data
results = app.export_data(
    formats=['jsonl', 'json', 'csv'],
    clean=True  # Apply cleaning rules
)

# results = {
#   'hotels': {'jsonl': 'export/hotels_clean.jsonl', ...},
#   'tourist_places': {...},
#   ...
# }
```

### Export for AI Training

```python
ai_results = app.export_ai_training()

# ai_results = {
#   'jsonl': 'export/ai_training/training_data.jsonl',
#   'json': 'export/ai_training/training_data.json',
#   'csv': 'export/ai_training/training_data.csv'
# }
```

---

## Training Data Format

The AI training data is structured for fine-tuning language models:

```json
{
  "type": "hotel_info",
  "instruction": "Tell me about The Oberoi Mumbai",
  "input": "",
  "output": "The Oberoi Mumbai\nCity: Mumbai\nState: Maharashtra\nLuxury 5-star hotel with world-class amenities...\nRating: 4.8"
}
```

**Types:**
- `hotel_info` - Detailed hotel information
- `hotel_city_query` - Hotel recommendations by city
- `place_info` - Tourist place details
- `place_city_query` - Places to visit recommendations
- `restaurant_info` - Restaurant recommendations

**Compatible with:**
- Llama2, Mistral, etc. (via instruction-tuning)
- GPT-3, Claude (few-shot prompting)
- Fine-tuning frameworks (LlamaIndex, LangChain)

---

## Data Quality Metrics

After cleaning, exported data includes:

- **Confidence Score** (0-100): Data quality confidence
- **Verified Flag** (0/1): Cross-verified from multiple sources
- **Sources List**: Originating data sources
- **Completeness**: All key fields populated

---

## Integration with ML Workflows

### Using with Hugging Face

```python
from datasets import load_dataset

# Load training data
dataset = load_dataset('json', data_files='export/ai_training/training_data.jsonl')

# Fine-tune model
from transformers import AutoModelForSeq2SeqLM, Trainer, TrainingArguments

model = AutoModelForSeq2SeqLM.from_pretrained('model-id')
trainer = Trainer(model=model, args=TrainingArguments(...), train_dataset=dataset)
trainer.train()
```

### Using with LlamaIndex

```python
from llama_index import SimpleDirectoryReader, VectorStoreIndex

# Create documents from clean data
documents = SimpleDirectoryReader('export/ai_training').load_data()

# Build index
index = VectorStoreIndex.from_documents(documents)

# Query
response = index.as_query_engine().query("Best hotels in Mumbai")
```

---

## Troubleshooting

### Issue: "thefuzz not installed"
```bash
pip install thefuzz python-Levenshtein
```

### Issue: Low deduplication rate
Adjust threshold (default 88):
```bash
python cli.py clean --threshold 85  # More aggressive
python cli.py clean --threshold 92  # More conservative
```

### Issue: Too much data removed
Check confidence threshold in `core/db_cleaner.py`:
```python
MIN_CONFIDENCE_BARE = 40  # Increase to 50-60 to keep more data
```

---

## Performance Notes

**Estimated Processing Times:**
- Cleaning 10,000 records: ~5-10 seconds
- Deduplication: ~30-60 seconds (depends on record similarity)
- Export to JSON/CSV: ~2-5 seconds
- Building AI training data: ~5-10 seconds

**Storage:**
- Clean JSON: ~2-5 MB per 1000 records
- JSONL: ~2-5 MB per 1000 records (more efficient for streaming)
- CSV: ~1-2 MB per 1000 records
- AI Training JSONL: ~3-7 MB per 1000 samples

---

## Next Steps

1. **Run the pipeline:**
   ```bash
   python cli.py pipeline
   ```

2. **Review outputs:**
   - Check `export/` for clean data
   - Check `export/ai_training/` for training data

3. **Fine-tune a model:**
   - Use the JSONL training data with your preferred framework
   - See "Integration with ML Workflows" section above

4. **Deploy:**
   - Integrate cleaned data into your application
   - Use trained model for recommendations/answers

---

For issues or questions, check the logs in `logs/` directory.
