"""
Nexuzy Data Collector — Kaggle Dataset Importer
================================================
Downloads and imports curated Kaggle datasets into nexuzy_travel.db.

Setup (one-time):
  pip install kaggle pandas
  Get kaggle.json from https://www.kaggle.com/settings  -> API -> Create New Token
  Save to  C:\\Users\\<you>\\.kaggle\\kaggle.json

Usage:
  from core.kaggle_importer import KaggleImporter
  ki = KaggleImporter(db)
  ki.run_all()           # import every dataset
  ki.run('top_places')   # import only one by id
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False
    logger.warning("pandas not installed — run: pip install pandas")

try:
    import kaggle  # noqa: F401
    _KAGGLE_OK = True
except (ImportError, OSError):
    _KAGGLE_OK = False
    logger.warning(
        "Kaggle API not configured.\n"
        "  1. pip install kaggle\n"
        "  2. Go to https://www.kaggle.com/settings -> API -> Create New Token\n"
        "  3. Save kaggle.json to C:/Users/<you>/.kaggle/kaggle.json"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dataset registry — every entry in kaggle_datasets.ALL_DATASETS that is on
# Kaggle gets a matching entry here with its exact CSV column names.
# ─────────────────────────────────────────────────────────────────────────────
DATASETS: list[dict] = [

    # ── Tourist Places ────────────────────────────────────────────────────────
    {
        'id':           'indian_tourism_54f',
        'slug':         'sushanthnaidu24/indian-tourism-dataset',
        'description':  'Indian Tourism Dataset (100 destinations, 54 fields)',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'name': 'name',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'District': 'district',
            'Address': 'address', 'Location': 'address',
            'Category': 'category', 'Type': 'category',
            'Description': 'description', 'About': 'description',
            'Entry_Fee': 'entry_fee', 'Entry Fee': 'entry_fee', 'Entrance_Fee': 'entry_fee',
            'Timings': 'timings', 'Opening_Hours': 'timings',
            'Best_Time_to_Visit': 'best_time_to_visit', 'Best Time to Visit': 'best_time_to_visit',
            'Rating': 'rating', 'Google_Rating': 'rating',
            'Latitude': 'latitude', 'Lat': 'latitude', 'lat': 'latitude',
            'Longitude': 'longitude', 'Lon': 'longitude', 'lon': 'longitude', 'Long': 'longitude',
            'Visit_Duration': 'visit_duration',
            'Best_Season': 'peak_season', 'Peak_Season': 'peak_season',
        },
    },
    {
        'id':           'explore_india_tourist',
        'slug':         'kumarperiya/explore-india-a-tourist-destination-dataset',
        'description':  'Explore India Tourist Destination Dataset',
        'target_table': 'tourist_places',
        'col_map': {
            # Actual CSV: Place_Name, City, State, Category, Description,
            #             Best_Time_to_Visit, Rating, Latitude, Longitude,
            #             Entry_Fee, Timings
            'Place_Name': 'name', 'Place Name': 'name', 'Name': 'name', 'name': 'name',
            'Place': 'name', 'place': 'name',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'District': 'district',
            'Category': 'category', 'Type': 'category', 'category': 'category',
            'Description': 'description', 'description': 'description', 'About': 'description',
            'Best_Time_to_Visit': 'best_time_to_visit',
            'Best Time to Visit': 'best_time_to_visit',
            'Best_Time': 'best_time_to_visit',
            'Rating': 'rating', 'rating': 'rating', 'Google_Rating': 'rating',
            'Latitude': 'latitude', 'latitude': 'latitude', 'Lat': 'latitude',
            'Longitude': 'longitude', 'longitude': 'longitude',
            'Lon': 'longitude', 'Long': 'longitude', 'Lng': 'longitude',
            'Entry_Fee': 'entry_fee', 'Entry Fee': 'entry_fee', 'Entrance Fee': 'entry_fee',
            'Timings': 'timings', 'timings': 'timings', 'Opening_Hours': 'timings',
            'Address': 'address', 'address': 'address', 'Location': 'address',
        },
    },
    {
        'id':           'top_places',
        'slug':         'dhrubangtalukdar/top-indian-places-to-visit-indian-tourism',
        'description':  'Top Indian Places to Visit (Indian Tourism)',
        'target_table': 'tourist_places',
        'col_map': {
            # Actual CSV: Zone, State, City, Name, Type,
            #             time needed to visit in hrs, Google review rating,
            #             Entrance Fee in INR, Best Time to visit,
            #             Establishment Year, DSLR Allowed, Weekly Off,
            #             Significance, Number of google review in lakhs,
            #             Airport with 50km Radius
            'Name': 'name', 'name': 'name',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'Zone': 'district',
            'Type': 'category', 'Category': 'category',
            'Google review rating': 'rating',
            'Entrance Fee in INR': 'entry_fee',
            'time needed to visit in hrs': 'visit_duration',
            'Best Time to visit': 'best_time_to_visit',
            'Weekly Off': 'timings',
            'Significance': 'description',
            'Establishment Year': 'description',
            'DSLR Allowed': 'description',
            'Number of google review in lakhs': 'description',
            'Airport with 50km Radius': 'description',
        },
    },
    {
        'id':           'india_tourism_atlas',
        'slug':         'anushkamandekar/indiatourismatlas',
        'description':  'India Tourism Atlas',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'Attraction': 'name',
            'City': 'city', 'State': 'state', 'District': 'district',
            'Category': 'category', 'Type': 'category',
            'Description': 'description', 'Significance': 'description',
            'Rating': 'rating', 'Fare': 'entry_fee', 'Entry_Fee': 'entry_fee',
            'Latitude': 'latitude', 'Lat': 'latitude',
            'Longitude': 'longitude', 'Lon': 'longitude', 'Long': 'longitude',
            'Address': 'address', 'Location': 'address',
            'Best_Time': 'best_time_to_visit', 'Best Time to Visit': 'best_time_to_visit',
        },
    },
    {
        'id':           'india_must_see_places',
        'slug':         'saketk511/travel-dataset-guide-to-indias-must-see-places',
        'description':  "Guide to India's Must-See Places (325 destinations)",
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'Attraction': 'name',
            'City': 'city', 'State': 'state',
            'Category': 'category', 'Type': 'category',
            'Description': 'description', 'About': 'description',
            'Rating': 'rating',
            'Entry_Fee': 'entry_fee', 'Entrance Fee': 'entry_fee',
            'Timings': 'timings',
            'Latitude': 'latitude', 'Lat': 'latitude',
            'Longitude': 'longitude', 'Lon': 'longitude',
            'Best_Time': 'best_time_to_visit', 'Best Time to Visit': 'best_time_to_visit',
            'Address': 'address', 'Location': 'address',
        },
    },
    {
        'id':           'famous_indian_tourist_places',
        'slug':         'naqibahmedkadri/famous-indian-tourist-places',
        'description':  'Famous Indian Tourist Places',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name',
            'City': 'city', 'State': 'state',
            'Category': 'category', 'Type': 'category',
            'Description': 'description',
            'Rating': 'rating',
            'Latitude': 'latitude', 'Longitude': 'longitude',
            'Entry_Fee': 'entry_fee',
            'Best_Time': 'best_time_to_visit',
        },
    },
    {
        'id':           'most_traveled_cities',
        'slug':         'kirtandwivedi02/most-traveled-cities-in-india',
        'description':  'Most Traveled Cities in India',
        'target_table': 'tourist_places',
        'col_map': {
            'City': 'name', 'city': 'name',
            'State': 'state', 'state': 'state',
            'Description': 'description', 'description': 'description',
            'Tourists': 'description', 'tourists': 'description',
            'Category': 'category', 'Region': 'district',
            'Latitude': 'latitude', 'Longitude': 'longitude',
            'Rating': 'rating',
        },
    },
    {
        'id':           'india_places_reviews',
        'slug':         'ritvik1909/indian-places-to-visit-reviews-data',
        'description':  'Indian Places Reviews Dataset',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name',
            'City': 'city', 'State': 'state',
            'Review': 'description', 'Description': 'description',
            'Rating': 'rating',
            'Category': 'category',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },

    # ── Hotels ────────────────────────────────────────────────────────────────
    {
        'id':           'makemytrip_hotels',
        'slug':         'PromptCloudHQ/hotels-on-makemytrip',
        'description':  'Hotels on MakeMyTrip (20,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            'hotel_name': 'name', 'name': 'name', 'Name': 'name',
            'Hotel': 'name', 'hotel': 'name',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'address': 'address', 'Address': 'address', 'Location': 'address',
            'description': 'description', 'Description': 'description', 'About': 'description',
            'star_rating': 'stars', 'stars': 'stars', 'Stars': 'stars', 'Rating': 'rating',
            'hotel_rating': 'rating', 'rating': 'rating',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'price_per_night': 'price_per_night', 'Price_INR': 'price_per_night',
            'amenities': 'amenities', 'Amenities': 'amenities', 'Facilities': 'amenities',
            'contact': 'contact', 'Contact': 'contact', 'Phone': 'contact',
            'website': 'website', 'Website': 'website',
            'latitude': 'latitude', 'Latitude': 'latitude', 'Lat': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude', 'Lon': 'longitude',
            'category': 'category', 'Category': 'category', 'Type': 'category',
        },
    },
    {
        'id':           'booking_com_hotels',
        'slug':         'PromptCloudHQ/indian-hotels-on-bookingcom',
        'description':  'Indian Hotels on Booking.com (6,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            'hotel_name': 'name', 'name': 'name', 'Hotel': 'name',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'address': 'address', 'Address': 'address', 'Location': 'address',
            'description': 'description', 'Description': 'description',
            'star_rating': 'stars', 'Stars': 'stars', 'Stars_Rating': 'stars',
            'rating': 'rating', 'Rating': 'rating', 'review_score': 'rating',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'amenities': 'amenities', 'facilities': 'amenities', 'Facilities': 'amenities',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'cleartrip_hotels',
        'slug':         'PromptCloudHQ/indian-hotels-on-cleartrip',
        'description':  'Indian Hotels on Cleartrip (5,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            'hotel_name': 'name', 'Hotel': 'name', 'name': 'name',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'address': 'address', 'Address': 'address',
            'description': 'description', 'Description': 'description',
            'star_rating': 'stars', 'Stars': 'stars',
            'rating': 'rating', 'Rating': 'rating',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'amenities': 'amenities', 'Amenities': 'amenities',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'goibibo_hotels',
        'slug':         'PromptCloudHQ/hotels-on-goibibo',
        'description':  'Indian Hotels on Goibibo (4,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            'hotel_name': 'name', 'Hotel': 'name', 'name': 'name',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'address': 'address', 'Address': 'address',
            'description': 'description', 'Description': 'description',
            'star_rating': 'stars', 'Stars': 'stars',
            'rating': 'rating', 'Rating': 'rating',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'amenities': 'amenities', 'Amenities': 'amenities',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'google_indian_hotels',
        'slug':         'alvinmanojalex/google-indian-hotel-data',
        'description':  'Google Indian Hotel Data 2023',
        'target_table': 'hotels',
        'col_map': {
            # Actual CSV: Hotel, Location, Rating, Category, Price,
            #             Latitude, Longitude, Description
            'Hotel': 'name', 'Hotel Name': 'name', 'Hotel_Name': 'name',
            'hotel': 'name', 'Name': 'name', 'name': 'name',
            'Location': 'address', 'location': 'address',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'Address': 'address', 'address': 'address',
            'Rating': 'rating', 'rating': 'rating',
            'Stars': 'stars', 'stars': 'stars', 'Star_Rating': 'stars',
            'Category': 'category', 'category': 'category', 'Type': 'category',
            'Price': 'price_per_night', 'Price_INR': 'price_per_night',
            'price': 'price_per_night', 'Fare': 'price_per_night',
            'Description': 'description', 'description': 'description', 'About': 'description',
            'Amenities': 'amenities', 'amenities': 'amenities', 'Facilities': 'amenities',
            'Contact': 'contact', 'contact': 'contact', 'Phone': 'contact',
            'Website': 'website', 'website': 'website',
            'Latitude': 'latitude', 'latitude': 'latitude', 'Lat': 'latitude',
            'Longitude': 'longitude', 'longitude': 'longitude',
            'Lon': 'longitude', 'Long': 'longitude',
        },
    },
    {
        'id':           'hotels_india_reviews',
        'slug':         'aakashshinde1507/hotels-in-india',
        'description':  'Hotels in India',
        'target_table': 'hotels',
        'col_map': {
            'Name': 'name', 'Hotel': 'name', 'hotel_name': 'name',
            'City': 'city', 'State': 'state',
            'Rating': 'rating', 'rating': 'rating', 'review_score': 'rating',
            'Stars': 'stars', 'star_rating': 'stars',
            'Sustainability': 'description', 'sustainability_level': 'description',
            'Reviews': 'description', 'review_count': 'description',
            'Description': 'description',
            'Price': 'price_per_night',
            'Amenities': 'amenities',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },

    # ── Flights ───────────────────────────────────────────────────────────────
    {
        'id':           'flights_india',
        'slug':         'dhairya903/flights-in-india',
        'description':  'Flights in India Dataset',
        'target_table': 'flights',
        'col_map': {
            'Airline': 'airline', 'airline': 'airline', 'Carrier': 'airline',
            'Flight': 'name', 'Flight_Name': 'name', 'flight': 'name',
            'Source': 'origin', 'From': 'origin', 'Origin': 'origin', 'source': 'origin',
            'Destination': 'destination', 'To': 'destination', 'dest': 'destination',
            'Route': 'route_name', 'route': 'route_name',
            'Dep_Time': 'departure_time', 'Departure': 'departure_time', 'Dep Time': 'departure_time',
            'Arrival_Time': 'arrival_time', 'Arrival': 'arrival_time', 'Arrival Time': 'arrival_time',
            'Duration': 'duration', 'duration': 'duration',
            'Price': 'fare', 'Fare': 'fare', 'price': 'fare', 'Price_INR': 'fare',
            'Total_Stops': 'description', 'Stops': 'description',
            'Additional_Info': 'description', 'Info': 'description',
        },
    },
    {
        'id':           'indian_airlines',
        'slug':         'kabil007/indian-domestic-airline-dataset',
        'description':  'Indian Domestic Airline Dataset (103 airports)',
        'target_table': 'flights',
        'col_map': {
            # Actual CSV: Airline, Source, Destination, Route,
            #             Dep_Time, Arrival_Time, Duration,
            #             Total_Stops, Additional_Info, Price
            'Airline': 'airline', 'airline': 'airline', 'Carrier': 'airline',
            'Flight': 'name', 'flight': 'name', 'Flight_Name': 'name',
            'Source': 'origin', 'source': 'origin', 'From': 'origin', 'Origin': 'origin',
            'Destination': 'destination', 'destination': 'destination',
            'To': 'destination', 'dest': 'destination',
            'Route': 'route_name', 'route': 'route_name',
            'Dep_Time': 'departure_time', 'Dep Time': 'departure_time',
            'Departure': 'departure_time', 'departure': 'departure_time',
            'Arrival_Time': 'arrival_time', 'Arrival Time': 'arrival_time',
            'Arrival': 'arrival_time', 'arrival': 'arrival_time',
            'Duration': 'duration', 'duration': 'duration', 'Total_Time': 'duration',
            'Price': 'fare', 'price': 'fare', 'Fare': 'fare', 'Price_INR': 'fare',
            'Total_Stops': 'description', 'Stops': 'description',
            'Additional_Info': 'description', 'Additional Info': 'description',
            'Info': 'description',
        },
    },
    {
        'id':           'indian_flight_schedules',
        'slug':         'nikhilkhetan/indian-flight-schedules',
        'description':  'Indian Flight Schedules',
        'target_table': 'flights',
        'col_map': {
            'Airline': 'airline', 'airline': 'airline',
            'Flight': 'name', 'Flight_No': 'name', 'flight_no': 'name',
            'Source': 'origin', 'From': 'origin', 'Origin': 'origin',
            'Destination': 'destination', 'To': 'destination',
            'Route': 'route_name',
            'Dep_Time': 'departure_time', 'Departure': 'departure_time',
            'Arrival_Time': 'arrival_time', 'Arrival': 'arrival_time',
            'Duration': 'duration',
            'Price': 'fare', 'Fare': 'fare',
            'Stops': 'description', 'Additional_Info': 'description',
        },
    },
    {
        'id':           'india_domestic_flights_6yr',
        'slug':         'shraddha4ever20/indian-domestic-flights-dataset-20192025',
        'description':  'Indian Domestic Flights Dataset 2019-2025',
        'target_table': 'flights',
        'col_map': {
            'Airline': 'airline', 'airline': 'airline',
            'Flight': 'name', 'FlightNo': 'name',
            'Source': 'origin', 'Origin': 'origin', 'From': 'origin',
            'Destination': 'destination', 'To': 'destination',
            'Route': 'route_name',
            'Departure': 'departure_time', 'Dep_Time': 'departure_time',
            'Arrival': 'arrival_time', 'Arrival_Time': 'arrival_time',
            'Duration': 'duration',
            'Price': 'fare', 'Fare': 'fare',
            'Stops': 'description',
            'Year': 'description', 'Date': 'description',
        },
    },
    {
        'id':           'global_airline_routes',
        'slug':         'elmoallistair/airlines-airport-and-routes',
        'description':  'Airlines, Airports & Flight Routes (67,664 routes)',
        'target_table': 'flights',
        'col_map': {
            'airline': 'airline', 'Airline': 'airline', 'airline_name': 'airline',
            'name': 'name', 'Name': 'name',
            'source_airport': 'origin', 'src_airport': 'origin',
            'destination_airport': 'destination', 'dst_airport': 'destination',
            'Source Airport': 'origin', 'Destination Airport': 'destination',
            'route': 'route_name', 'Route': 'route_name',
            'equipment': 'description', 'Equipment': 'description',
            'stops': 'description', 'Stops': 'description',
            'codeshare': 'description',
        },
    },
    {
        'id':           'openflights_routes',
        'slug':         'open-flights/flight-route-database',
        'description':  'Flight Route Database (59,036 routes)',
        'target_table': 'flights',
        'col_map': {
            'airline': 'airline', 'Airline': 'airline',
            'name': 'name',
            'source airport': 'origin', 'Source Airport': 'origin',
            'destination airport': 'destination', 'Destination Airport': 'destination',
            'route': 'route_name',
            'equipment': 'description', 'stops': 'description',
        },
    },
    {
        'id':           'airline_routes_92k',
        'slug':         'moonnectar/airline-routes-92k-and-airports-10k-dataset',
        'description':  'Airline Routes 92K+ & Airports 9K+',
        'target_table': 'flights',
        'col_map': {
            'Airline': 'airline', 'airline': 'airline',
            'Name': 'name', 'name': 'name',
            'Source': 'origin', 'source': 'origin', 'Origin': 'origin',
            'Destination': 'destination', 'destination': 'destination',
            'Route': 'route_name',
            'Equipment': 'description', 'Stops': 'description',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },

    # ── Railways ──────────────────────────────────────────────────────────────
    {
        'id':           'indian_railways_core',
        'slug':         'sripaadsrinivasan/indian-railways-dataset',
        'description':  'Indian Railways Dataset',
        'target_table': 'tourist_places',
        'col_map': {
            'Train_Name': 'name', 'Train Name': 'name', 'name': 'name', 'Name': 'name',
            'Train_No': 'description', 'Train No': 'description',
            'Source': 'city', 'From': 'city', 'Origin': 'city',
            'Destination': 'description', 'To': 'description',
            'Route': 'description', 'Type': 'category', 'Category': 'category',
            'Distance': 'description', 'Duration': 'description',
        },
    },
    {
        'id':           'indian_railways_latest',
        'slug':         'arihantjain09/indian-railways-latest',
        'description':  'Indian Railways Latest (11,114 trains)',
        'target_table': 'tourist_places',
        'col_map': {
            'Train_Name': 'name', 'Train Name': 'name', 'TrainName': 'name',
            'train_name': 'name', 'Name': 'name',
            'Train_No': 'description', 'TrainNo': 'description',
            'From': 'city', 'Source': 'city', 'Origin': 'city',
            'To': 'description', 'Destination': 'description',
            'Type': 'category', 'Train_Type': 'category',
            'Distance_km': 'description', 'Duration': 'description',
            'Departure': 'description', 'Arrival': 'description',
        },
    },
    {
        'id':           'railway_stations',
        'slug':         'flugeltomar/indian-railway-dataset',
        'description':  'Indian Railway Stations Dataset',
        'target_table': 'tourist_places',
        'col_map': {
            'Station_Name': 'name', 'Station Name': 'name', 'StationName': 'name',
            'station_name': 'name', 'Name': 'name',
            'Station_Code': 'description', 'Code': 'description',
            'Zone': 'district', 'State': 'state', 'City': 'city',
            'Latitude': 'latitude', 'Lat': 'latitude',
            'Longitude': 'longitude', 'Lon': 'longitude',
            'Category': 'category',
        },
    },
    {
        'id':           'railway_stations_facilities',
        'slug':         'shraddha4ever20/indian-railway-stations-codes-and-facilities-data',
        'description':  'Indian Railway Stations Codes & Facilities',
        'target_table': 'tourist_places',
        'col_map': {
            'Station_Name': 'name', 'Station Name': 'name', 'Name': 'name',
            'Station_Code': 'description', 'Code': 'description',
            'Zone': 'district', 'State': 'state',
            'Platforms': 'description', 'WiFi': 'description',
            'Food': 'description', 'Accessibility': 'description',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'railways_prices',
        'slug':         'bhavyarajdev/indian-railways-schedule-prices-availability-data',
        'description':  'Indian Railways Schedule, Prices & Availability',
        'target_table': 'tourist_places',
        'col_map': {
            'Train_Name': 'name', 'Train Name': 'name', 'Name': 'name',
            'Train_No': 'description',
            'From': 'city', 'To': 'description',
            'Class': 'category', 'Fare': 'entry_fee', 'Price': 'entry_fee',
            'Availability': 'description', 'Schedule': 'description',
            'Departure': 'timings', 'Arrival': 'description',
        },
    },
    {
        'id':           'railways_timetable',
        'slug':         'harsh16/indian-railways-time-table-for-trains-available',
        'description':  'Indian Railways Time Table',
        'target_table': 'tourist_places',
        'col_map': {
            'Train_Name': 'name', 'Train Name': 'name', 'TrainName': 'name', 'Name': 'name',
            'Train_No': 'description', 'TrainNo': 'description',
            'Source': 'city', 'From': 'city',
            'Destination': 'description', 'To': 'description',
            'Departure_Time': 'timings', 'Arrival_Time': 'description',
            'Type': 'category', 'Zone': 'district',
        },
    },

    # ── Bus Routes ────────────────────────────────────────────────────────────
    {
        'id':           'bus_routes_pan_india',
        'slug':         'rohitgds/pan-india-bus-routes-35k-schedules-1000-cities',
        'description':  'Pan India Bus Routes (35,667 schedules)',
        'target_table': 'tourist_places',
        'col_map': {
            'Route_Name': 'name', 'Route Name': 'name', 'Bus_Name': 'name', 'Name': 'name',
            'Source': 'city', 'From': 'city', 'Origin': 'city',
            'Destination': 'description', 'To': 'description',
            'Departure_Time': 'timings', 'Arrival_Time': 'description',
            'Duration': 'description', 'Distance': 'description',
            'Price': 'entry_fee', 'Fare': 'entry_fee',
            'Operator': 'category', 'Bus_Type': 'category',
        },
    },
    {
        'id':           'bus_routes_cities',
        'slug':         'ayushkhaire/indian-cities-buses-routes-and-prices',
        'description':  'Indian Cities Bus Routes & Prices',
        'target_table': 'tourist_places',
        'col_map': {
            'Route': 'name', 'Route_Name': 'name', 'Bus': 'name', 'Name': 'name',
            'From': 'city', 'Source': 'city',
            'To': 'description', 'Destination': 'description',
            'City': 'city', 'State': 'state',
            'Price': 'entry_fee', 'Fare': 'entry_fee',
            'Duration': 'description', 'Distance': 'description',
            'Type': 'category',
        },
    },

    # ── Travel Guides / Route Planning ────────────────────────────────────────
    {
        'id':           'travel_recommendation',
        'slug':         'amanmehra23/travel-recommendation-dataset',
        'description':  'Travel Recommendation Dataset',
        'target_table': 'tourist_places',
        'col_map': {
            'Destination': 'name', 'Place': 'name', 'Name': 'name',
            'City': 'city', 'State': 'state', 'Country': 'state',
            'Category': 'category', 'Type': 'category',
            'Description': 'description', 'About': 'description',
            'Rating': 'rating',
            'Budget': 'entry_fee', 'Cost': 'entry_fee',
            'Best_Time': 'best_time_to_visit',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'dynamic_tourism_routes',
        'slug':         'ziya07/dynamic-tourism-route-dataset-dtrd',
        'description':  'Dynamic Tourism Route Dataset (DTRD)',
        'target_table': 'tourist_places',
        'col_map': {
            'Attraction': 'name', 'Name': 'name', 'Place': 'name',
            'City': 'city', 'State': 'state',
            'Category': 'category', 'Type': 'category',
            'Description': 'description',
            'Rating': 'rating',
            'Crowd_Density': 'crowd_level',
            'Best_Time': 'best_time_to_visit',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'road_tourism_sustainable',
        'slug':         'ziya07/road-tourism-data-for-sustainable-route-prediction',
        'description':  'Road Tourism Data for Sustainable Route Prediction',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'Route': 'name',
            'From': 'city', 'City': 'city', 'State': 'state',
            'Category': 'category',
            'Description': 'description',
            'Distance': 'description', 'Duration': 'description',
            'Traffic': 'description', 'Sustainability_Score': 'description',
        },
    },
    {
        'id':           'tourist_attractions',
        'slug':         'dakshineswarm/indian-tourist-attraction-dataset',
        'description':  'Indian Tourist Attractions (~500 places)',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'Attraction': 'name',
            'City': 'city', 'State': 'state',
            'Category': 'category', 'Type': 'category',
            'Description': 'description',
            'Rating': 'rating',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'india_tourism_stats',
        'slug':         'rajkumarl/india-tourism-statistics',
        'description':  'India Tourism Statistics',
        'target_table': 'tourist_places',
        'col_map': {
            'State': 'state', 'City': 'city', 'Name': 'name',
            'Destination': 'name', 'Description': 'description',
            'Rating': 'rating', 'Visitors': 'description',
        },
    },
    {
        'id':           'hotel_details',
        'slug':         'nehaprabhakar/hotel-details-dataset-india',
        'description':  'Hotel Details Dataset — India',
        'target_table': 'hotels',
        'col_map': {
            'hotel_name': 'name', 'name': 'name', 'Hotel': 'name',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'address': 'address', 'Address': 'address',
            'description': 'description', 'Description': 'description',
            'rating': 'rating', 'Rating': 'rating',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'google_places_rating',
        'slug':         'chetanborse/google-places-rating-for-indian-cities',
        'description':  'Google Places Rating for Indian Cities',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'Title': 'name',
            'City': 'city', 'State': 'state',
            'Category': 'category', 'Type': 'category',
            'Rating': 'rating', 'Review Count': 'description',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'india_tourism_datasets',
        'slug':         'rakkeshcase/india-tourism-datasets',
        'description':  'India Tourism Datasets (multi-file bundle)',
        'target_table': 'tourist_places',
        'col_map': {
            'Name': 'name', 'Place': 'name', 'Attraction': 'name',
            'City': 'city', 'State': 'state',
            'Category': 'category', 'Type': 'category',
            'Description': 'description',
            'Rating': 'rating',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# KaggleImporter — Main class for importing Kaggle datasets
# ─────────────────────────────────────────────────────────────────────────────
class KaggleImporter:
    """Import curated Kaggle datasets into nexuzy_travel.db"""
    
    def __init__(self, db):
        """Initialize KaggleImporter with database connection
        
        Args:
            db: Database connection object
        """
        self.db = db
        self.imported_count = 0
        self.failed_count = 0
    
    def run_all(self):
        """Import all available Kaggle datasets"""
        logger.info(f"Starting import of {len(DATASETS)} Kaggle datasets...")
        
        if not _KAGGLE_OK:
            logger.error("Kaggle API not configured. Cannot proceed.")
            return False
        
        if not _PANDAS_OK:
            logger.error("pandas not installed. Cannot proceed.")
            return False
        
        for dataset in DATASETS:
            try:
                self.run(dataset['id'])
            except Exception as e:
                logger.error(f"Failed to import {dataset['id']}: {e}")
                self.failed_count += 1
        
        logger.info(f"Import complete: {self.imported_count} succeeded, {self.failed_count} failed")
        return self.failed_count == 0
    
    def run(self, dataset_id: str):
        """Import a specific dataset by ID
        
        Args:
            dataset_id: The 'id' field from DATASETS
            
        Returns:
            bool: True if successful
        """
        # Find the dataset in registry
        dataset = None
        for ds in DATASETS:
            if ds['id'] == dataset_id:
                dataset = ds
                break
        
        if not dataset:
            logger.error(f"Dataset '{dataset_id}' not found in registry")
            return False
        
        logger.info(f"Importing {dataset['description']} ({dataset['slug']})...")
        
        try:
            if not _KAGGLE_OK or not _PANDAS_OK:
                logger.warning(f"Skipping {dataset_id}: missing dependencies")
                return False
            
            # Create temporary directory for download
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Download dataset
                logger.debug(f"Downloading from {dataset['slug']}...")
                import subprocess
                result = subprocess.run(
                    ['kaggle', 'datasets', 'download', '-d', dataset['slug'], '-p', str(tmppath)],
                    capture_output=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    logger.error(f"Kaggle download failed: {result.stderr.decode()}")
                    self.failed_count += 1
                    return False
                
                # Extract and find CSV
                import zipfile
                for zf in tmppath.glob('*.zip'):
                    with zipfile.ZipFile(zf) as z:
                        z.extractall(tmppath)
                
                # Find CSV files
                csv_files = list(tmppath.glob('*.csv'))
                if not csv_files:
                    logger.warning(f"No CSV files found in {dataset['slug']}")
                    self.failed_count += 1
                    return False
                
                # Load first CSV
                csv_file = csv_files[0]
                logger.debug(f"Loading {csv_file.name}...")
                
                # Try to load CSV with error handling for malformed rows
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8')
                except (pd.errors.ParserError, UnicodeDecodeError) as e:
                    logger.warning(f"CSV parsing error, attempting with error_bad_lines: {e}")
                    try:
                        # Try again with on_bad_lines='skip' (pandas 1.3+) or error_bad_lines=False (pandas < 1.3)
                        try:
                            df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')
                        except TypeError:
                            df = pd.read_csv(csv_file, encoding='utf-8', error_bad_lines=False)
                    except Exception as e2:
                        logger.error(f"Failed to parse CSV even with error recovery: {e2}")
                        self.failed_count += 1
                        return False
                
                if df.empty:
                    logger.warning(f"CSV file {csv_file.name} is empty after parsing")
                    self.failed_count += 1
                    return False
                
                # Map columns and prepare data
                mapped_data = self._map_columns(df, dataset['col_map'])
                
                # Insert into database
                if self.db and hasattr(self.db, 'insert_batch'):
                    self.db.insert_batch(dataset['target_table'], mapped_data)
                
                logger.info(f"Successfully imported {len(mapped_data)} records from {dataset_id}")
                self.imported_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Error importing {dataset_id}: {e}")
            self.failed_count += 1
            return False
    
    def _map_columns(self, df, col_map):
        """Map CSV columns to database columns using the mapping dictionary
        
        Args:
            df: pandas DataFrame
            col_map: Dictionary mapping CSV columns to DB columns
            
        Returns:
            list: List of dictionaries with mapped data
        """
        mapped_records = []
        
        for _, row in df.iterrows():
            record = {}
            for csv_col, db_col in col_map.items():
                if csv_col in df.columns and pd.notna(row[csv_col]):
                    if db_col not in record or pd.isna(record.get(db_col)):
                        record[db_col] = row[csv_col]
            
            if record:
                mapped_records.append(record)
        
        return mapped_records