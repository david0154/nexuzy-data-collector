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
    # NOTE: PromptCloud datasets (MakeMyTrip, Booking.com, Cleartrip, Goibibo)
    # all use 'property_name' as the hotel name column, NOT 'hotel_name'.
    # Real columns verified from Kaggle/OpenDataBay metadata:
    #   property_name, hotel_description, hotel_facilities, hotel_star_rating,
    #   site_review_rating, city, province, state, address, locality,
    #   latitude, longitude, property_type, pageurl
    {
        'id':           'makemytrip_hotels',
        'slug':         'PromptCloudHQ/hotels-on-makemytrip',
        'description':  'Hotels on MakeMyTrip (20,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            # PromptCloud real columns
            'property_name': 'name',
            'hotel_description': 'description',
            'hotel_facilities': 'amenities',
            'hotel_star_rating': 'stars',
            'site_review_rating': 'rating',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'province': 'state',
            'address': 'address', 'Address': 'address',
            'locality': 'address',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
            'property_type': 'category',
            'pageurl': 'website',
            # Fallback generic names
            'hotel_name': 'name', 'name': 'name', 'Name': 'name', 'Hotel': 'name',
            'hotel_rating': 'rating', 'rating': 'rating', 'Rating': 'rating',
            'star_rating': 'stars', 'stars': 'stars', 'Stars': 'stars',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'price_per_night': 'price_per_night', 'Price_INR': 'price_per_night',
            'amenities': 'amenities', 'Amenities': 'amenities', 'Facilities': 'amenities',
            'description': 'description', 'Description': 'description',
            'contact': 'contact', 'Contact': 'contact', 'Phone': 'contact',
            'website': 'website', 'Website': 'website',
            'category': 'category', 'Category': 'category', 'Type': 'category',
        },
    },
    {
        'id':           'booking_com_hotels',
        'slug':         'PromptCloudHQ/indian-hotels-on-bookingcom',
        'description':  'Indian Hotels on Booking.com (6,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            # PromptCloud real columns
            'property_name': 'name',
            'hotel_description': 'description',
            'hotel_facilities': 'amenities',
            'hotel_star_rating': 'stars',
            'site_review_rating': 'rating',
            'site_review_count': 'description',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'province': 'state',
            'address': 'address', 'Address': 'address',
            'locality': 'address',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
            'property_type': 'category',
            'room_type': 'amenities',
            'pageurl': 'website',
            # Fallback
            'hotel_name': 'name', 'name': 'name', 'Hotel': 'name',
            'rating': 'rating', 'Rating': 'rating', 'review_score': 'rating',
            'star_rating': 'stars', 'Stars': 'stars', 'Stars_Rating': 'stars',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'amenities': 'amenities', 'facilities': 'amenities', 'Facilities': 'amenities',
            'description': 'description', 'Description': 'description',
        },
    },
    {
        'id':           'cleartrip_hotels',
        'slug':         'PromptCloudHQ/indian-hotels-on-cleartrip',
        'description':  'Indian Hotels on Cleartrip (5,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            # PromptCloud real columns
            'property_name': 'name',
            'hotel_description': 'description',
            'hotel_facilities': 'amenities',
            'hotel_star_rating': 'stars',
            'site_review_rating': 'rating',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'province': 'state',
            'address': 'address', 'Address': 'address',
            'locality': 'address',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
            'property_type': 'category',
            'pageurl': 'website',
            # Fallback
            'hotel_name': 'name', 'Hotel': 'name', 'name': 'name',
            'rating': 'rating', 'Rating': 'rating',
            'star_rating': 'stars', 'Stars': 'stars',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'amenities': 'amenities', 'Amenities': 'amenities',
            'description': 'description', 'Description': 'description',
        },
    },
    {
        'id':           'goibibo_hotels',
        'slug':         'PromptCloudHQ/hotels-on-goibibo',
        'description':  'Indian Hotels on Goibibo (4,000 hotels)',
        'target_table': 'hotels',
        'col_map': {
            # PromptCloud real columns
            'property_name': 'name',
            'hotel_description': 'description',
            'hotel_facilities': 'amenities',
            'hotel_star_rating': 'stars',
            'site_review_rating': 'rating',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'province': 'state',
            'address': 'address', 'Address': 'address',
            'locality': 'address',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
            'property_type': 'category',
            'pageurl': 'website',
            # Fallback
            'hotel_name': 'name', 'Hotel': 'name', 'name': 'name',
            'rating': 'rating', 'Rating': 'rating',
            'star_rating': 'stars', 'Stars': 'stars',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'amenities': 'amenities', 'Amenities': 'amenities',
            'description': 'description', 'Description': 'description',
        },
    },
    {
        'id':           'google_indian_hotels',
        'slug':         'alvinmanojalex/google-indian-hotel-data',
        'description':  'Google Indian Hotel Data 2023',
        'target_table': 'hotels',
        'col_map': {
            'Hotel': 'name', 'Hotel Name': 'name', 'Hotel_Name': 'name',
            'hotel': 'name', 'Name': 'name', 'name': 'name',
            'property_name': 'name',
            'Location': 'address', 'location': 'address',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'Address': 'address', 'address': 'address',
            'locality': 'address',
            'Rating': 'rating', 'rating': 'rating', 'site_review_rating': 'rating',
            'Stars': 'stars', 'stars': 'stars', 'Star_Rating': 'stars',
            'hotel_star_rating': 'stars',
            'Category': 'category', 'category': 'category', 'Type': 'category',
            'property_type': 'category',
            'Price': 'price_per_night', 'Price_INR': 'price_per_night',
            'price': 'price_per_night', 'Fare': 'price_per_night',
            'Description': 'description', 'description': 'description', 'About': 'description',
            'hotel_description': 'description',
            'Amenities': 'amenities', 'amenities': 'amenities', 'Facilities': 'amenities',
            'hotel_facilities': 'amenities',
            'Contact': 'contact', 'contact': 'contact', 'Phone': 'contact',
            'Website': 'website', 'website': 'website', 'pageurl': 'website',
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
            'Name': 'name', 'Hotel': 'name', 'hotel_name': 'name', 'property_name': 'name',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'Rating': 'rating', 'rating': 'rating', 'review_score': 'rating',
            'site_review_rating': 'rating',
            'Stars': 'stars', 'star_rating': 'stars', 'hotel_star_rating': 'stars',
            'Sustainability': 'description', 'sustainability_level': 'description',
            'Reviews': 'description', 'review_count': 'description',
            'Description': 'description', 'hotel_description': 'description',
            'Price': 'price_per_night',
            'Amenities': 'amenities', 'hotel_facilities': 'amenities',
            'Latitude': 'latitude', 'latitude': 'latitude',
            'Longitude': 'longitude', 'longitude': 'longitude',
        },
    },
    {
        'id':           'hotel_details',
        'slug':         'nehaprabhakar/hotel-details-dataset-india',
        'description':  'Hotel Details Dataset — India',
        'target_table': 'hotels',
        'col_map': {
            'hotel_name': 'name', 'name': 'name', 'Hotel': 'name', 'property_name': 'name',
            'city': 'city', 'City': 'city',
            'state': 'state', 'State': 'state',
            'address': 'address', 'Address': 'address', 'locality': 'address',
            'description': 'description', 'Description': 'description',
            'hotel_description': 'description',
            'rating': 'rating', 'Rating': 'rating', 'site_review_rating': 'rating',
            'hotel_star_rating': 'stars',
            'price': 'price_per_night', 'Price': 'price_per_night',
            'hotel_facilities': 'amenities',
            'latitude': 'latitude', 'Latitude': 'latitude',
            'longitude': 'longitude', 'Longitude': 'longitude',
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

    # ── Railways → trains table ───────────────────────────────────────────────
    {
        'id':           'indian_railways_core',
        'slug':         'sripaadsrinivasan/indian-railways-dataset',
        'description':  'Indian Railways Dataset',
        'target_table': 'trains',
        'col_map': {
            'Train_Name': 'train_name', 'Train Name': 'train_name', 'TrainName': 'train_name',
            'train_name': 'train_name', 'Name': 'train_name', 'name': 'train_name',
            'Train_No': 'train_no', 'Train No': 'train_no', 'TrainNo': 'train_no',
            'Source': 'origin', 'From': 'origin', 'Origin': 'origin', 'source': 'origin',
            'Destination': 'destination', 'To': 'destination', 'dest': 'destination',
            'Route': 'description', 'Type': 'train_type', 'Category': 'train_type',
            'Distance': 'distance_km', 'Distance_km': 'distance_km',
            'Duration': 'duration',
            'Departure': 'departure_time', 'Departure_Time': 'departure_time',
            'Arrival': 'arrival_time', 'Arrival_Time': 'arrival_time',
            'Zone': 'zone', 'State': 'state',
        },
    },
    {
        'id':           'indian_railways_latest',
        'slug':         'arihantjain09/indian-railways-latest',
        'description':  'Indian Railways Latest (11,114 trains)',
        'target_table': 'trains',
        'col_map': {
            'Train_Name': 'train_name', 'Train Name': 'train_name', 'TrainName': 'train_name',
            'train_name': 'train_name', 'Name': 'train_name',
            'Train_No': 'train_no', 'TrainNo': 'train_no', 'train_no': 'train_no',
            'From': 'origin', 'Source': 'origin', 'Origin': 'origin',
            'To': 'destination', 'Destination': 'destination',
            'Type': 'train_type', 'Train_Type': 'train_type',
            'Distance_km': 'distance_km', 'Distance': 'distance_km',
            'Duration': 'duration',
            'Departure': 'departure_time', 'Arrival': 'arrival_time',
            'Zone': 'zone',
        },
    },
    {
        'id':           'railway_stations',
        'slug':         'flugeltomar/indian-railway-dataset',
        'description':  'Indian Railway Stations Dataset',
        'target_table': 'trains',
        'col_map': {
            'Station_Name': 'train_name', 'Station Name': 'train_name',
            'StationName': 'train_name', 'station_name': 'train_name', 'Name': 'train_name',
            'Station_Code': 'station_code', 'Code': 'station_code',
            'Zone': 'zone', 'State': 'state', 'City': 'origin',
            'Latitude': 'latitude', 'Lat': 'latitude',
            'Longitude': 'longitude', 'Lon': 'longitude',
            'Category': 'train_type',
        },
    },
    {
        'id':           'railway_stations_facilities',
        'slug':         'shraddha4ever20/indian-railway-stations-codes-and-facilities-data',
        'description':  'Indian Railway Stations Codes & Facilities',
        'target_table': 'trains',
        'col_map': {
            'Station_Name': 'train_name', 'Station Name': 'train_name', 'Name': 'train_name',
            'Station_Code': 'station_code', 'Code': 'station_code',
            'Zone': 'zone', 'State': 'state',
            'Platforms': 'platforms', 'WiFi': 'wifi',
            'Food': 'description', 'Accessibility': 'description',
            'Latitude': 'latitude', 'Longitude': 'longitude',
        },
    },
    {
        'id':           'railways_prices',
        'slug':         'bhavyarajdev/indian-railways-schedule-prices-availability-data',
        'description':  'Indian Railways Schedule, Prices & Availability',
        'target_table': 'trains',
        'col_map': {
            'Train_Name': 'train_name', 'Train Name': 'train_name', 'Name': 'train_name',
            'train_name': 'train_name', 'TrainName': 'train_name',
            'Train_No': 'train_no', 'Train No': 'train_no', 'train_no': 'train_no',
            'From': 'origin', 'Source': 'origin', 'from': 'origin', 'source_station': 'origin',
            'To': 'destination', 'Destination': 'destination', 'to': 'destination',
            'Class': 'train_type', 'class': 'train_type', 'Travel_Class': 'train_type',
            'Fare': 'fare', 'fare': 'fare', 'Price': 'fare', 'price': 'fare',
            'Availability': 'availability', 'availability': 'availability',
            'Schedule': 'schedule', 'schedule': 'schedule',
            'Departure': 'departure_time', 'departure': 'departure_time',
            'Dep_Time': 'departure_time', 'Departure_Time': 'departure_time',
            'Arrival': 'arrival_time', 'arrival': 'arrival_time',
            'Arrival_Time': 'arrival_time',
            'Duration': 'duration', 'duration': 'duration',
            'Distance': 'distance_km', 'distance': 'distance_km',
            'Zone': 'zone', 'State': 'state',
        },
    },
    {
        'id':           'railways_timetable',
        'slug':         'harsh16/indian-railways-time-table-for-trains-available',
        'description':  'Indian Railways Time Table',
        'target_table': 'trains',
        'col_map': {
            'Train_Name': 'train_name', 'Train Name': 'train_name',
            'TrainName': 'train_name', 'Name': 'train_name',
            'Train_No': 'train_no', 'TrainNo': 'train_no',
            'Source': 'origin', 'From': 'origin',
            'Destination': 'destination', 'To': 'destination',
            'Departure_Time': 'departure_time', 'Dep_Time': 'departure_time',
            'Arrival_Time': 'arrival_time',
            'Type': 'train_type', 'Zone': 'zone',
            'State': 'state', 'Distance': 'distance_km',
        },
    },

    # ── Bus Routes → buses table ──────────────────────────────────────────────
    {
        'id':           'bus_routes_pan_india',
        'slug':         'rohitgds/pan-india-bus-routes-35k-schedules-1000-cities',
        'description':  'Pan India Bus Routes (35,667 schedules)',
        'target_table': 'buses',
        'col_map': {
            'Route_Name': 'route_name', 'Route Name': 'route_name', 'Route': 'route_name',
            'Bus_Name': 'route_name', 'Name': 'route_name', 'name': 'route_name',
            'Source': 'origin', 'From': 'origin', 'Origin': 'origin', 'from': 'origin',
            'Destination': 'destination', 'To': 'destination', 'to': 'destination',
            'Departure_Time': 'departure_time', 'Dep_Time': 'departure_time',
            'Departure': 'departure_time',
            'Arrival_Time': 'arrival_time', 'Arrival': 'arrival_time',
            'Duration': 'duration', 'duration': 'duration',
            'Distance': 'distance_km', 'Distance_km': 'distance_km',
            'Price': 'fare', 'Fare': 'fare', 'fare': 'fare', 'price': 'fare',
            'Operator': 'operator', 'operator': 'operator', 'Bus_Operator': 'operator',
            'Bus_Type': 'bus_type', 'Type': 'bus_type', 'type': 'bus_type',
            'City': 'city', 'State': 'state',
        },
    },
    {
        'id':           'bus_routes_cities',
        'slug':         'ayushkhaire/indian-cities-buses-routes-and-prices',
        'description':  'Indian Cities Bus Routes & Prices',
        'target_table': 'buses',
        'col_map': {
            'Route': 'route_name', 'Route_Name': 'route_name', 'route_name': 'route_name',
            'Bus': 'route_name', 'Name': 'route_name', 'name': 'route_name',
            'From': 'origin', 'Source': 'origin', 'from': 'origin',
            'To': 'destination', 'Destination': 'destination', 'to': 'destination',
            'City': 'city', 'city': 'city',
            'State': 'state', 'state': 'state',
            'Price': 'fare', 'Fare': 'fare', 'fare': 'fare', 'price': 'fare',
            'Duration': 'duration', 'Distance': 'distance_km',
            'Type': 'bus_type', 'Bus_Type': 'bus_type',
            'Operator': 'operator',
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


class KaggleImporter:
    """Import curated Kaggle datasets into nexuzy_travel.db"""

    def __init__(self, db):
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
        """Import a specific dataset by ID"""
        dataset = next((ds for ds in DATASETS if ds['id'] == dataset_id), None)
        if not dataset:
            logger.error(f"Dataset '{dataset_id}' not found in registry")
            return False

        logger.info(f"Importing {dataset['description']} ({dataset['slug']})...")

        try:
            if not _KAGGLE_OK or not _PANDAS_OK:
                logger.warning(f"Skipping {dataset_id}: missing dependencies")
                return False

            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)

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

                import zipfile
                for zf in tmppath.glob('*.zip'):
                    with zipfile.ZipFile(zf) as z:
                        z.extractall(tmppath)

                csv_files = list(tmppath.glob('*.csv'))
                if not csv_files:
                    logger.warning(f"No CSV files found in {dataset['slug']}")
                    self.failed_count += 1
                    return False

                csv_file = csv_files[0]
                logger.debug(f"Loading {csv_file.name}...")

                # Always log actual CSV columns so col_map mismatches are visible
                try:
                    df_head = pd.read_csv(csv_file, encoding='utf-8', nrows=0)
                    logger.info(f"[col_map debug] {dataset_id} CSV columns: {list(df_head.columns)}")
                    df = pd.read_csv(csv_file, encoding='utf-8')
                except (pd.errors.ParserError, UnicodeDecodeError) as e:
                    logger.warning(f"CSV parsing error, retrying with on_bad_lines=skip: {e}")
                    try:
                        try:
                            df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')
                        except TypeError:
                            df = pd.read_csv(csv_file, encoding='utf-8', error_bad_lines=False)
                    except Exception as e2:
                        logger.error(f"Failed to parse CSV: {e2}")
                        self.failed_count += 1
                        return False

                if df.empty:
                    logger.warning(f"CSV file {csv_file.name} is empty")
                    self.failed_count += 1
                    return False

                mapped_data = self._map_columns(df, dataset['col_map'])

                if not mapped_data:
                    logger.warning(
                        f"No rows mapped for {dataset_id}. "
                        f"CSV columns: {list(df.columns)} | "
                        f"col_map keys: {list(dataset['col_map'].keys())}"
                    )
                    self.failed_count += 1
                    return False

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
        """Map CSV columns to database columns using the mapping dictionary"""
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
