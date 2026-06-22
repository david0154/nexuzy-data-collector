"""
kaggle_datasets.py  —  Single source-of-truth for all Kaggle / Open dataset URLs.

Import this anywhere in the app:
    from kaggle_datasets import ALL_DATASETS, CATEGORY_COLORS

No duplicates.  Every dataset appears exactly once.
"""

ALL_DATASETS = [
    # ──────────────────────────────────────────────────
    # 🏛️ Tourist Places
    # ──────────────────────────────────────────────────
    {
        "category": "🏛️ Tourist Places",
        "name": "Indian Tourism Dataset (100 destinations, 54 fields)",
        "desc": "Tourist places · coordinates · best season · budget · airports · travel tips.",
        "url": "https://www.kaggle.com/datasets/sushanthnaidu24/indian-tourism-dataset",
        "records": "100",
    },
    {
        "category": "🏛️ Tourist Places",
        "name": "Explore India: Tourist Destination Dataset",
        "desc": "156 destinations across India with transport and attraction information.",
        "url": "https://www.kaggle.com/datasets/kumarperiya/explore-india-a-tourist-destination-dataset",
        "records": "156",
    },
    {
        "category": "🏛️ Tourist Places",
        "name": "Top Indian Places to Visit",
        "desc": "City, state, category, visit duration, ratings and entry fees.",
        "url": "https://www.kaggle.com/datasets/dhrubangtalukdar/top-indian-places-to-visit-indian-tourism",
        "records": "—",
    },
    {
        "category": "🏛️ Tourist Places",
        "name": "India Tourism Atlas",
        "desc": "Tourist attractions with latitude, longitude, ratings and fare information.",
        "url": "https://www.kaggle.com/datasets/anushkamandekar/indiatourismatlas",
        "records": "—",
    },
    {
        "category": "🏛️ Tourist Places",
        "name": "Guide to India's Must-See Places (325 destinations)",
        "desc": "325 destinations, categories, location details and travel information.",
        "url": "https://www.kaggle.com/datasets/saketk511/travel-dataset-guide-to-indias-must-see-places",
        "records": "325",
    },
    {
        "category": "🏛️ Tourist Places",
        "name": "Famous Indian Tourist Places",
        "desc": "Well-known tourist spots with descriptions, ratings and location data.",
        "url": "https://www.kaggle.com/datasets/naqibahmedkadri/famous-indian-tourist-places",
        "records": "—",
    },
    # ──────────────────────────────────────────────────
    # 🏨 Hotels
    # ──────────────────────────────────────────────────
    {
        "category": "🏨 Hotels",
        "name": "Hotels on MakeMyTrip (20,000 hotels)",
        "desc": "20,000 hotel records with descriptions, ratings, coordinates, amenities. Based on 615,000+ source.",
        "url": "https://www.kaggle.com/datasets/PromptCloudHQ/hotels-on-makemytrip",
        "records": "20,000",
    },
    {
        "category": "🏨 Hotels",
        "name": "Indian Hotels on Booking.com (6,000 hotels)",
        "desc": "Ratings, reviews, facilities, coordinates, room types. Subset of 94,000+ hotel dataset.",
        "url": "https://www.kaggle.com/datasets/PromptCloudHQ/indian-hotels-on-bookingcom",
        "records": "6,000",
    },
    {
        "category": "🏨 Hotels",
        "name": "Indian Hotels on Cleartrip (5,000 hotels)",
        "desc": "Based on a larger 42,000+ hotel source.",
        "url": "https://www.kaggle.com/datasets/PromptCloudHQ/indian-hotels-on-cleartrip",
        "records": "5,000",
    },
    {
        "category": "🏨 Hotels",
        "name": "Indian Hotels on Goibibo (4,000 hotels)",
        "desc": "Hotel listings from Goibibo platform with prices and ratings. Subset of 33,000+ source.",
        "url": "https://www.kaggle.com/datasets/PromptCloudHQ/hotels-on-goibibo",
        "records": "4,000",
    },
    {
        "category": "🏨 Hotels",
        "name": "Google Indian Hotel Data 2023",
        "desc": "Hotels from 51 Indian cities — price, ratings, hotel features.",
        "url": "https://www.kaggle.com/datasets/alvinmanojalex/google-indian-hotel-data",
        "records": "51 cities",
    },
    {
        "category": "🏨 Hotels",
        "name": "Hotels in India",
        "desc": "Hotel names, ratings, sustainability level, reviews.",
        "url": "https://www.kaggle.com/datasets/aakashshinde1507/hotels-in-india",
        "records": "—",
    },
    {
        "category": "🏨 Hotels",
        "name": "TBO Hotels Dataset (1,000,000+ hotels worldwide)",
        "desc": "Massive worldwide hotel dataset — filter for India records on import.",
        "url": "https://www.kaggle.com/datasets/raj713335/tbo-hotels-dataset",
        "records": "1,000,000+",
    },
    # ──────────────────────────────────────────────────
    # 🧭 Travel Guides
    # ──────────────────────────────────────────────────
    {
        "category": "🧭 Travel Guides",
        "name": "Most Traveled Cities in India",
        "desc": "Ratings, city descriptions, best time to visit.",
        "url": "https://www.kaggle.com/datasets/kirtandwivedi02/most-traveled-cities-in-india",
        "records": "—",
    },
    {
        "category": "🧭 Travel Guides",
        "name": "Indian Places Reviews Dataset",
        "desc": "User reviews of Indian places — useful for sentiment analysis and recommendations.",
        "url": "https://www.kaggle.com/datasets/ritvik1909/indian-places-to-visit-reviews-data",
        "records": "—",
    },
    {
        "category": "🧭 Travel Guides",
        "name": "Travel Recommendation Dataset",
        "desc": "User travel history · destinations · reviews · travel preferences.",
        "url": "https://www.kaggle.com/datasets/amanmehra23/travel-recommendation-dataset",
        "records": "—",
    },
    # ──────────────────────────────────────────────────
    # 🛣️ Route Planning
    # ──────────────────────────────────────────────────
    {
        "category": "🛣️ Route Planning",
        "name": "Dynamic Tourism Route Dataset (DTRD)",
        "desc": "Tourist routes · attractions · traffic · weather · crowd density · route optimisation.",
        "url": "https://www.kaggle.com/datasets/ziya07/dynamic-tourism-route-dataset-dtrd",
        "records": "—",
    },
    {
        "category": "🛣️ Route Planning",
        "name": "Road Tourism Data for Sustainable Route Prediction",
        "desc": "Road conditions · traffic congestion · travel modes · route sustainability scores.",
        "url": "https://www.kaggle.com/datasets/ziya07/road-tourism-data-for-sustainable-route-prediction",
        "records": "—",
    },
    {
        "category": "🛣️ Route Planning",
        "name": "Traveler Trip Dataset",
        "desc": "Origin→Destination · transport type · trip duration · accommodation and transportation costs.",
        "url": "https://www.kaggle.com/datasets/rkiattisak/traveler-trip-data",
        "records": "—",
    },
    {
        "category": "🛣️ Route Planning",
        "name": "GTFS Traffic Prediction Dataset (366 routes, 5,624 stops)",
        "desc": "GTFS-format traffic & transit prediction across 366 routes and 5,624 stops.",
        "url": "https://www.kaggle.com/datasets/charvibannur/gtfs-traffic-prediction-dataset",
        "records": "5,624 stops",
    },
    # ──────────────────────────────────────────────────
    # 🚆 Railways
    # ──────────────────────────────────────────────────
    {
        "category": "🚆 Railways",
        "name": "Indian Railways Dataset",
        "desc": "Core Indian Railways data: trains, routes and station information.",
        "url": "https://www.kaggle.com/datasets/sripaadsrinivasan/indian-railways-dataset",
        "records": "—",
    },
    {
        "category": "🚆 Railways",
        "name": "Indian Railways Latest (11,114 trains, 186,000+ schedule rows)",
        "desc": "Most comprehensive & up-to-date Indian Railways dataset on Kaggle.",
        "url": "https://www.kaggle.com/datasets/arihantjain09/indian-railways-latest",
        "records": "186,000+",
    },
    {
        "category": "🚆 Railways",
        "name": "Indian Railway Stations Dataset",
        "desc": "Station codes, names, zones, coordinates.",
        "url": "https://www.kaggle.com/datasets/flugeltomar/indian-railway-dataset",
        "records": "—",
    },
    {
        "category": "🚆 Railways",
        "name": "Indian Railway Stations Codes & Facilities",
        "desc": "Station codes with facility data: platforms, Wi-Fi, food, accessibility.",
        "url": "https://www.kaggle.com/datasets/shraddha4ever20/indian-railway-stations-codes-and-facilities-data",
        "records": "—",
    },
    {
        "category": "🚆 Railways",
        "name": "Indian Railways Schedule, Prices & Availability",
        "desc": "Train schedule with ticket prices and seat availability.",
        "url": "https://www.kaggle.com/datasets/bhavyarajdev/indian-railways-schedule-prices-availability-data",
        "records": "—",
    },
    {
        "category": "🚆 Railways",
        "name": "Indian Railways Time Table",
        "desc": "Full timetable for trains available on Indian Railways.",
        "url": "https://www.kaggle.com/datasets/harsh16/indian-railways-time-table-for-trains-available",
        "records": "—",
    },
    # ──────────────────────────────────────────────────
    # ✈️ Flights
    # ──────────────────────────────────────────────────
    {
        "category": "✈️ Flights",
        "name": "Flights in India Dataset",
        "desc": "Indian domestic flight data with routes, airlines and schedules.",
        "url": "https://www.kaggle.com/datasets/dhairya903/flights-in-india",
        "records": "—",
    },
    {
        "category": "✈️ Flights",
        "name": "Indian Domestic Airline Dataset (103 airports)",
        "desc": "103 Indian airports, airlines, routes and schedules.",
        "url": "https://www.kaggle.com/datasets/kabil007/indian-domestic-airline-dataset",
        "records": "103 airports",
    },
    {
        "category": "✈️ Flights",
        "name": "Indian Flight Schedules",
        "desc": "Scheduled domestic flight data across Indian airports.",
        "url": "https://www.kaggle.com/datasets/nikhilkhetan/indian-flight-schedules",
        "records": "—",
    },
    {
        "category": "✈️ Flights",
        "name": "Indian Domestic Flights Dataset 2019–2025",
        "desc": "Historical and recent domestic flight data across 6 years.",
        "url": "https://www.kaggle.com/datasets/shraddha4ever20/indian-domestic-flights-dataset-20192025",
        "records": "2019–2025",
    },
    {
        "category": "✈️ Flights",
        "name": "Airlines, Airports & Flight Routes (67,664 routes)",
        "desc": "Global airline route database with 67,664 routes.",
        "url": "https://www.kaggle.com/datasets/elmoallistair/airlines-airport-and-routes",
        "records": "67,664",
    },
    {
        "category": "✈️ Flights",
        "name": "Flight Route Database (59,036 routes)",
        "desc": "OpenFlights route database covering 59,036 routes worldwide.",
        "url": "https://www.kaggle.com/datasets/open-flights/flight-route-database",
        "records": "59,036",
    },
    {
        "category": "✈️ Flights",
        "name": "Airline Routes 92K+ & Airports 9K+",
        "desc": "92,000+ airline routes and 9,000+ airport records worldwide.",
        "url": "https://www.kaggle.com/datasets/moonnectar/airline-routes-92k-and-airports-10k-dataset",
        "records": "92,000+",
    },
    # ──────────────────────────────────────────────────
    # 🚌 Bus Routes
    # ──────────────────────────────────────────────────
    {
        "category": "🚌 Bus Routes",
        "name": "Pan India Bus Routes (35,667 schedules, 1,000+ cities)",
        "desc": "35,667 bus schedules spanning 1,000+ Indian cities.",
        "url": "https://www.kaggle.com/datasets/rohitgds/pan-india-bus-routes-35k-schedules-1000-cities",
        "records": "35,667",
    },
    {
        "category": "🚌 Bus Routes",
        "name": "Indian Cities Bus Routes & Prices",
        "desc": "Bus routes with pricing across major Indian cities.",
        "url": "https://www.kaggle.com/datasets/ayushkhaire/indian-cities-buses-routes-and-prices",
        "records": "—",
    },
    {
        "category": "🚌 Bus Routes",
        "name": "Delhi Open Transit Data (GTFS)",
        "desc": "GTFS-format public transit data for Delhi buses.",
        "url": "https://www.kaggle.com/datasets/prasannadsa/delhi-open-transit-data",
        "records": "—",
    },
    {
        "category": "🚌 Bus Routes",
        "name": "Chennai Bus Route Dataset",
        "desc": "Bus routes across Chennai with stop and timing data.",
        "url": "https://www.kaggle.com/datasets/baarathsrinivasan/chennai-bus-route",
        "records": "—",
    },
    # ──────────────────────────────────────────────────
    # 🗺️ Open Data (non-Kaggle)
    # ──────────────────────────────────────────────────
    {
        "category": "🗺️ Open Data",
        "name": "OpenStreetMap India Extract",
        "desc": "Entire India map: hotels, restaurants, tourist spots, stations, airports, hospitals, roads.",
        "url": "https://download.geofabrik.de/asia/india.html",
        "records": "Full India",
    },
    {
        "category": "🗺️ Open Data",
        "name": "Data.gov.in Transport Datasets",
        "desc": "Official Indian government transport and highway datasets.",
        "url": "https://data.gov.in",
        "records": "Various",
    },
]

# Colour per category (used by the UI tree view)
CATEGORY_COLORS: dict[str, str] = {
    "🏛️ Tourist Places": "#e94560",
    "🏨 Hotels":          "#00b4d8",
    "🧭 Travel Guides":   "#00ff88",
    "🛣️ Route Planning":  "#ffd166",
    "🚆 Railways":        "#a29bfe",
    "✈️ Flights":         "#74b9ff",
    "🚌 Bus Routes":      "#fd79a8",
    "🗺️ Open Data":       "#55efc4",
}

# Flat list of all unique URLs (handy for validation)
ALL_URLS: list[str] = [d["url"] for d in ALL_DATASETS]


def _assert_no_duplicates() -> None:
    """Startup self-check: crash loudly if a URL appears more than once."""
    seen: set[str] = set()
    for d in ALL_DATASETS:
        url = d["url"]
        assert url not in seen, f"Duplicate dataset URL in kaggle_datasets.py: {url}"
        seen.add(url)


_assert_no_duplicates()   # runs once on import
