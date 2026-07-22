import os
import googlemaps

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def geocode(address: str):
    if not API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set in environment variables.")

    gmaps = googlemaps.Client(key=API_KEY)

    # Perform forward geocoding with US region biasing
    results = gmaps.geocode(address, region="us")

    if not results:
        return None

    # Retrieve coordinates from the top match
    location = results[0]["geometry"]["location"]
    return float(location["lat"]), float(location["lng"])