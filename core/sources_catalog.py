"""
Nexuzy Data Collector - Sources Catalog
Categorized India travel data sources with metadata.
"""

SOURCES = {
    "government": {
        "description": "Official government tourism portals",
        "priority": 1,
        "urls": [
            "https://www.incredibleindia.gov.in",
            "https://tourism.gov.in",
            "https://asi.nic.in",
            "https://www.india.gov.in/topics/travel-tourism",
            "https://data.gov.in/catalog/tourist-places",
            "https://data.gov.in/catalog/hotels-india",
            "https://data.gov.in/catalog/heritage-sites",
            "https://whc.unesco.org/en/statesparties/in",
        ]
    },
    "state_tourism": {
        "description": "State tourism department websites",
        "priority": 1,
        "urls": [
            "https://www.wbtourism.gov.in",
            "https://www.rajasthantourism.gov.in",
            "https://www.keralatourism.org",
            "https://www.goatourism.gov.in",
            "https://www.himachaltourism.gov.in",
            "https://uttarakhandtourism.gov.in",
            "https://www.tamilnadutourism.tn.gov.in",
            "https://www.gujarattourism.com",
            "https://www.maharashtratourism.gov.in",
            "https://www.karnataka.com/tourism",
            "https://www.odishatourism.gov.in",
            "https://www.assamtourism.gov.in",
            "https://www.sikkimtourism.gov.in",
            "https://www.meghalayatourism.in",
            "https://www.andamantourism.gov.in",
            "https://www.delhitourism.gov.in",
            "https://www.uptourism.gov.in",
            "https://www.mptourism.com",
            "https://www.bihartourism.gov.in",
            "https://aptourism.gov.in",
            "https://www.telanganatourism.gov.in",
            "https://www.jktourism.gov.in",
            "https://www.arunachaltourism.com",
            "https://www.sikkimtourism.gov.in",
            "https://www.chhattisgarhtourism.in",
            "https://www.jharkhandtourism.gov.in",
            "https://haryanatourism.gov.in",
            "https://www.punjabtourism.gov.in",
            "https://tripuratourism.gov.in",
            "https://www.manipurtourism.gov.in",
            "https://www.nagalandtourism.com",
            "https://www.lakshadweeptourism.com",
        ]
    },
    "travel_portals": {
        "description": "Major travel booking and discovery portals",
        "priority": 2,
        "urls": [
            "https://www.tripadvisor.in",
            "https://www.holidify.com",
            "https://www.thrillophilia.com",
            "https://www.trawell.in",
            "https://traveltriangle.com",
            "https://www.tourmyindia.com",
            "https://www.easemytrip.com",
            "https://www.thomascook.in",
            "https://www.lonelyplanet.com/india",
            "https://www.roughguides.com/india",
            "https://www.indiaplanet.com",
            "https://www.ixigo.com/travel-guide",
            "https://www.travelogyindia.com",
            "https://www.indiatravelportal.com",
            "https://www.rome2rio.com/s/India",
        ]
    },
    "hotels_booking": {
        "description": "Hotel and accommodation booking sites",
        "priority": 2,
        "urls": [
            "https://www.makemytrip.com/hotels/india_hotels",
            "https://www.goibibo.com/hotels/india",
            "https://www.yatra.com/hotels/india",
            "https://www.cleartrip.com/hotels",
            "https://www.booking.com/searchresults/in/in.html",
            "https://www.trivago.in",
            "https://www.agoda.com/en-in",
            "https://www.clubmahindra.com",
            "https://www.hotels.com/search/India",
        ]
    },
    "food_restaurants": {
        "description": "Restaurant and food discovery platforms",
        "priority": 2,
        "urls": [
            "https://www.zomato.com/india",
            "https://www.eazydiner.com",
            "https://www.dineout.co.in",
            "https://www.burrp.com",
        ]
    },
    "transport": {
        "description": "Transport and route information",
        "priority": 2,
        "urls": [
            "https://www.indianrailways.gov.in",
            "https://www.irctc.co.in",
            "https://www.redbus.in/bus-routes",
            "https://www.abhibus.com",
            "https://www.roadtripper.in",
            "https://www.rome2rio.com/s/India",
        ]
    },
    "heritage_temples": {
        "description": "Heritage sites, temples, religious tourism",
        "priority": 1,
        "urls": [
            "https://asi.nic.in/monuments",
            "https://whc.unesco.org/en/statesparties/in",
            "https://www.templenet.com",
            "https://www.12jyotirlinga.com",
            "https://www.shaktipiths.com",
            "https://www.divyatirtha.org",
        ]
    },
    "travel_blogs": {
        "description": "Travel blogs and personal travel writing",
        "priority": 3,
        "urls": [
            "https://traveltriangle.com/blog",
            "https://www.inditales.com",
            "https://www.holidify.com/blog",
            "https://www.thrillophilia.com/blog",
            "https://www.desi-traveler.com",
            "https://www.thetravelblogger.in",
            "https://www.backpackingwithsam.in",
            "https://www.mouthshut.com/travel/India",
        ]
    },
    "open_data": {
        "description": "Open datasets and geographic data",
        "priority": 1,
        "urls": [
            "https://data.gov.in/catalog/tourist-places",
            "https://data.gov.in/catalog/hotels-india",
            "https://data.gov.in/catalog/heritage-sites",
            "https://nominatim.openstreetmap.org",
        ]
    },
    "city_specific": {
        "description": "Dedicated city and destination websites",
        "priority": 2,
        "urls": [
            "https://www.darjeelingtourism.com",
            "https://www.sundarbans.org.in",
            "https://www.jaisalmerfort.com",
            "https://www.udaipurtourism.co.in",
            "https://www.agratourism.in",
            "https://www.varanasiontour.com",
            "https://www.risikeshtourism.in",
            "https://www.manalihotels.in",
            "https://www.shimlatourism.co.in",
            "https://www.mysoredasara.com",
            "https://www.ooty.com",
            "https://www.munnar.com",
            "https://www.alleppeybackwaters.com",
            "https://www.pondicherrytourism.co.in",
            "https://www.gangtok.com",
            "https://www.leh-ladakh.com",
            "https://www.andamantourism.info",
            "https://www.hampi.in",
            "https://www.amritsartourism.com",
            "https://www.khajuraho.com",
            "https://www.ajantaellora.in",
        ]
    }
}


def get_all_urls() -> list:
    """Return all URLs across all categories, sorted by priority."""
    result = []
    for cat, data in sorted(SOURCES.items(), key=lambda x: x[1]['priority']):
        result.extend(data['urls'])
    return list(dict.fromkeys(result))  # deduplicate preserving order


def get_urls_by_category(category: str) -> list:
    return SOURCES.get(category, {}).get('urls', [])


def get_categories() -> list:
    return list(SOURCES.keys())
