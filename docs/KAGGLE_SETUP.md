# Kaggle Dataset Import Setup

Nexuzy can auto-download and import curated Kaggle travel datasets directly into
`data/nexuzy_travel.db`.

## Step 1 — Install dependencies

```powershell
pip install kaggle pandas
```

## Step 2 — Get your Kaggle API token

1. Go to **https://www.kaggle.com/settings**
2. Scroll to **API** section → click **Create New Token**
3. A file `kaggle.json` will download automatically

## Step 3 — Place the token file

**Windows:**
```
C:\Users\<YourName>\.kaggle\kaggle.json
```

If the `.kaggle` folder doesn't exist, create it:
```powershell
mkdir C:\Users\$env:USERNAME\.kaggle
Copy-Item "$env:USERPROFILE\Downloads\kaggle.json" "$env:USERPROFILE\.kaggle\kaggle.json"
```

## Step 4 — Run the importer

**Import ALL datasets at once:**
```python
from core.database import Database
from core.kaggle_importer import KaggleImporter

db = Database()
ki = KaggleImporter(db)
results = ki.run_all()
print(results)  
# {'tourist_attractions': 487, 'top_places': 301, 'most_traveled_cities': 98, ...}
```

**Import a single dataset:**
```python
ki.run('tourist_attractions')   # just the attraction dataset
ki.run('hotel_details')         # just hotels
```

**Or run from command line:**
```powershell
python -c "from core.database import Database; from core.kaggle_importer import KaggleImporter; KaggleImporter(Database()).run_all()"
```

## Registered Datasets

| ID | Kaggle Slug | Records | Table |
|---|---|---|---|
| `tourist_attractions` | dakshineswarm/indian-tourist-attraction-dataset | ~500 | tourist_places |
| `top_places` | dhrubangtalukdar/top-indian-places-to-visit-indian-tourism | ~300 | tourist_places |
| `most_traveled_cities` | kirtandwivedi02/most-traveled-cities-in-india | ~100 | tourist_places |
| `india_tourism_stats` | rajkumarl/india-tourism-statistics | ~200 | tourist_places |
| `hotel_details` | nehaprabhakar/hotel-details-dataset-india | ~1000 | hotels |
| `google_places_rating` | chetanborse/google-places-rating-for-indian-cities | ~500 | tourist_places |
| `india_tourism_datasets` | rakkeshcase/india-tourism-datasets | ~400 | tourist_places |

All imports are **deduplicated** — re-running never creates duplicate records.
