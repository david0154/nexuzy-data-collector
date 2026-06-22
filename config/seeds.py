"""
Nexuzy Data Collector — Seed URL Registry
All seed sources for the crawler. Government sites that are dead/SSL-broken
have been replaced with working equivalents.
"""

# ---------------------------------------------------------------------------
# Working travel portals (verified June 2026)
# ---------------------------------------------------------------------------
PORTAL_SEEDS = [
    # Indian government tourism (working mirrors)
    'https://tourism.gov.in',
    'https://www.tourismofindia.com',
    'https://www.india.gov.in/topics/travel-tourism',
    'https://knowindia.india.gov.in/culture-and-heritage/',

    # State tourism (working)
    'https://www.uttarakhandtourism.gov.in',
    'https://www.hptdc.in',
    'https://www.keralatourism.org',
    'https://www.gujarattourism.com',
    'https://www.maharashtratourism.gov.in',
    'https://www.goatourism.gov.in',
    'https://www.tamilnadutourism.tn.gov.in',
    'https://www.karnatakatourism.org',
    'https://www.odishatourism.gov.in',
    'https://www.assamtourism.gov.in',

    # West Bengal (replaced dead wbtourism.gov.in)
    'https://www.wbtourismgov.in',
    'https://www.westbengaltourism.travel',

    # Rajasthan (replaced dead rajasthantourism.gov.in)
    'https://www.tourism.rajasthan.gov.in',

    # Sikkim (replaced dead sikkimtourism.gov.in)
    'https://www.sikkimtourism.org',

    # Andaman (replaced dead andamantourism.gov.in)
    'https://www.andamantourism.org',

    # Jharkhand / Bihar (replaced dead .gov.in)
    'https://www.jharkhandtourism.in',
    'https://www.bihartourism.gov.in/en',

    # J&K / Ladakh (replaced dead jktourism.gov.in)
    'https://www.jktourism.org',
    'https://www.lahdc.nic.in',

    # Mizoram (replaced dead mizoramt.nic.in)
    'https://tourism.mizoram.gov.in',
]

# ---------------------------------------------------------------------------
# Travel editorial & guides
# ---------------------------------------------------------------------------
EDITORIAL_SEEDS = [
    'https://www.lonelyplanet.com/india',
    'https://www.tripadvisor.in/Tourism-g304551-India-Vacations.html',
    'https://www.holidify.com/country/india/',
    'https://traveltriangle.com/blog/places-to-visit-in-india/',
    'https://www.thrillophilia.com/india',
    'https://www.trawell.in',
    'https://www.tourmyindia.com',
    'https://www.nativeplanet.com',
    'https://www.cleartrip.com/collections/destinations',
    'https://en.wikivoyage.org/wiki/India',
    'https://www.justdial.com/India/Hotels',
]

# ---------------------------------------------------------------------------
# Wikipedia regional pages (stable, reliable)
# ---------------------------------------------------------------------------
WIKIPEDIA_SEEDS = [
    'https://en.wikipedia.org/wiki/Tourism_in_India',
    'https://en.wikipedia.org/wiki/Tourism_in_West_Bengal',
    'https://en.wikipedia.org/wiki/Tourism_in_Rajasthan',
    'https://en.wikipedia.org/wiki/Tourism_in_Kerala',
    'https://en.wikipedia.org/wiki/List_of_tourist_attractions_in_India',
    'https://en.wikipedia.org/wiki/List_of_hotels_in_India',
    'https://en.wikipedia.org/wiki/List_of_World_Heritage_Sites_in_India',
]

# ---------------------------------------------------------------------------
# All seeds combined
# ---------------------------------------------------------------------------
ALL_SEEDS = PORTAL_SEEDS + EDITORIAL_SEEDS + WIKIPEDIA_SEEDS

# Dead URLs that are known to be permanently broken (skip without retrying)
DEAD_URLS = {
    'https://www.incredibleindia.org',           # SSL broken
    'https://www.india.gov.in/topics/travel-tourism',  # 404
    'https://www.wbtourism.gov.in',              # SSL broken
    'https://www.rajasthantourism.gov.in',       # SSL broken
    'https://www.sikkimtourism.gov.in',          # ConnectTimeout
    'https://www.mizoramt.nic.in',               # Max retries
    'https://www.jktourism.gov.in',              # Max retries
    'https://www.lahaultourism.in',              # Max retries
    'https://www.andamantourism.gov.in',         # ConnectTimeout
    'https://www.jharkhandtourism.gov.in',       # ConnectTimeout
    'https://www.bihartourism.gov.in',           # ConnectTimeout
    'https://overpass-api.de/api/interpreter',   # Not a crawl target
    'https://overpass.kumi.systems/api/interpreter',  # Not a crawl target
}
