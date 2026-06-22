# Nexuzy Data Collector - Installation Guide

## Requirements
- Python 3.10, 3.11, or 3.12
- Windows 10/11 x64
- **NO C++ compiler needed**
- **NO Visual Studio needed**
- Internet connection for first run (model download)

---

## Step 1 — Upgrade pip

```powershell
python -m pip install --upgrade pip
```

---

## Step 2 — Install numpy & pandas (prebuilt wheels only)

Run this FIRST before requirements.txt:

```powershell
pip install numpy==2.1.3 pandas==2.2.3 --only-binary=:all:
```

> `--only-binary=:all:` forces pip to use prebuilt `.whl` files only.
> It will NEVER try to compile from source.

---

## Step 3 — Install all other packages

```powershell
pip install -r requirements.txt --only-binary=:all: --ignore-installed numpy pandas
```

Or individually if any package fails:

```powershell
pip install requests beautifulsoup4 html5lib trafilatura newspaper4k
pip install playwright selenium webdriver-manager
pip install transformers tokenizers sentencepiece huggingface_hub
pip install sqlite-utils openpyxl fuzzywuzzy python-levenshtein
pip install geopy wikipedia feedparser
pip install tqdm loguru pyyaml python-dotenv schedule httpx Pillow
pip install jsonlines markdown
```

---

## Step 4 — Install Playwright browser (optional)

Only needed for JS-heavy sites:

```powershell
playwright install chromium
```

---

## Step 5 — Run the app

```powershell
python main.py
```

---

## Step 6 — Download AI Model (in app)

1. Open app → click **🤖 AI Model** tab
2. Select **Gemma 2B IT** (recommended) or **Qwen2 0.5B** (ultra light)
3. Click **⬇ Download Model**
4. Model downloads to `models/hf_cache/` automatically

> No HuggingFace account needed for public models.

---

## Packages Removed (needed C++)

| Removed | Replaced With |
|---------|---------------|
| `llama-cpp-python` | `transformers` + `onnxruntime` |
| `numpy==1.26.4` (source build) | `numpy==2.1.3` (prebuilt wheel) |
| `lxml==5.2.2` (source build) | `lxml==5.3.1` (prebuilt wheel) |
| `newspaper3k` (broken) | `newspaper4k` (maintained) |
| `pyarrow` (optional, large) | removed (not core) |

---

## Troubleshooting

**Error: `metadata-generation-failed` for numpy/pandas**
```powershell
pip install numpy==2.1.3 pandas==2.2.3 --only-binary=:all:
```

**Error: `No module named transformers`**
```powershell
pip install transformers tokenizers sentencepiece
```

**Error: `lxml` build fails**
```powershell
pip install lxml --only-binary=:all:
```

**App runs but AI extraction is slow (CPU only)**
- This is normal without GPU
- Use **Qwen2 0.5B** for faster CPU inference
- Rule-based fallback activates automatically if model is slow
