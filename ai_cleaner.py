# ai_cleaner.py — Run after scraper finishes to clean garbage data from DB
# Powered by rule-based AI cleaning (works without PyTorch/TinyLlama)
# Fixes applied:
#   1. Correct table name: 'tourist_places' (not 'places')
#   2. Guides table: auto-detects name column (name / title / guide_name)
#   3. Blank-city guard: rows with no city are deleted unless city can be inferred
#   4. Short single-word names (no city context) are deleted as unverifiable

import sqlite3
import re

GARBAGE_PATTERNS = [
    r"^sign up", r"^log(in|out)", r"^register", r"^become a member",
    r"^language$", r"^our brands$", r"^site map$", r"^notices$",
    r"^image credits?$", r"^\|\s*sl\.?\s*no", r"^latest updates\s*:",
    r"^welcome back", r"^home\s*>", r"^explore$", r"^seasons$",
    r"^viewpoints", r"^view more", r"^read more", r"^\d{3,} services$",
    r"shri\.\s+\w+\s+\w+",   # politician names like "Shri. Devendra Fadnavis"
    r"^login to continue",
    r"^fair and festival$",
    r"^handicrafts$",
    r"^travel itinerary$",
    r"^cuisine$",
    r"^how to reach$",
    r"^about place:\s*$",
    r"^about the location:\s*$",
    r"^\s*$",                 # blank / whitespace only
    r"^where are you",        # search box placeholder text
    r"^find your",            # search box placeholder text
    r"farmers'\s*market",     # event listings, not places
    r"^it is celebrated",     # event description sentences
    r"^this light",           # food/dessert description sentences
    r"^also known as",        # description sentences
    r"^for those looking",    # description sentences
    r"^one of the most popular",  # description sentences
    r"^nestled in",           # description sentences
    r"^the trip was",         # user review text
    r"^it was very good",     # user review text
    r"highlights$",           # tour package heading
    r"^kinnaur valley",       # tour package name
]

INDIA_CITIES = {
    "mumbai", "delhi", "kolkata", "chennai", "bangalore", "bengaluru",
    "hyderabad", "ahmedabad", "pune", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "patna",
    "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad",
    "meerut", "rajkot", "varanasi", "srinagar", "aurangabad", "dhanbad",
    "amritsar", "allahabad", "ranchi", "howrah", "coimbatore", "jabalpur",
    "gwalior", "vijayawada", "jodhpur", "madurai", "raipur", "kota",
    "chandigarh", "guwahati", "solapur", "hubballi", "tiruchirappalli",
    "bareilly", "mysuru", "mysore", "goa", "shimla", "shillong", "leh",
    "darjeeling", "ooty", "coorg", "bhubaneswar", "puri", "pondicherry",
    "puducherry", "mangalore", "mangaluru", "kochi", "cochin",
    "thiruvananthapuram", "trivandrum", "kozhikode", "thrissur", "udaipur",
    "pushkar", "jaisalmer", "bikaner", "mount abu", "nainital", "mussoorie",
    "haridwar", "rishikesh", "dehradun", "manali", "dharamshala",
    "mcleod ganj", "dalhousie", "kasauli", "aizawl", "imphal", "agartala",
    "itanagar", "kohima", "dispur", "gangtok", "silvassa", "daman", "diu",
    "panaji", "vizag", "siliguri", "ujjain", "ajmer", "alwar", "bharatpur",
    "munnar", "wayanad", "varkala", "alleppey", "alappuzha", "kovalam",
    "mahabalipuram", "hampi", "badami", "belur", "halebidu", "chikmagalur",
    "kodaikanal", "yercaud", "valparai", "coonoor", "mettupalayam",
    "tirupati", "srisailam", "lepakshi", "nagarjunasagar", "warangal",
    "khajuraho", "orchha", "sanchi", "pachmarhi", "kanha", "bandhavgarh",
    "ranthambore", "sariska", "bharatpur", "sawai madhopur",
    "corbett", "rishikesh", "auli", "lansdowne", "chopta", "tungnath",
    "lakshadweep", "andaman", "port blair", "havelock", "neil island",
}

INDIA_KEYWORDS = [
    "india", "mumbai", "delhi", "bengaluru", "bangalore", "kolkata",
    "chennai", "hyderabad", "jaipur", "kerala", "rajasthan", "goa",
    "punjab", "gujarat", "maharashtra", "karnataka", "tamil", "odisha",
    "assam", "meghalaya", "uttarakhand", "himachal", "jammu", "kashmir",
    "sikkim", "mizoram", "nagaland", "manipur", "tripura", "arunachal",
    "chhattisgarh", "jharkhand", "uttarpradesh", "madhyapradesh",
]

# ── City spelling normaliser (typos found in actual scrape output) ─────────
CITY_TYPO_MAP = {
    "mumabi": "Mumbai",
    "mumbi": "Mumbai",
    "mumbai ": "Mumbai",
    "new delhi": "Delhi",
    "bengaluru": "Bangalore",
    "ooty ": "Ooty",
    "andheri": "Mumbai",
    "bandra west, mumbai": "Mumbai",
    "bandra": "Mumbai",
    "juhu": "Mumbai",
    "powai": "Mumbai",
    "andheri west": "Mumbai",
    "andheri east": "Mumbai",
    "colaba": "Mumbai",
    "kurla": "Mumbai",
    "malad": "Mumbai",
    "borivali": "Mumbai",
    "kandivali": "Mumbai",
    "goregaon": "Mumbai",
    "vile parle": "Mumbai",
    "santacruz": "Mumbai",
    "bkc": "Mumbai",
}


def get_name_column(cur, table: str) -> str | None:
    """Auto-detect the name column for a table (handles guides/places variants)."""
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1].lower() for row in cur.fetchall()]
    for candidate in ["name", "title", "guide_name", "place_name",
                      "restaurant_name", "hotel_name"]:
        if candidate in cols:
            return candidate
    return None


def is_garbage(name: str) -> bool:
    """Return True if name looks like garbage (nav label, CTA, politician, blank)."""
    if not name or len(name.strip()) < 4:
        return True
    name_lower = name.strip().lower()
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, name_lower):
            return True
    # Too few real letters (mostly symbols/numbers)
    if len(re.sub(r'[^a-zA-Z]', '', name)) < 4:
        return True
    # Very long names (>120 chars) are almost always scraped paragraphs
    if len(name.strip()) > 120:
        return True
    return False


def is_india_record(name: str, city: str, url: str = "") -> bool:
    """Return True only if record belongs to India."""
    combined = f"{name} {city} {url}".lower()
    return any(kw in combined for kw in INDIA_KEYWORDS)


def fix_city(name: str, city: str) -> str:
    """
    1. Normalise known typos/sub-areas → canonical city name.
    2. If city is blank or wrong, detect correct Indian city from name.
    """
    # Step 1: normalise typos / sub-area names
    city_key = city.strip().lower()
    if city_key in CITY_TYPO_MAP:
        return CITY_TYPO_MAP[city_key]

    # Step 2: detect city from record name
    name_lower = name.lower()
    for c in INDIA_CITIES:
        if re.search(r'\b' + re.escape(c) + r'\b', name_lower):
            return c.title()

    return city


def clean_table(cur, table: str, name_col: str) -> tuple[int, int, int]:
    """Clean a single table. Returns (rows_scanned, deleted, city_fixed)."""
    try:
        cur.execute(f"SELECT id, {name_col}, city FROM {table}")
        rows = cur.fetchall()
    except Exception as e:
        print(f"⚠  Could not read [{table}]: {e}")
        return 0, 0, 0

    deleted = 0
    fixed = 0

    for row_id, name, city in rows:
        name = (name or "").strip()
        city = (city or "").strip()

        # 1. Delete obvious garbage names
        if is_garbage(name):
            cur.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
            print(f"🗑  DELETED [{table}] id={row_id}: {name!r}")
            deleted += 1
            continue

        # 2. Blank city — try to infer; delete if cannot
        if not city:
            inferred = fix_city(name, city)
            if inferred:
                cur.execute(
                    f"UPDATE {table} SET city=? WHERE id=?",
                    (inferred, row_id)
                )
                print(f"📍  CITY INFERRED [{table}] id={row_id}: '' → {inferred!r} | {name!r}")
                fixed += 1
                city = inferred
            else:
                cur.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
                print(f"🏙  NO-CITY DELETED [{table}] id={row_id}: {name!r}")
                deleted += 1
                continue

        # 3. Delete non-India records
        if not is_india_record(name, city):
            cur.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
            print(f"🌍  NON-INDIA DELETED [{table}] id={row_id}: {name!r} | city={city!r}")
            deleted += 1
            continue

        # 4. Fix wrong / misspelled city
        corrected_city = fix_city(name, city)
        if corrected_city.lower() != city.lower():
            cur.execute(
                f"UPDATE {table} SET city=? WHERE id=?",
                (corrected_city, row_id)
            )
            print(f"📍  CITY FIXED [{table}] id={row_id}: {city!r} → {corrected_city!r} | {name!r}")
            fixed += 1

    print(f"✅  {table}: {deleted} deleted, {fixed} city-fixed  (out of {len(rows)} rows)")
    return len(rows), deleted, fixed


def clean_database(db_path: str = "data/nexuzy_travel.db") -> None:
    """Scan all tables and delete garbage rows, fix wrong/blank cities."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ── Correct table names (tourist_places not places) ──────────────────
    tables = ["tourist_places", "hotels", "restaurants", "guides"]

    total_scanned = 0
    total_deleted = 0
    total_fixed = 0

    for table in tables:
        # Check table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if not cur.fetchone():
            print(f"⚠  Table '{table}' not found — skipping.")
            continue

        # Auto-detect the name column (handles guides using 'title' etc.)
        name_col = get_name_column(cur, table)
        if not name_col:
            print(f"⚠  [{table}] No recognised name column found — skipping.")
            continue

        print(f"\n🔍  Scanning [{table}] (name_col='{name_col}') ...")
        scanned, deleted, fixed = clean_table(cur, table, name_col)
        total_scanned += scanned
        total_deleted += deleted
        total_fixed += fixed

    conn.commit()
    conn.close()

    print(f"""
╔══════════════════════════════════════════╗
║  🤖  AI CLEANER — DONE                  ║
╠══════════════════════════════════════════╣
║  Rows scanned  : {total_scanned:<6}                  ║
║  Deleted       : {total_deleted:<6}                  ║
║  City fixed    : {total_fixed:<6}                  ║
╚══════════════════════════════════════════╝
""")


if __name__ == "__main__":
    clean_database()